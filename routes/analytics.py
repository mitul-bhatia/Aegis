"""
Aegis — Advanced Analytics API

Provides deep insights into security posture, trends, and patterns.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, and_, case

from database.db import SessionLocal
from database.models import Repo, Scan, ScanStatus
from utils.cache import cache_result

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class SecurityTrend(BaseModel):
    date: str
    total_scans: int
    vulnerabilities_found: int
    vulnerabilities_fixed: int
    critical_count: int
    high_count: int
    medium_count: int


class VulnerabilityBreakdown(BaseModel):
    vuln_type: str
    count: int
    severity_distribution: Dict[str, int]
    avg_fix_time_hours: float


class RepoRiskScore(BaseModel):
    repo_id: int
    repo_name: str
    risk_score: float
    total_scans: int
    open_vulnerabilities: int
    last_scan: str


@router.get("/trends", response_model=List[SecurityTrend])
@cache_result("analytics_trends", ttl=300)  # Cache for 5 minutes
async def get_security_trends(days: int = 30):
    """
    Get security trends over time.
    
    Shows daily breakdown of scans, vulnerabilities found/fixed, and severity distribution.
    """
    db = SessionLocal()
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get daily scan statistics
        daily_stats = db.query(
            func.date(Scan.created_at).label('date'),
            func.count(Scan.id).label('total_scans'),
            func.sum(
                case(
                    (Scan.vulnerability_type.isnot(None), 1),
                    else_=0
                )
            ).label('vulnerabilities_found'),
            func.sum(
                case(
                    (Scan.status == ScanStatus.FIXED.value, 1),
                    else_=0
                )
            ).label('vulnerabilities_fixed'),
            func.sum(
                case(
                    (Scan.severity.in_(['CRITICAL', 'ERROR']), 1),
                    else_=0
                )
            ).label('critical_count'),
            func.sum(
                case(
                    (Scan.severity == 'HIGH', 1),
                    else_=0
                )
            ).label('high_count'),
            func.sum(
                case(
                    (Scan.severity.in_(['MEDIUM', 'WARNING']), 1),
                    else_=0
                )
            ).label('medium_count'),
        ).filter(
            Scan.created_at >= start_date
        ).group_by(
            func.date(Scan.created_at)
        ).order_by(
            func.date(Scan.created_at)
        ).all()
        
        return [
            SecurityTrend(
                date=str(stat.date),
                total_scans=stat.total_scans or 0,
                vulnerabilities_found=stat.vulnerabilities_found or 0,
                vulnerabilities_fixed=stat.vulnerabilities_fixed or 0,
                critical_count=stat.critical_count or 0,
                high_count=stat.high_count or 0,
                medium_count=stat.medium_count or 0,
            )
            for stat in daily_stats
        ]
    finally:
        db.close()


@router.get("/vulnerability-breakdown", response_model=List[VulnerabilityBreakdown])
@cache_result("analytics_vuln_breakdown", ttl=600)  # Cache for 10 minutes
async def get_vulnerability_breakdown():
    """
    Get breakdown of vulnerability types with severity distribution and avg fix time.
    """
    db = SessionLocal()
    try:
        # Get vulnerability type statistics
        vuln_stats = db.query(
            Scan.vulnerability_type,
            Scan.severity,
            func.count(Scan.id).label('count'),
            func.avg(
                func.extract('epoch', Scan.completed_at - Scan.created_at) / 3600
            ).label('avg_fix_time_hours')
        ).filter(
            Scan.vulnerability_type.isnot(None)
        ).group_by(
            Scan.vulnerability_type,
            Scan.severity
        ).all()
        
        # Organize by vulnerability type
        vuln_map = {}
        for stat in vuln_stats:
            if stat.vulnerability_type not in vuln_map:
                vuln_map[stat.vulnerability_type] = {
                    'count': 0,
                    'severity_distribution': {},
                    'fix_times': []
                }
            
            vuln_map[stat.vulnerability_type]['count'] += stat.count
            vuln_map[stat.vulnerability_type]['severity_distribution'][stat.severity or 'UNKNOWN'] = stat.count
            if stat.avg_fix_time_hours:
                vuln_map[stat.vulnerability_type]['fix_times'].append(stat.avg_fix_time_hours)
        
        # Convert to response format
        result = []
        for vuln_type, data in vuln_map.items():
            avg_fix_time = sum(data['fix_times']) / len(data['fix_times']) if data['fix_times'] else 0
            result.append(VulnerabilityBreakdown(
                vuln_type=vuln_type,
                count=data['count'],
                severity_distribution=data['severity_distribution'],
                avg_fix_time_hours=round(avg_fix_time, 2)
            ))
        
        return sorted(result, key=lambda x: x.count, reverse=True)
    finally:
        db.close()


@router.get("/repo-risk-scores", response_model=List[RepoRiskScore])
@cache_result("analytics_repo_risk", ttl=600)  # Cache for 10 minutes
async def get_repo_risk_scores():
    """
    Calculate risk scores for all repositories based on scan history.
    
    Risk score factors:
    - Number of open vulnerabilities
    - Severity of vulnerabilities
    - Time since last scan
    - Fix rate
    """
    db = SessionLocal()
    try:
        repos = db.query(Repo).all()
        risk_scores = []
        
        for repo in repos:
            # Get scan statistics
            total_scans = db.query(Scan).filter(Scan.repo_id == repo.id).count()
            
            if total_scans == 0:
                continue
            
            # Count open vulnerabilities
            open_vulns = db.query(Scan).filter(
                Scan.repo_id == repo.id,
                Scan.status.in_([
                    ScanStatus.EXPLOIT_CONFIRMED.value,
                    ScanStatus.PATCHING.value,
                    ScanStatus.AWAITING_APPROVAL.value,
                    ScanStatus.FAILED.value,
                ])
            ).count()
            
            # Get last scan
            last_scan = db.query(Scan).filter(
                Scan.repo_id == repo.id
            ).order_by(Scan.created_at.desc()).first()
            
            # Calculate risk score (0-100)
            days_since_scan = 999  # Default to very old
            if last_scan and last_scan.created_at:
                # Make last_scan.created_at timezone-aware if it isn't
                scan_time = last_scan.created_at
                if scan_time.tzinfo is None:
                    scan_time = scan_time.replace(tzinfo=timezone.utc)
                days_since_scan = (datetime.now(timezone.utc) - scan_time).days
            
            risk_score = min(100, (
                open_vulns * 10 +  # Each open vuln adds 10 points
                (30 if days_since_scan > 7 else 0)  # No recent scan
            ))
            
            risk_scores.append(RepoRiskScore(
                repo_id=repo.id,
                repo_name=repo.full_name,
                risk_score=risk_score,
                total_scans=total_scans,
                open_vulnerabilities=open_vulns,
                last_scan=str(last_scan.created_at) if last_scan else "Never"
            ))
        
        return sorted(risk_scores, key=lambda x: x.risk_score, reverse=True)
    finally:
        db.close()
