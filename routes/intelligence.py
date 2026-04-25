"""
Aegis Intelligence API Routes

Provides endpoints for threat intelligence, ML predictions, and security insights.
These endpoints power the Intelligence Dashboard and enhanced repo cards.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.db import SessionLocal
from database.models import Repo, Scan, ScanStatus
from scheduler_module.intelligent_scheduler import intelligent_scheduler
from intelligence.threat_engine import ThreatIntelligenceEngine
from ml.vulnerability_predictor import VulnerabilityPredictor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])

# Initialize intelligence components
threat_engine = ThreatIntelligenceEngine()
vulnerability_predictor = VulnerabilityPredictor()


# ── Response Models ──────────────────────────────────────

class RepoIntelligenceResponse(BaseModel):
    """Intelligence data for a single repository"""
    repo_id: int
    repo_name: str
    threat_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    critical_threats: int
    high_threats: int
    medium_threats: int
    predicted_risk: float  # 0.0-1.0
    vulnerability_density: float  # vulnerabilities per 1K lines
    activity_score: float  # 0.0-1.0
    business_impact: float  # 0.0-1.0
    adaptive_interval_hours: float
    last_scan: Optional[str]
    next_scan_in_minutes: Optional[int]


class GlobalThreatResponse(BaseModel):
    """Global threat intelligence across all repositories"""
    level: str  # CRITICAL, HIGH, MEDIUM, LOW
    emergency_repos: List[str]
    total_threats: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class MLPredictionResponse(BaseModel):
    """ML prediction for a repository"""
    repo_id: int
    repo_name: str
    risk_score: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    factors: List[str]


class PredictionsResponse(BaseModel):
    """All ML predictions"""
    high_risk_repos: List[MLPredictionResponse]
    accuracy: float
    total_predictions: int
    false_positives: int
    false_negatives: int


class SchedulerInsightsResponse(BaseModel):
    """Detailed scheduler performance insights"""
    total_scans: int
    repo_patterns: int
    avg_scan_duration: float
    threat_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    scans_today: int
    vulnerabilities_found_today: int
    vulnerabilities_fixed_today: int


# ── Helper Functions ──────────────────────────────────────

def _calculate_vulnerability_density(repo_id: int, db) -> float:
    """Calculate vulnerability density for a repository"""
    # Get scans from last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    scans = db.query(Scan).filter(
        Scan.repo_id == repo_id,
        Scan.created_at >= thirty_days_ago
    ).all()
    
    if not scans:
        return 0.0
    
    # Count vulnerabilities found
    vuln_count = sum(1 for scan in scans if scan.vulnerability_type is not None)
    
    # Estimate lines of code (simplified - could be enhanced)
    estimated_loc = 10000  # Default estimate
    
    # Calculate density (vulnerabilities per 1000 lines)
    if estimated_loc > 0:
        density = (vuln_count / len(scans)) / (estimated_loc / 1000)
        return min(density, 10.0)  # Cap at 10.0
    
    return 0.0


def _calculate_activity_score(repo_id: int, db) -> float:
    """Calculate repository activity score based on recent scans"""
    # Count scans in last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_scans = db.query(Scan).filter(
        Scan.repo_id == repo_id,
        Scan.created_at >= seven_days_ago
    ).count()
    
    # Normalize to 0-1 scale (10+ scans = 1.0)
    activity_score = min(recent_scans / 10.0, 1.0)
    return activity_score


def _assess_business_impact(repo_name: str) -> float:
    """Assess business impact based on repository name patterns"""
    name_lower = repo_name.lower()
    
    # High impact keywords
    if any(keyword in name_lower for keyword in ['prod', 'production', 'main', 'core', 'api', 'payment']):
        return 0.9
    
    # Medium impact keywords
    elif any(keyword in name_lower for keyword in ['staging', 'dev', 'service']):
        return 0.6
    
    # Low impact keywords
    elif any(keyword in name_lower for keyword in ['test', 'demo', 'sandbox', 'example']):
        return 0.3
    
    # Default medium impact
    return 0.5


def _calculate_adaptive_interval(
    base_interval: float,
    activity_score: float,
    predicted_risk: float
) -> float:
    """Calculate adaptive scan interval based on activity and risk"""
    # Activity multiplier: more active repos scanned more frequently
    activity_multiplier = 1.0 + (activity_score * 0.5)
    
    # Risk multiplier: higher risk repos scanned more frequently
    risk_multiplier = 1.0 + (predicted_risk * 0.3)
    
    # Calculate adjusted interval
    adjusted_interval = base_interval / (activity_multiplier * risk_multiplier)
    
    # Ensure minimum interval of 1 hour
    return max(adjusted_interval, 1.0)


# ── API Endpoints ──────────────────────────────────────────

@router.get("/repo/{repo_id}", response_model=RepoIntelligenceResponse)
async def get_repo_intelligence(repo_id: int):
    """
    Get comprehensive intelligence data for a specific repository.
    
    Returns threat assessment, ML predictions, vulnerability metrics,
    activity analysis, and adaptive scheduling information.
    """
    db = SessionLocal()
    try:
        # Get repository
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Get threat intelligence
        threat_intel = await threat_engine.get_repo_threats(repo.full_name)
        
        # Get ML risk prediction
        predicted_risk = await vulnerability_predictor.predict_repo_risk(repo)
        
        # Calculate metrics
        vulnerability_density = _calculate_vulnerability_density(repo_id, db)
        activity_score = _calculate_activity_score(repo_id, db)
        business_impact = _assess_business_impact(repo.full_name)
        
        # Get last scan
        last_scan = db.query(Scan).filter(
            Scan.repo_id == repo_id
        ).order_by(Scan.created_at.desc()).first()
        
        # Calculate adaptive interval
        base_interval = intelligent_scheduler.scan_interval
        adaptive_interval = _calculate_adaptive_interval(
            base_interval,
            activity_score,
            predicted_risk
        )
        
        # Calculate next scan time
        next_scan_in_minutes = None
        if last_scan:
            # Ensure last_scan.created_at is timezone-aware
            scan_time = last_scan.created_at
            if scan_time.tzinfo is None:
                scan_time = scan_time.replace(tzinfo=timezone.utc)
            
            time_since_scan = datetime.now(timezone.utc) - scan_time
            time_until_next = timedelta(hours=adaptive_interval) - time_since_scan
            next_scan_in_minutes = max(int(time_until_next.total_seconds() / 60), 0)
        
        return RepoIntelligenceResponse(
            repo_id=repo.id,
            repo_name=repo.full_name,
            threat_level=threat_intel.level,
            critical_threats=threat_intel.critical_threats,
            high_threats=threat_intel.high_threats,
            medium_threats=threat_intel.medium_threats,
            predicted_risk=predicted_risk,
            vulnerability_density=vulnerability_density,
            activity_score=activity_score,
            business_impact=business_impact,
            adaptive_interval_hours=adaptive_interval,
            last_scan=last_scan.created_at.isoformat() if last_scan else None,
            next_scan_in_minutes=next_scan_in_minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repo intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/global", response_model=GlobalThreatResponse)
async def get_global_threat_level():
    """
    Get global threat intelligence across all repositories.
    
    Returns overall threat level, emergency repositories,
    and threat count breakdown by severity.
    """
    try:
        # Get global threat level
        global_level = await threat_engine.get_global_threat_level()
        
        # Get emergency repositories
        emergency_repos = await threat_engine.get_emergency_repos()
        
        # Get threat counts by severity
        db = SessionLocal()
        try:
            # Count active scans with vulnerabilities by severity
            critical_count = db.query(Scan).filter(
                Scan.severity == "CRITICAL",
                Scan.status.in_([ScanStatus.EXPLOIT_CONFIRMED.value, ScanStatus.PATCHING.value])
            ).count()
            
            high_count = db.query(Scan).filter(
                Scan.severity == "HIGH",
                Scan.status.in_([ScanStatus.EXPLOIT_CONFIRMED.value, ScanStatus.PATCHING.value])
            ).count()
            
            medium_count = db.query(Scan).filter(
                Scan.severity == "MEDIUM",
                Scan.status.in_([ScanStatus.EXPLOIT_CONFIRMED.value, ScanStatus.PATCHING.value])
            ).count()
            
            low_count = db.query(Scan).filter(
                Scan.severity == "LOW",
                Scan.status.in_([ScanStatus.EXPLOIT_CONFIRMED.value, ScanStatus.PATCHING.value])
            ).count()
            
            total_threats = critical_count + high_count + medium_count + low_count
            
        finally:
            db.close()
        
        return GlobalThreatResponse(
            level=global_level,
            emergency_repos=emergency_repos,
            total_threats=total_threats,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count
        )
        
    except Exception as e:
        logger.error(f"Error getting global threat level: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions", response_model=PredictionsResponse)
async def get_ml_predictions():
    """
    Get ML risk predictions for all repositories.
    
    Returns high-risk repositories with confidence scores,
    model accuracy metrics, and prediction statistics.
    """
    db = SessionLocal()
    try:
        # Get all indexed repositories
        repos = db.query(Repo).filter(Repo.is_indexed == True).all()
        
        # Generate predictions for each repo
        predictions = []
        for repo in repos:
            risk_score = await vulnerability_predictor.predict_repo_risk(repo)
            
            # Only include high-risk repos (risk > 0.6)
            if risk_score > 0.6:
                # Get contributing factors
                factors = await vulnerability_predictor.get_risk_factors(repo)

                # Confidence scales with scan history depth (more data = more confident)
                scan_count = db.query(Scan).filter(Scan.repo_id == repo.id).count()
                confidence = round(min(0.5 + scan_count / 20, 0.95), 2)

                predictions.append(MLPredictionResponse(
                    repo_id=repo.id,
                    repo_name=repo.full_name,
                    risk_score=risk_score,
                    confidence=confidence,
                    factors=factors,
                ))
        
        # Sort by risk score descending
        predictions.sort(key=lambda x: x.risk_score, reverse=True)
        
        # Get model accuracy metrics
        accuracy = await vulnerability_predictor.get_accuracy()
        total_predictions = await vulnerability_predictor.get_total_predictions()
        false_positives = await vulnerability_predictor.get_false_positives()
        false_negatives = await vulnerability_predictor.get_false_negatives()
        
        return PredictionsResponse(
            high_risk_repos=predictions,
            accuracy=accuracy,
            total_predictions=total_predictions,
            false_positives=false_positives,
            false_negatives=false_negatives
        )
        
    except Exception as e:
        logger.error(f"Error getting ML predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/scheduler/insights", response_model=SchedulerInsightsResponse)
async def get_scheduler_insights():
    """
    Get detailed scheduler performance insights.
    
    Returns scan statistics, priority distribution,
    performance metrics, and daily activity.
    """
    try:
        # Get insights from intelligent scheduler
        insights = await intelligent_scheduler.get_scheduling_insights()
        
        # Get today's statistics
        db = SessionLocal()
        try:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            scans_today = db.query(Scan).filter(
                Scan.created_at >= today_start
            ).count()
            
            vulnerabilities_found_today = db.query(Scan).filter(
                Scan.created_at >= today_start,
                Scan.vulnerability_type.isnot(None)
            ).count()
            
            vulnerabilities_fixed_today = db.query(Scan).filter(
                Scan.created_at >= today_start,
                Scan.status == ScanStatus.FIXED.value
            ).count()
            
        finally:
            db.close()
        
        # Priority distribution from actual scan data
        priority_distribution = {
            "CRITICAL": db.query(Scan).filter(Scan.severity.in_(["CRITICAL", "ERROR"])).count(),
            "HIGH":     db.query(Scan).filter(Scan.severity == "HIGH").count(),
            "MEDIUM":   db.query(Scan).filter(Scan.severity.in_(["MEDIUM", "WARNING"])).count(),
            "LOW":      db.query(Scan).filter(Scan.severity == "LOW").count(),
            "ROUTINE":  db.query(Scan).filter(Scan.severity.is_(None)).count(),
        }
        
        return SchedulerInsightsResponse(
            total_scans=insights.get("total_scans", 0),
            repo_patterns=insights.get("repo_patterns", 0),
            avg_scan_duration=insights.get("avg_scan_duration", 0.0),
            threat_distribution=insights.get("threat_distribution", {}),
            priority_distribution=priority_distribution,
            scans_today=scans_today,
            vulnerabilities_found_today=vulnerabilities_found_today,
            vulnerabilities_fixed_today=vulnerabilities_fixed_today
        )
        
    except Exception as e:
        logger.error(f"Error getting scheduler insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ── Analytics Endpoint ────────────────────────────────────

@router.get("/analytics")
async def get_analytics(user_id: int, days: int = 30):
    """
    Aggregated security analytics for the dashboard analytics page.

    Returns:
    - vuln_trend    : daily counts of vulns found and fixed
    - top_vulns     : most common vulnerability types
    - mttr_hours    : mean time to remediation (hours)
    - fix_rate      : fraction of found vulns that were fixed
    - severity_dist : breakdown by severity
    - total_scans   : total scans in the period
    - regressions   : count of regression scans
    """
    from sqlalchemy import func

    db = SessionLocal()
    try:
        # Get repos for this user
        repos = db.query(Repo).filter(Repo.user_id == user_id).all()
        repo_ids = [r.id for r in repos]

        if not repo_ids:
            return _empty_analytics()

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # All scans in the period
        scans = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids),
            Scan.created_at >= cutoff,
        ).order_by(Scan.created_at.asc()).all()

        # ── Vulnerability trend (daily) ───────────────────
        trend: dict[str, dict] = {}
        for scan in scans:
            day = scan.created_at.strftime("%Y-%m-%d")
            if day not in trend:
                trend[day] = {"date": day, "found": 0, "fixed": 0}
            if scan.vulnerability_type:
                trend[day]["found"] += 1
            if scan.status == ScanStatus.FIXED.value:
                trend[day]["fixed"] += 1

        vuln_trend = list(trend.values())

        # ── Top vulnerability types ───────────────────────
        vuln_counts = (
            db.query(Scan.vulnerability_type, func.count(Scan.id).label("count"))
            .filter(
                Scan.repo_id.in_(repo_ids),
                Scan.created_at >= cutoff,
                Scan.vulnerability_type.isnot(None),
            )
            .group_by(Scan.vulnerability_type)
            .order_by(func.count(Scan.id).desc())
            .limit(8)
            .all()
        )
        top_vulns = [{"type": vt, "count": cnt} for vt, cnt in vuln_counts]

        # ── Severity distribution ─────────────────────────
        sev_counts = (
            db.query(Scan.severity, func.count(Scan.id).label("count"))
            .filter(
                Scan.repo_id.in_(repo_ids),
                Scan.created_at >= cutoff,
                Scan.severity.isnot(None),
            )
            .group_by(Scan.severity)
            .all()
        )
        severity_dist = {sev: cnt for sev, cnt in sev_counts}

        # ── MTTR (mean time to remediation) ──────────────
        # For fixed scans: time from created_at to completed_at
        fixed_scans = [s for s in scans if s.status == ScanStatus.FIXED.value and s.completed_at]
        mttr_hours = 0.0
        if fixed_scans:
            durations = []
            for s in fixed_scans:
                created = s.created_at
                completed = s.completed_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=timezone.utc)
                delta = (completed - created).total_seconds() / 3600
                if delta >= 0:
                    durations.append(delta)
            if durations:
                mttr_hours = round(sum(durations) / len(durations), 2)

        # ── Fix rate ──────────────────────────────────────
        vuln_scans = [s for s in scans if s.vulnerability_type and s.status != ScanStatus.FALSE_POSITIVE.value]
        fixed_count = len([s for s in vuln_scans if s.status == ScanStatus.FIXED.value])
        fix_rate = round(fixed_count / len(vuln_scans), 2) if vuln_scans else 0.0

        # ── Regression count ──────────────────────────────
        regression_count = sum(1 for s in scans if getattr(s, "is_regression", False))

        return {
            "vuln_trend": vuln_trend,
            "top_vulns": top_vulns,
            "severity_dist": severity_dist,
            "mttr_hours": mttr_hours,
            "fix_rate": fix_rate,
            "total_scans": len(scans),
            "total_vulns_found": len(vuln_scans),
            "total_fixed": fixed_count,
            "regressions": regression_count,
            "period_days": days,
        }

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


def _empty_analytics() -> dict:
    return {
        "vuln_trend": [],
        "top_vulns": [],
        "severity_dist": {},
        "mttr_hours": 0.0,
        "fix_rate": 0.0,
        "total_scans": 0,
        "total_vulns_found": 0,
        "total_fixed": 0,
        "regressions": 0,
        "period_days": 30,
    }


# ── Security Scorecard Endpoint ───────────────────────────

@router.get("/scorecard/{repo_id}")
async def get_security_scorecard(repo_id: int):
    """
    Generate a letter-grade security scorecard for a repository.

    Grade is computed from five weighted dimensions:
    - Vulnerability rate   (30%) — how often vulns are found per scan
    - Fix rate             (25%) — fraction of vulns that get fixed
    - MTTR                 (20%) — mean time to remediation (lower = better)
    - Open severity        (15%) — unresolved CRITICAL/HIGH vulns
    - Regression rate      (10%) — how often fixed vulns reappear

    Returns grade (A-F), score (0-100), and per-dimension breakdown.
    """
    from sqlalchemy import func

    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        all_scans = db.query(Scan).filter(
            Scan.repo_id == repo_id,
            Scan.created_at >= thirty_days_ago,
        ).all()

        total = len(all_scans)

        if total == 0:
            return {
                "repo_id": repo_id,
                "repo_name": repo.full_name,
                "grade": "N/A",
                "score": None,
                "dimensions": {},
                "open_vulns": 0,
                "message": "No scans in the last 30 days",
            }

        # ── Dimension 1: Vulnerability rate (lower = better) ──
        vuln_scans = [s for s in all_scans if s.vulnerability_type and s.status != ScanStatus.FALSE_POSITIVE.value]
        vuln_rate = len(vuln_scans) / total  # 0–1
        vuln_score = round((1 - vuln_rate) * 100)  # 100 = no vulns

        # ── Dimension 2: Fix rate (higher = better) ───────────
        fixed = [s for s in vuln_scans if s.status == ScanStatus.FIXED.value]
        fix_rate = len(fixed) / len(vuln_scans) if vuln_scans else 1.0
        fix_score = round(fix_rate * 100)

        # ── Dimension 3: MTTR (lower = better) ────────────────
        # Score 100 if < 1h, 0 if > 48h, linear in between
        mttr_hours = 0.0
        fixed_with_time = [s for s in fixed if s.completed_at]
        if fixed_with_time:
            durations = []
            for s in fixed_with_time:
                created = s.created_at.replace(tzinfo=timezone.utc) if s.created_at.tzinfo is None else s.created_at
                completed = s.completed_at.replace(tzinfo=timezone.utc) if s.completed_at.tzinfo is None else s.completed_at
                delta = (completed - created).total_seconds() / 3600
                if delta >= 0:
                    durations.append(delta)
            if durations:
                mttr_hours = sum(durations) / len(durations)

        mttr_score = max(0, round(100 - (mttr_hours / 48) * 100)) if mttr_hours > 0 else 100

        # ── Dimension 4: Open severity (fewer = better) ────────
        open_statuses = [
            ScanStatus.EXPLOIT_CONFIRMED.value,
            ScanStatus.PATCHING.value,
            ScanStatus.AWAITING_APPROVAL.value,
            ScanStatus.FAILED.value,
        ]
        open_critical = db.query(Scan).filter(
            Scan.repo_id == repo_id,
            Scan.status.in_(open_statuses),
            Scan.severity.in_(["CRITICAL", "ERROR"]),
        ).count()
        open_high = db.query(Scan).filter(
            Scan.repo_id == repo_id,
            Scan.status.in_(open_statuses),
            Scan.severity == "HIGH",
        ).count()
        open_vulns = open_critical + open_high

        # Each open CRITICAL = -20pts, each open HIGH = -10pts (floor 0)
        severity_score = max(0, 100 - (open_critical * 20) - (open_high * 10))

        # ── Dimension 5: Regression rate (lower = better) ──────
        regressions = sum(1 for s in all_scans if getattr(s, "is_regression", False))
        regression_rate = regressions / total
        regression_score = max(0, round((1 - regression_rate * 5) * 100))  # 1 regression per 20 scans = 0

        # ── Weighted composite score ───────────────────────────
        composite = (
            vuln_score      * 0.30 +
            fix_score       * 0.25 +
            mttr_score      * 0.20 +
            severity_score  * 0.15 +
            regression_score * 0.10
        )
        composite = round(composite)

        # ── Letter grade ───────────────────────────────────────
        if composite >= 90:
            grade = "A"
        elif composite >= 80:
            grade = "B"
        elif composite >= 70:
            grade = "C"
        elif composite >= 55:
            grade = "D"
        else:
            grade = "F"

        return {
            "repo_id": repo_id,
            "repo_name": repo.full_name,
            "grade": grade,
            "score": composite,
            "dimensions": {
                "vulnerability_rate": {"score": vuln_score, "label": "Vulnerability Rate", "weight": 0.30},
                "fix_rate":           {"score": fix_score,  "label": "Fix Rate",           "weight": 0.25},
                "mttr":               {"score": mttr_score, "label": "Time to Fix",        "weight": 0.20},
                "open_severity":      {"score": severity_score, "label": "Open Severity",  "weight": 0.15},
                "regression_rate":    {"score": regression_score, "label": "Regression Rate", "weight": 0.10},
            },
            "open_vulns": open_vulns,
            "mttr_hours": round(mttr_hours, 1),
            "fix_rate": round(fix_rate, 2),
            "total_scans": total,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scorecard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
