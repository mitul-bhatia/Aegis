"""
Aegis Intelligent Scheduler - AI-Powered Security Operations

Advanced scheduling system that learns optimal scan timing,
prioritizes based on threat intelligence, and adapts to patterns.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import config
from database.db import SessionLocal
from database.models import Repo, Scan, ScanStatus
from orchestrator import run_aegis_pipeline
from intelligence.threat_engine import ThreatIntelligenceEngine
from ml.vulnerability_predictor import VulnerabilityPredictor

logger = logging.getLogger(__name__)


class ScanPriority(Enum):
    CRITICAL = 1  # Immediate scan
    HIGH = 2      # Within 1 hour
    MEDIUM = 3    # Within 6 hours
    LOW = 4       # Within 24 hours
    ROUTINE = 5   # Normal scheduling


@dataclass
class ScanContext:
    """Context for intelligent scan decisions"""
    repo: Repo
    last_scan: Optional[Scan]
    threat_level: ScanPriority
    activity_score: float
    vulnerability_density: float
    business_impact: float
    predicted_risk: float


class IntelligentScheduler:
    """AI-powered scheduler with threat intelligence integration"""
    
    def __init__(self):
        self.running = False
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_HOURS", "24"))
        self.background_task = None
        
        # Intelligence components
        self.threat_engine = ThreatIntelligenceEngine()
        self.vulnerability_predictor = VulnerabilityPredictor()
        
        # Learning data
        self.scan_history: List[Dict] = []
        self.repo_patterns: Dict[str, Dict] = {}
        
        logger.info("🧠 Intelligent Scheduler initialized with AI capabilities")
    
    async def start(self):
        """Start the intelligent scheduler"""
        if self.running:
            logger.warning("Intelligent Scheduler already running")
            return
        
        self.running = True
        logger.info(f"🧠 Aegis Intelligent Scheduler started - AI-powered scanning")
        
        # Start multiple concurrent tasks
        self.background_task = asyncio.create_task(self._run_intelligent_scheduler())
        asyncio.create_task(self._threat_monitoring_loop())
        asyncio.create_task(self._learning_loop())
    
    async def stop(self):
        """Stop the intelligent scheduler"""
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            logger.info("🛑 Intelligent Scheduler stopped")
    
    async def _run_intelligent_scheduler(self):
        """Main intelligent scheduling loop"""
        while self.running:
            try:
                # Get all repos with intelligent prioritization
                repos_with_context = await self._analyze_repositories()
                
                # Sort by priority and schedule scans
                prioritized_repos = sorted(repos_with_context, key=lambda x: x.threat_level.value)
                
                logger.info(f"🧠 Processing {len(prioritized_repos)} repositories with AI prioritization")
                
                for repo_context in prioritized_repos:
                    if not self.running:
                        break
                    
                    # Check if scan is needed based on intelligent criteria
                    if await self._should_scan_repository(repo_context):
                        await self._execute_intelligent_scan(repo_context)
                
                # Adaptive sleep based on current threat level
                sleep_duration = await self._calculate_adaptive_sleep()
                await asyncio.sleep(sleep_duration)
                
            except asyncio.CancelledError:
                logger.info("Intelligent scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in intelligent scheduler: {e}")
                await asyncio.sleep(300)  # 5 minutes on error
    
    async def _analyze_repositories(self) -> List[ScanContext]:
        """Analyze all repositories and create scan contexts"""
        db = SessionLocal()
        try:
            repos = db.query(Repo).filter(Repo.is_indexed == True).all()
            contexts = []
            
            for repo in repos:
                context = await self._create_scan_context(repo, db)
                contexts.append(context)
            
            return contexts
        finally:
            db.close()
    
    async def _create_scan_context(self, repo: Repo, db) -> ScanContext:
        """Create intelligent scan context for a repository"""
        # Get last scan
        last_scan = db.query(Scan).filter(
            Scan.repo_id == repo.id
        ).order_by(Scan.created_at.desc()).first()
        
        # Calculate activity score based on recent commits
        activity_score = await self._calculate_activity_score(repo, db)
        
        # Get threat intelligence
        threat_level = await self._assess_threat_level(repo, last_scan)
        
        # Calculate vulnerability density
        vulnerability_density = await self._calculate_vulnerability_density(repo, db)
        
        # Assess business impact (could be configured per repo)
        business_impact = await self._assess_business_impact(repo)
        
        # Predict current risk
        predicted_risk = await self.vulnerability_predictor.predict_repo_risk(repo)
        
        return ScanContext(
            repo=repo,
            last_scan=last_scan,
            threat_level=threat_level,
            activity_score=activity_score,
            vulnerability_density=vulnerability_density,
            business_impact=business_impact,
            predicted_risk=predicted_risk
        )
    
    async def _calculate_activity_score(self, repo: Repo, db) -> float:
        """Calculate repository activity score (0.0-1.0)"""
        # Count recent scans as proxy for activity
        recent_scans = db.query(Scan).filter(
            Scan.repo_id == repo.id,
            Scan.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
        ).count()
        
        # Normalize to 0-1 scale (more scans = higher activity)
        activity_score = min(recent_scans / 10.0, 1.0)
        return activity_score
    
    async def _assess_threat_level(self, repo: Repo, last_scan: Optional[Scan]) -> ScanPriority:
        """Assess threat level based on multiple factors"""
        # Get threat intelligence for this repo
        threat_intel = await self.threat_engine.get_repo_threats(repo.full_name)
        
        # Base priority on threat intelligence
        if threat_intel.critical_threats > 0:
            return ScanPriority.CRITICAL
        elif threat_intel.high_threats > 0:
            return ScanPriority.HIGH
        elif threat_intel.medium_threats > 0:
            return ScanPriority.MEDIUM
        
        # Consider time since last scan
        if last_scan:
            time_since_scan = datetime.now(timezone.utc) - last_scan.created_at
            if time_since_scan > timedelta(hours=48):
                return ScanPriority.LOW
        
        return ScanPriority.ROUTINE
    
    async def _calculate_vulnerability_density(self, repo: Repo, db) -> float:
        """Calculate vulnerability density (vulns per 1000 lines)"""
        recent_scans = db.query(Scan).filter(
            Scan.repo_id == repo.id,
            Scan.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).all()
        
        if not recent_scans:
            return 0.0
        
        vuln_count = sum(1 for scan in recent_scans if scan.status in [ScanStatus.FIXED.value])
        # Estimate lines of code (this could be made more accurate)
        estimated_loc = 10000  # Default estimate
        
        density = (vuln_count / len(recent_scans)) / (estimated_loc / 1000)
        return min(density, 1.0)
    
    async def _assess_business_impact(self, repo: Repo) -> float:
        """Assess business impact (0.0-1.0)"""
        # This could be enhanced with actual business logic
        # For now, use repo name patterns as a simple heuristic
        name_lower = repo.full_name.lower()
        
        if any(keyword in name_lower for keyword in ['prod', 'main', 'core', 'api']):
            return 0.9
        elif any(keyword in name_lower for keyword in ['test', 'demo', 'staging']):
            return 0.3
        else:
            return 0.6
    
    async def _should_scan_repository(self, context: ScanContext) -> bool:
        """Intelligent decision on whether to scan now"""
        # Always scan critical priority
        if context.threat_level == ScanPriority.CRITICAL:
            return True
        
        # Check if enough time has passed based on priority
        if not context.last_scan:
            return True
        
        time_since_scan = datetime.now(timezone.utc) - context.last_scan.created_at
        
        # Adaptive timing based on priority and activity
        if context.threat_level == ScanPriority.HIGH:
            max_interval = timedelta(hours=1)
        elif context.threat_level == ScanPriority.MEDIUM:
            max_interval = timedelta(hours=6)
        elif context.threat_level == ScanPriority.LOW:
            max_interval = timedelta(hours=24)
        else:  # ROUTINE
            max_interval = timedelta(hours=self.scan_interval)
        
        # Adjust interval based on activity and predicted risk
        activity_multiplier = 1.0 + (context.activity_score * 0.5)
        risk_multiplier = 1.0 + (context.predicted_risk * 0.3)
        
        adjusted_interval = max_interval / (activity_multiplier * risk_multiplier)
        
        return time_since_scan > adjusted_interval
    
    async def _execute_intelligent_scan(self, context: ScanContext):
        """Execute scan with enhanced context"""
        logger.info(f"🧠 Starting intelligent scan: {context.repo.full_name} "
                   f"(Priority: {context.threat_level.name}, Risk: {context.predicted_risk:.2f})")
        
        # Create enhanced scan info
        scan_info = {
            "repo_name": context.repo.full_name,
            "repo_url": f"https://github.com/{context.repo.full_name}",
            "commit_sha": "latest",
            "branch": "main",
            "files_changed": [],
            "is_autonomous": True,
            "intelligence_context": {
                "threat_level": context.threat_level.value,
                "predicted_risk": context.predicted_risk,
                "activity_score": context.activity_score,
                "vulnerability_density": context.vulnerability_density,
                "business_impact": context.business_impact
            }
        }
        
        try:
            await run_aegis_pipeline(scan_info)
            
            # Learn from this scan
            await self._learn_from_scan(context, scan_info)
            
        except Exception as e:
            logger.error(f"Intelligent scan failed for {context.repo.full_name}: {e}")
    
    async def _threat_monitoring_loop(self):
        """Background loop for threat intelligence monitoring"""
        while self.running:
            try:
                # Update threat intelligence
                await self.threat_engine.update_threat_feeds()
                
                # Check for emergency threats that require immediate scanning
                emergency_repos = await self.threat_engine.get_emergency_repos()
                
                if emergency_repos:
                    logger.warning(f"🚨 Emergency threats detected: {len(emergency_repos)} repos")
                    for repo_name in emergency_repos:
                        # Trigger immediate scan for emergency repos
                        await self._trigger_emergency_scan(repo_name)
                
                # Sleep for threat monitoring interval
                await asyncio.sleep(300)  # 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in threat monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _learning_loop(self):
        """Background loop for continuous learning"""
        while self.running:
            try:
                # Update ML models with latest data
                await self.vulnerability_predictor.update_models()
                
                # Analyze patterns and improve scheduling
                await self._analyze_scheduling_patterns()
                
                # Sleep for learning interval
                await asyncio.sleep(3600)  # 1 hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(300)
    
    async def _calculate_adaptive_sleep(self) -> int:
        """Calculate adaptive sleep duration based on current threat landscape"""
        # Get current global threat level
        global_threat_level = await self.threat_engine.get_global_threat_level()
        
        # Adjust scan frequency based on threat level
        if global_threat_level == "CRITICAL":
            return 300  # 5 minutes
        elif global_threat_level == "HIGH":
            return 900  # 15 minutes
        elif global_threat_level == "MEDIUM":
            return 1800  # 30 minutes
        else:
            return self.scan_interval * 3600  # Normal interval
    
    async def _trigger_emergency_scan(self, repo_name: str):
        """Trigger emergency scan for high-priority repository"""
        db = SessionLocal()
        try:
            repo = db.query(Repo).filter(Repo.full_name == repo_name).first()
            if repo:
                context = await self._create_scan_context(repo, db)
                context.threat_level = ScanPriority.CRITICAL
                await self._execute_intelligent_scan(context)
        finally:
            db.close()
    
    async def _learn_from_scan(self, context: ScanContext, scan_info: Dict):
        """Learn from scan results to improve future decisions"""
        # Store scan pattern data
        pattern_data = {
            "timestamp": datetime.now(timezone.utc),
            "repo": context.repo.full_name,
            "threat_level": context.threat_level.value,
            "predicted_risk": context.predicted_risk,
            "actual_outcome": scan_info.get("outcome", "unknown"),
            "duration": scan_info.get("duration", 0)
        }
        
        self.scan_history.append(pattern_data)
        
        # Update repo-specific patterns
        if context.repo.full_name not in self.repo_patterns:
            self.repo_patterns[context.repo.full_name] = {
                "scan_count": 0,
                "avg_duration": 0,
                "vulnerability_rate": 0
            }
        
        pattern = self.repo_patterns[context.repo.full_name]
        pattern["scan_count"] += 1
        
        # Update averages
        if pattern["avg_duration"] == 0:
            pattern["avg_duration"] = scan_info.get("duration", 0)
        else:
            pattern["avg_duration"] = (
                pattern["avg_duration"] * 0.8 + scan_info.get("duration", 0) * 0.2
            )
    
    async def _analyze_scheduling_patterns(self):
        """Analyze scheduling patterns to optimize future decisions"""
        if len(self.scan_history) < 10:
            return
        
        # Analyze effectiveness of different scheduling decisions
        recent_scans = self.scan_history[-100:]  # Last 100 scans
        
        # Calculate success rates by threat level
        threat_level_stats = {}
        for scan in recent_scans:
            level = scan["threat_level"]
            if level not in threat_level_stats:
                threat_level_stats[level] = {"total": 0, "successful": 0}
            
            threat_level_stats[level]["total"] += 1
            if scan["actual_outcome"] == "success":
                threat_level_stats[level]["successful"] += 1
        
        # Log insights
        for level, stats in threat_level_stats.items():
            success_rate = stats["successful"] / stats["total"]
            logger.info(f"🧠 Threat level {level} success rate: {success_rate:.2%}")
    
    async def get_scheduling_insights(self) -> Dict:
        """Get insights about scheduling performance"""
        return {
            "total_scans": len(self.scan_history),
            "repo_patterns": len(self.repo_patterns),
            "avg_scan_duration": sum(s.get("duration", 0) for s in self.scan_history) / max(len(self.scan_history), 1),
            "threat_distribution": self._get_threat_distribution()
        }
    
    def _get_threat_distribution(self) -> Dict[str, int]:
        """Get distribution of threat levels in recent scans"""
        distribution = {level.name: 0 for level in ScanPriority}
        for scan in self.scan_history[-50:]:  # Last 50 scans
            # Convert integer threat_level back to name
            for level in ScanPriority:
                if level.value == scan["threat_level"]:
                    distribution[level.name] += 1
                    break
        return distribution


# Global intelligent scheduler instance
intelligent_scheduler = IntelligentScheduler()


async def start_intelligent_scheduler():
    """Start the intelligent scheduler (call from main.py)"""
    await intelligent_scheduler.start()


async def stop_intelligent_scheduler():
    """Stop the intelligent scheduler (call from main.py)"""
    await intelligent_scheduler.stop()
