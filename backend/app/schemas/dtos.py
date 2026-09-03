from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ── Auth Schemas ─────────────────────────────────────────

class OAuthRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


class InstallationLinkRequest(BaseModel):
    user_id: int
    installation_id: int


class UserInfo(BaseModel):
    id: int
    github_id: int
    github_username: str
    github_avatar_url: Optional[str] = None
    github_installation_id: Optional[int] = None

    class Config:
        from_attributes = True


# ── Repo Schemas ─────────────────────────────────────────

class RepoCreateRequest(BaseModel):
    user_id: int
    repo_url: str = Field(..., max_length=512)


class RepoInfo(BaseModel):
    id: int
    full_name: str
    webhook_id: Optional[int] = None
    is_indexed: bool = False
    status: str = "active"
    created_at: str
    html_url: Optional[str] = None

    class Config:
        from_attributes = True


class AvailableRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    description: Optional[str] = None
    default_branch: str = "main"


# ── Scan Schemas ─────────────────────────────────────────

class FindingInfo(BaseModel):
    file: str
    line_start: int
    vuln_type: str
    severity: str # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    relevant_code: str
    confidence: str = "HIGH"


class ScanInfo(BaseModel):
    id: int
    repo_id: int
    commit_sha: str
    branch: str
    status: str
    vulnerability_type: Optional[str] = None
    severity: Optional[str] = None
    pr_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    vulnerable_file: Optional[str] = None
    exploit_output: Optional[str] = None
    patch_diff: Optional[str] = None
    error_message: Optional[str] = None
    original_code: Optional[str] = None
    exploit_script: Optional[str] = None
    findings_json: Optional[str] = None
    current_agent: Optional[str] = None
    agent_message: Optional[str] = None
    patch_attempts: int = 0
    is_regression: bool = False

    class Config:
        from_attributes = True


class TriggerResult(BaseModel):
    message: str
    repo: str
    commit: str
    files: List[str] = []


class ScanApproveRequest(BaseModel):
    user_context: Optional[str] = None


# ── Stats & Intelligence Schemas ─────────────────────────

class StatsInfo(BaseModel):
    total_repos: int = 0
    active_scans: int = 0
    vulns_fixed: int = 0
    total_scans: int = 0
    false_positives: int = 0
    last_scan_at: Optional[str] = None


class RepoIntelligence(BaseModel):
    repo_id: int
    repo_name: str
    threat_level: str = "LOW"
    critical_threats: int = 0
    high_threats: int = 0
    medium_threats: int = 0
    predicted_risk: float = 0.0
    vulnerability_density: float = 0.0
    activity_score: float = 0.0
    business_impact: float = 0.0
    adaptive_interval_hours: int = 24
    last_scan: Optional[str] = None
    next_scan_in_minutes: Optional[int] = None


class GlobalThreat(BaseModel):
    level: str = "LOW"
    emergency_repos: List[str] = []
    total_threats: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class AnalyticsData(BaseModel):
    vuln_trend: List[Dict[str, Any]] = []
    top_vulns: List[Dict[str, Any]] = []
    severity_dist: Dict[str, int] = {}
    mttr_hours: float = 0.0
    fix_rate: float = 100.0
    total_scans: int = 0
    total_vulns_found: int = 0
    total_fixed: int = 0
    regressions: int = 0
    period_days: int = 30


class ScorecardDimension(BaseModel):
    score: float
    label: str
    weight: float


class ScorecardData(BaseModel):
    repo_id: int
    repo_name: str
    grade: str = "A"
    score: Optional[float] = 95.0
    dimensions: Dict[str, ScorecardDimension] = {}
    open_vulns: int = 0
    mttr_hours: float = 0.0
    fix_rate: float = 100.0
    total_scans: int = 0
    message: Optional[str] = None
