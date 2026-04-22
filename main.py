import json
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import config
from database.db import init_db
from github_integration.webhook import verify_signature, extract_push_info
from orchestrator import run_aegis_pipeline
from routes.auth import router as auth_router
from routes.repos import router as repos_router
from routes.scans import router as scans_router

# Initialize configuration
config.setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Security System")

# CORS — allow the Next.js frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount new API routes
app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(scans_router)

# Create database tables on startup
@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized")

@app.get("/health")
async def health():
    return {"status": "Aegis is running", "version": "0.1.0"}

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
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

if __name__ == "__main__":
    logger.info(f"Starting Aegis on port {config.PORT}...")
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
