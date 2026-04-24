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
router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

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
                
                predictions.append(MLPredictionResponse(
                    repo_id=repo.id,
                    repo_name=repo.full_name,
                    risk_score=risk_score,
                    confidence=0.85,  # Placeholder - could be calculated from model
                    factors=factors
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
        
        # Get priority distribution from scheduler
        priority_distribution = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "ROUTINE": 0
        }
        
        # This would be populated from actual scheduler state
        # For now, using placeholder logic
        
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

