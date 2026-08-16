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
from notifications.alert_manager import notify_scan_event, ScanEvent

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
    
    PROCESSING_QUEUE = f"{QUEUE_NAME}_processing"

    while True:
        try:
            # Reliable Queue Pattern: move from pending to processing atomically
            # timeout=5 means wait 5s for an item. If timeout, returns None
            payload_str = r.brpoplpush(QUEUE_NAME, PROCESSING_QUEUE, timeout=5)
            if not payload_str:
                continue

            # If payload_str is bytes (which it usually is from redis), decode it
            if isinstance(payload_str, bytes):
                payload_str = payload_str.decode("utf-8")

            push_info = json.loads(payload_str)
            repo_name = push_info.get("repo_name", "unknown")
            commit_sha = push_info.get("commit_sha", "")[:8]

            logger.info(f"⚡ Worker picked up scan job for {repo_name} @ {commit_sha}")
            start_t = time.time()
            
            try:
                result = run_aegis_pipeline(push_info)
                elapsed = time.time() - start_t
                logger.info(f"✅ Worker successfully completed scan for {repo_name} @ {commit_sha} in {elapsed:.1f}s")
                
                if result and isinstance(result, dict) and result.get("pr_url"):
                    event = ScanEvent(
                        scan_id=0,  # worker doesn't have scan_id directly here
                        repo_name=repo_name,
                        status="fixed",
                        vulnerability_type=result.get("vulnerability_type", "Security Bug"),
                        severity=result.get("severity", "HIGH"),
                        vulnerable_file=result.get("vulnerable_file", "Codebase"),
                        pr_url=result.get("pr_url"),
                        error_message=None,
                        scan_url=f"{config.FRONTEND_URL}/dashboard"
                    )
                    notify_scan_event(event)
            except Exception as e:
                elapsed = time.time() - start_t
                logger.error(f"❌ Worker pipeline failed for {repo_name} @ {commit_sha} after {elapsed:.1f}s: {e}")
            finally:
                # Remove from processing queue regardless of success/failure 
                # (so it doesn't stay stuck forever, though in a real distributed system we might move it to a DLQ)
                r.lrem(PROCESSING_QUEUE, 0, payload_str)

        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in background worker execution: {e}")
            time.sleep(5)


import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

def start_dummy_server():
    """
    Render requires Web Services to bind to a port, otherwise the deploy fails.
    If the worker is deployed as a Web Service (e.g. on Render Free Tier),
    this dummy server listens on $PORT to satisfy the health check.
    """
    port = int(os.environ.get("PORT", 10000))
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Worker is running")
    
    try:
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        logger.info(f"Started dummy HTTP server on port {port} to satisfy Render Web Service checks")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start dummy server: {e}")

if __name__ == "__main__":
    config.setup_logging()
    
    # If PORT is in the environment, we might be deployed as a Web Service on Render
    if os.environ.get("PORT"):
        threading.Thread(target=start_dummy_server, daemon=True).start()
        
    start_worker()
