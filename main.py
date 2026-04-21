import json
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import uvicorn

import config
from github.webhook import verify_signature, extract_push_info
from orchestrator import run_aegis_pipeline

# Initialize configuration
config.setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Security System")

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
    if event_type != "push":
        logger.info(f"Ignoring GitHub event type: {event_type}")
        return {"message": f"Ignoring event type: {event_type}"}
        
    payload = json.loads(body)
    push_info = extract_push_info(payload)
    
    logger.info(f"Push received: {push_info['commit_sha'][:8]} on {push_info['repo_name']}")
    logger.info(f"Files changed: {push_info['files_changed']}")
    
    # Run the pipeline in the background so we can respond to GitHub quickly
    background_tasks.add_task(run_aegis_pipeline, push_info)
    
    return {"message": "Webhook received", "commit": push_info["commit_sha"][:8]}

if __name__ == "__main__":
    logger.info(f"Starting Aegis on port {config.PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT, reload=True)
