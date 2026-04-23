#!/usr/bin/env python3
"""
Manual test to trigger the Aegis pipeline without relying on GitHub webhooks.
This simulates a push event and runs the full 4-agent pipeline.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import run_aegis_pipeline
from database.db import SessionLocal
from database.models import Repo
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_manual_trigger():
    """Manually trigger a scan on the test repo"""
    
    # Get the test repo from database
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.full_name == "mitu1046/aegis-test-repo").first()
        
        if not repo:
            logger.error("Test repo not found in database!")
            logger.info("Available repos:")
            for r in db.query(Repo).all():
                logger.info(f"  - {r.full_name} (ID: {r.id})")
            return
        
        logger.info(f"Found repo: {repo.full_name} (ID: {repo.id})")
        logger.info(f"Webhook ID: {repo.webhook_id}")
        logger.info(f"Status: {repo.status}")
        
        # Use the real commit SHA from the latest push
        # Get latest commit from GitHub API
        import requests
        api_url = f"https://api.github.com/repos/{repo.full_name}/commits/main"
        response = requests.get(api_url)
        if response.status_code != 200:
            logger.error(f"Failed to get latest commit: {response.status_code}")
            return
        
        commit_data = response.json()
        commit_sha = commit_data["sha"]
        files_changed = [f["filename"] for f in commit_data["files"]]
        
        logger.info(f"Latest commit: {commit_sha[:8]}")
        logger.info(f"Files changed: {files_changed}")
        
        # Create a real push event
        push_info = {
            "repo_name": repo.full_name,
            "repo_url": f"https://github.com/{repo.full_name}.git",
            "commit_sha": commit_sha,
            "branch": "main",
            "files_changed": files_changed,
            "is_pr": False,
        }
        
        logger.info("\n" + "="*60)
        logger.info("MANUALLY TRIGGERING AEGIS PIPELINE")
        logger.info("="*60)
        logger.info(f"Repo: {push_info['repo_name']}")
        logger.info(f"Branch: {push_info['branch']}")
        logger.info(f"Files: {push_info['files_changed']}")
        logger.info("="*60 + "\n")
        
        # Run the pipeline (it's not async, so just call it directly)
        run_aegis_pipeline(push_info)
        
        logger.info("\n" + "="*60)
        logger.info("PIPELINE COMPLETED")
        logger.info("="*60)
        logger.info("Check the dashboard at http://localhost:3000/dashboard")
        logger.info("="*60 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_manual_trigger()
