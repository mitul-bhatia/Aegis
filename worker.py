"""
Aegis — Asynchronous Redis Background Task Worker

Pulls scan jobs from REDIS_URL and executes run_aegis_pipeline off the main FastAPI web server thread.
Can be launched in production as a standalone worker process:
    python worker.py
"""

import os
import json
import time
import logging
import redis

import config
from orchestrator import run_aegis_pipeline
from notifications.alert_manager import send_scan_alert

logger = logging.getLogger(__name__)

QUEUE_NAME = "aegis_scans_queue"


def get_redis_client():
    """Connect to Redis instance defined by config.REDIS_URL."""
    if config.REDIS_URL.startswith("rediss://"):
        return redis.from_url(config.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
    return redis.from_url(config.REDIS_URL, decode_responses=True)



def enqueue_scan_job(push_info: dict) -> bool:
    """Push a scan job payload into Redis task queue."""
    try:
        r = get_redis_client()
        r.rpush(QUEUE_NAME, json.dumps(push_info))
        logger.info(f"Enqueued scan job for {push_info.get('repo_name')} ({push_info.get('commit_sha', '')[:8]}) to Redis")
        return True
    except Exception as e:
        logger.error(f"Failed to enqueue scan job to Redis: {e}")
        return False


def start_worker():
    """
    Main worker loop — continuously pops and executes scan jobs.
    """
    logger.info("🤖 Starting Aegis Redis Background Scan Worker...")
    logger.info(f"Connecting to Redis at: {config.REDIS_URL}")
    
    r = None
    while True:
        try:
            r = get_redis_client()
            r.ping()
            logger.info("✓ Connected to Redis worker queue successfully.")
            break
        except Exception as e:
            logger.error(f"Cannot connect to Redis at {config.REDIS_URL}: {e}. Retrying in 10s...")
            time.sleep(10)
    
    while True:
        try:
            # Blocking pop with 5 second timeout
            item = r.blpop(QUEUE_NAME, timeout=5)
            if not item:
                continue

            _, payload_str = item
            push_info = json.loads(payload_str)
            repo_name = push_info.get("repo_name", "unknown")
            commit_sha = push_info.get("commit_sha", "")[:8]

            logger.info(f"⚡ Worker picked up scan job for {repo_name} [{commit_sha}]")
            
            # Execute 7-agent pipeline
            result = run_aegis_pipeline(push_info)
            
            # Send Slack / Discord alerts on completion if vulnerability fixed
            if result and isinstance(result, dict) and result.get("pr_url"):
                send_scan_alert(
                    repo_name=repo_name,
                    vulnerability_type=result.get("vulnerability_type", "Security Bug"),
                    severity=result.get("severity", "HIGH"),
                    vulnerable_file=result.get("vulnerable_file", "Codebase"),
                    pr_url=result.get("pr_url"),
                )

        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in background worker execution: {e}")
            time.sleep(5)



if __name__ == "__main__":
    config.setup_logging()
    start_worker()
