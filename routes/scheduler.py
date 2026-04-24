"""
Aegis Scheduler Control Routes

Provides API endpoints to control autonomous scanning:
- GET /api/scheduler/status - Get scheduler status
- POST /api/scheduler/start - Start autonomous scanning
- POST /api/scheduler/stop - Stop autonomous scanning
- POST /api/scheduler/scan-now - Trigger immediate scan of all repos
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scheduler import scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class SchedulerStatusResponse(BaseModel):
    running: bool
    scan_interval_hours: int
    next_scan_in: int  # minutes until next scan


class ScanNowRequest(BaseModel):
    pass


@router.get("/status", response_model=SchedulerStatusResponse)
def get_scheduler_status():
    """Get current scheduler status"""
    return SchedulerStatusResponse(
        running=scheduler.running,
        scan_interval_hours=scheduler.scan_interval,
        next_scan_in=0 if not scheduler.running else scheduler.scan_interval * 60
    )


@router.post("/start")
async def start_scheduler():
    """Start autonomous scanning"""
    if scheduler.running:
        raise HTTPException(status_code=400, detail="Scheduler already running")
    
    await scheduler.start()
    logger.info("🚀 Autonomous scanning started via API")
    return {"message": "Autonomous scanning started"}


@router.post("/stop")
async def stop_scheduler():
    """Stop autonomous scanning"""
    if not scheduler.running:
        raise HTTPException(status_code=400, detail="Scheduler not running")
    
    await scheduler.stop()
    logger.info("🛑 Autonomous scanning stopped via API")
    return {"message": "Autonomous scanning stopped"}


@router.post("/scan-now")
async def trigger_scan_now():
    """Trigger immediate scan of all repositories"""
    if scheduler.running:
        raise HTTPException(status_code=400, detail="Cannot trigger manual scan while scheduler is running")
    
    await scheduler._scan_all_repos()
    logger.info("⚡ Manual scan triggered via API")
    return {"message": "Manual scan triggered"}
