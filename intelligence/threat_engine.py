"""
Aegis Threat Intelligence Engine

Monitors and assesses security threats across repositories.
Provides real-time threat levels and emergency detection.
"""

import logging
from typing import List
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from sqlalchemy import func

from database.db import SessionLocal
from database.models import Repo, Scan, ScanStatus

logger = logging.getLogger(__name__)


@dataclass
class ThreatIntelligence:
    """Threat intelligence data for a repository"""
    level: str  # CRITICAL, HIGH, MEDIUM, LOW
    critical_threats: int
    high_threats: int
    medium_threats: int


class ThreatIntelligenceEngine:
    """
    Threat intelligence engine for security monitoring.
    
    Analyzes scan history to determine threat levels based on:
    - Unresolved vulnerabilities by severity
    - Recent exploit confirmations
    - Failed remediation attempts
    """
    
    def __init__(self):
        self.threat_feeds = []
        logger.info("Threat Intelligence Engine initialized")
    
    async def get_repo_threats(self, repo_name: str) -> ThreatIntelligence:
        """
        Get threat intelligence for a specific repository.
        
        Analyzes the last 30 days of scan data to determine:
        - Current threat level (CRITICAL/HIGH/MEDIUM/LOW)
        - Count of unresolved vulnerabilities by severity
        
        Args:
            repo_name: Full repository name (e.g., "user/repo")
            
        Returns:
            ThreatIntelligence object with threat counts and level
        """
        db = SessionLocal()
        try:
            repo = db.query(Repo).filter(Repo.full_name == repo_name).first()
            if not repo:
                return ThreatIntelligence(
                    level="LOW",
                    critical_threats=0,
                    high_threats=0,
                    medium_threats=0
                )
            
            # Count unresolved vulnerabilities by severity (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Unresolved = exploit confirmed, patching, awaiting approval, or failed
            unresolved_statuses = [
                ScanStatus.EXPLOIT_CONFIRMED.value,
                ScanStatus.PATCHING.value,
                ScanStatus.AWAITING_APPROVAL.value,
                ScanStatus.FAILED.value,
            ]
            
            counts = db.query(
                Scan.severity,
                func.count(Scan.id)
            ).filter(
                Scan.repo_id == repo.id,
                Scan.created_at >= thirty_days_ago,
                Scan.severity.isnot(None),
                Scan.status.in_(unresolved_statuses)
            ).group_by(Scan.severity).all()
            
            severity_map = dict(counts)
            critical = severity_map.get("CRITICAL", 0) + severity_map.get("ERROR", 0)
            high = severity_map.get("HIGH", 0)
            medium = severity_map.get("MEDIUM", 0) + severity_map.get("WARNING", 0)
            
            # Calculate threat level based on unresolved vulnerabilities
            if critical > 0:
                level = "CRITICAL"
            elif high >= 3:
                level = "HIGH"
            elif high > 0 or medium >= 5:
                level = "MEDIUM"
            else:
                level = "LOW"
            
            logger.debug(
                f"Threat assessment for {repo_name}: {level} "
                f"(C:{critical}, H:{high}, M:{medium})"
            )
            
            return ThreatIntelligence(
                level=level,
                critical_threats=critical,
                high_threats=high,
                medium_threats=medium
            )
        finally:
            db.close()
    
    async def get_global_threat_level(self) -> str:
        """
        Get global threat level across all repositories.
        
        Returns the highest threat level found across all repos.
        
        Returns:
            Threat level: CRITICAL, HIGH, MEDIUM, or LOW
        """
        db = SessionLocal()
        try:
            repos = db.query(Repo).all()
            
            if not repos:
                return "LOW"
            
            # Check each repo and return the worst-case threat level
            max_level = "LOW"
            level_priority = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            
            for repo in repos:
                threat = await self.get_repo_threats(repo.full_name)
                if level_priority.get(threat.level, 0) > level_priority.get(max_level, 0):
                    max_level = threat.level
                
                # Early exit if we hit CRITICAL
                if max_level == "CRITICAL":
                    break
            
            logger.debug(f"Global threat level: {max_level}")
            return max_level
        finally:
            db.close()
    
    async def get_emergency_repos(self) -> List[str]:
        """
        Get list of repositories with emergency-level threats.
        
        Emergency = CRITICAL unresolved vulnerabilities or multiple HIGH severity issues.
        
        Returns:
            List of repository names requiring immediate attention
        """
        db = SessionLocal()
        try:
            repos = db.query(Repo).all()
            emergency_repos = []
            
            for repo in repos:
                threat = await self.get_repo_threats(repo.full_name)
                
                # Emergency criteria:
                # - Any CRITICAL unresolved vulnerabilities
                # - 5+ HIGH severity unresolved vulnerabilities
                if threat.critical_threats > 0 or threat.high_threats >= 5:
                    emergency_repos.append(repo.full_name)
            
            if emergency_repos:
                logger.warning(
                    f"Emergency repos detected: {', '.join(emergency_repos)}"
                )
            
            return emergency_repos
        finally:
            db.close()
    
    async def update_threat_feeds(self):
        """
        Update threat intelligence feeds.
        
        Currently a no-op. In production, this would:
        - Fetch latest CVE data
        - Update security advisories
        - Sync with threat intelligence platforms
        """
        logger.debug("Threat feed update (no external feeds configured)")
        pass

