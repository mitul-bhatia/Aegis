import asyncio
import json
import os
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from utils.limiter import limiter  # shared limiter instance used across all routes
import uvicorn

import config
from database.db import init_db, SessionLocal
from github_integration.webhook import verify_signature, extract_push_info
from orchestrator import run_aegis_pipeline
from routes.auth import router as auth_router
from routes.repos import router as repos_router
from routes.scans import router as scans_router, set_event_loop
from routes.scheduler import router as scheduler_router
from routes.intelligence import router as intelligence_router
from routes.export import router as export_router
from scheduler import start_autonomous_scheduler, stop_autonomous_scheduler

# Initialize configuration
config.setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Security System")

# Rate limiter — uses the client's IP address as the key
# Attach to app.state so slowapi can find it automatically
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow the Next.js frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount new API routes
app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(scans_router)
app.include_router(scheduler_router)
app.include_router(intelligence_router)
app.include_router(export_router)

# Create database tables on startup
@app.on_event("startup")
async def on_startup():
    # Database is already initialized - tables created via Base.metadata.create_all()
    logger.info("Database ready")

    # Give the SSE bridge the running event loop so the orchestrator
    # (which runs in a background thread) can push updates to SSE clients.
    set_event_loop(asyncio.get_event_loop())
    if not config.GITHUB_WEBHOOK_SECRET:
        logger.warning(
            "GITHUB_WEBHOOK_SECRET is empty. /webhook/github will reject requests until configured."
        )
    
    # Start autonomous scheduler
    if os.getenv("ENABLE_AUTONOMOUS_SCANNING", "true").lower() == "true":
        await start_autonomous_scheduler()
        logger.info("🤖 Autonomous scanning enabled")
    else:
        logger.info("🔧 Autonomous scanning disabled - webhook-only mode")

@app.get("/health")
async def health():
    """
    Health check endpoint — reports status of all critical components.
    Returns 'healthy' if everything is fine, 'degraded' if something is wrong.
    """
    checks = {}

    # Check: database responds
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Check: Docker daemon is reachable (needed for sandbox)
    try:
        import docker
        docker.from_env().ping()
        checks["docker"] = "healthy"
    except Exception:
        checks["docker"] = "unavailable"

    # Check: API keys are configured (we can't test them without making a call)
    checks["groq_api"] = "configured" if config.GROQ_API_KEY else "missing"
    checks["mistral_api"] = "configured" if config.MISTRAL_API_KEY else "missing"
    checks["github_token"] = "configured" if config.GITHUB_TOKEN else "missing"

    # Overall status: degraded if any check is unhealthy or missing
    is_healthy = all(
        v in ("healthy", "configured")
        for v in checks.values()
    )
    overall = "healthy" if is_healthy else "degraded"

    return {"status": overall, "checks": checks, "version": "2.0.0"}


@app.get("/ready")
async def readiness():
    """
    Readiness probe — used by Kubernetes / load balancers.
    Returns 503 if Docker is unavailable (we can't run exploits safely without it).
    """
    try:
        import docker
        docker.from_env().ping()
        return {"ready": True}
    except Exception:
        raise HTTPException(status_code=503, detail="Docker unavailable — not ready to process scans")

@app.post("/webhook/github")
@limiter.limit("30/minute")   # GitHub sends at most a few webhooks per minute per repo
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    if not config.GITHUB_WEBHOOK_SECRET:
        logger.error("Rejecting webhook: GITHUB_WEBHOOK_SECRET is not configured")
        raise HTTPException(
            status_code=503,
            detail="Webhook verification is not configured on the backend",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if not verify_signature(body, signature):
        logger.warning("Invalid webhook signature received.")
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    event_type = request.headers.get("X-GitHub-Event", "")

    # Handle push events
    if event_type == "push":
        payload = json.loads(body)
        push_info = extract_push_info(payload)
        
        logger.info(f"Push received: {push_info['commit_sha'][:8]} on {push_info['repo_name']}")
        logger.info(f"Files changed: {push_info['files_changed']}")
        
        # Run the pipeline in the background so we can respond to GitHub quickly
        background_tasks.add_task(run_aegis_pipeline, push_info)
        
        return {"message": "Webhook received", "commit": push_info["commit_sha"][:8]}

    # Handle pull_request events
    elif event_type == "pull_request":
        payload = json.loads(body)
        action = payload.get("action", "")

        # Only scan on opened or synchronized (new commits pushed to PR)
        if action in ("opened", "synchronize"):
            pr = payload["pull_request"]

            # Security: never scan PRs from forks.
            # A fork PR could contain malicious code targeting Aegis itself
            # (e.g. exploit scripts designed to escape the sandbox).
            head_repo = pr.get("head", {}).get("repo") or {}
            if head_repo.get("fork"):
                logger.warning(
                    f"Ignoring fork PR #{pr['number']} from "
                    f"{head_repo.get('full_name', 'unknown')} — security policy."
                )
                return {"message": "Fork PRs are not scanned for security reasons"}

            push_info = {
                "repo_name": payload["repository"]["full_name"],
                "repo_url": payload["repository"]["clone_url"],
                "commit_sha": pr["head"]["sha"],
                "branch": pr["head"]["ref"],
                "files_changed": [],  # Will be fetched by diff_fetcher
                "is_pr": True,
                "pr_number": pr["number"],
            }
            logger.info(f"PR #{pr['number']} ({action}): {push_info['commit_sha'][:8]} on {push_info['repo_name']}")
            background_tasks.add_task(run_aegis_pipeline, push_info)
            return {"message": "PR scan triggered", "pr": pr["number"]}

        return {"message": f"Ignoring PR action: {action}"}

    else:
        logger.info(f"Ignoring GitHub event type: {event_type}")
        return {"message": f"Ignoring event type: {event_type}"}

@app.on_event("shutdown")
async def on_shutdown():
    """Graceful shutdown handler"""
    logger.info("🛑 Shutting down Aegis...")
    await stop_autonomous_scheduler()


if __name__ == "__main__":
    logger.info(f"Starting Aegis on port {config.PORT}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.PORT,
        reload=False
    )
