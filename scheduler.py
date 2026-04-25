"""
Aegis Autonomous Scheduler

Provides continuous, autonomous scanning of repositories:
- Periodic scanning of all monitored repos
- Configurable scan intervals
- Background task management
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import List

import config
from database.db import SessionLocal
from database.models import Repo, Scan
from orchestrator import run_aegis_pipeline

logger = logging.getLogger(__name__)


class AegisScheduler:
    """Autonomous scheduler for continuous security scanning"""
    
    def __init__(self):
        self.running = False
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_HOURS", "24"))  # Default: daily
        self.background_task = None
    
    async def start(self):
        """Start the autonomous scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        logger.info(f"🤖 Aegis Scheduler started - scanning every {self.scan_interval} hours")
        
        self.background_task = asyncio.create_task(self._run_scheduler())
    
    async def stop(self):
        """Stop the autonomous scheduler"""
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            logger.info("🛑 Aegis Scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        # Wait for the server to fully start before running the first scan
        logger.info("⏳ Scheduler: waiting 30s before first scan...")
        await asyncio.sleep(30)

        while self.running:
            try:
                await self._scan_all_repos()
                # Sleep until next scan
                await asyncio.sleep(self.scan_interval * 3600)  # Convert hours to seconds
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _scan_all_repos(self):
        """Scan all monitored repositories"""
        db = SessionLocal()
        try:
            repos = db.query(Repo).filter(Repo.is_indexed == True).all()
            repo_data = [{"id": r.id, "full_name": r.full_name} for r in repos]
        finally:
            db.close()
            
        if not repo_data:
            logger.info("No indexed repositories found")
            return
            
        logger.info(f"🔍 Starting autonomous scan of {len(repo_data)} repositories")
        
        for repo_info in repo_data:
            repo_id = repo_info["id"]
            full_name = repo_info["full_name"]
            
            try:
                # Run the entire per-repo scan in a thread to avoid blocking the event loop
                await asyncio.to_thread(self._scan_single_repo, repo_id, full_name)
            except Exception as e:
                logger.error(f"Failed to scan {full_name}: {e}")

    def _scan_single_repo(self, repo_id: int, full_name: str):
        """Scan a single repo — runs in a background thread."""
        # Check if recent scan exists
        db = SessionLocal()
        try:
            recent_scan = db.query(Scan).filter(
                Scan.repo_id == repo_id,
                Scan.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            ).first()
            
            if recent_scan:
                logger.debug(f"Skipping {full_name} - already scanned today")
                return
        finally:
            db.close()
        
        # Fetch actual latest commit from GitHub
        try:
            from github import Github
            import config
            g = Github(config.GITHUB_TOKEN)
            github_repo = g.get_repo(full_name)
            default_branch = github_repo.default_branch
            commit_sha = github_repo.get_branch(default_branch).commit.sha
            
            # Get files changed in this commit
            commit = github_repo.get_commit(commit_sha)
            files_changed = [f.filename for f in commit.files]
        except Exception as gh_err:
            logger.error(f"Failed to fetch latest commit for {full_name}: {gh_err}")
            return
        
        # Create scan info for pipeline
        scan_info = {
            "repo_name": full_name,
            "repo_url": f"https://github.com/{full_name}",
            "commit_sha": commit_sha,
            "branch": default_branch,
            "files_changed": files_changed,
            "is_autonomous": True,  # Mark as autonomous scan
        }
        
        logger.info(f"🚀 Autonomous scan: {full_name} @ {commit_sha[:8]}")
        run_aegis_pipeline(scan_info)


# Global scheduler instance
scheduler = AegisScheduler()


async def start_autonomous_scheduler():
    """Start the autonomous scheduler (call from main.py)"""
    await scheduler.start()


async def stop_autonomous_scheduler():
    """Stop the autonomous scheduler (call from main.py)"""
    await scheduler.stop()
