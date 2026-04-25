"""
Aegis — Database Models

Four tables:
- users: GitHub OAuth users
- repos: Monitored repositories (one webhook per repo)
- scans: Every scan run (linked to repo, tracks full lifecycle)
- vuln_signatures: Records of fixed vulnerabilities for regression detection
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from database.db import Base


# ── Scan Status Enum ──────────────────────────────────────
class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    SCANNING = "scanning"          # Semgrep running
    EXPLOITING = "exploiting"      # Agent A writing exploit + sandbox testing
    EXPLOIT_CONFIRMED = "exploit_confirmed"  # Exploit succeeded
    PATCHING = "patching"          # Agent B writing fix
    VERIFYING = "verifying"        # Agent C testing the fix
    AWAITING_APPROVAL = "awaiting_approval"  # CRITICAL vuln — waiting for human approval
    FIXED = "fixed"                # Fix verified, PR opened
    FALSE_POSITIVE = "false_positive"  # Semgrep flagged but exploit failed
    CLEAN = "clean"                # No vulnerabilities found
    FAILED = "failed"              # Pipeline error
    REGRESSION = "regression"      # Previously fixed vuln reappeared


# ── User ──────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    github_username = Column(String(255), nullable=False)
    github_avatar_url = Column(String(500), default="")
    github_token = Column(String(255), nullable=False)  # Encrypted in production
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    repos = relationship("Repo", back_populates="user", cascade="all, delete-orphan")


# ── Repo ──────────────────────────────────────────────────
class Repo(Base):
    __tablename__ = "repos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)  # e.g. "mitulbhatia/my-app"
    webhook_id = Column(Integer, nullable=True)       # GitHub webhook ID (for uninstall)
    is_indexed = Column(Boolean, default=False)        # RAG index complete?
    status = Column(String(50), default="setting_up")  # setting_up / monitoring / error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="repos")
    scans = relationship("Scan", back_populates="repo", cascade="all, delete-orphan")
    vuln_signatures = relationship("VulnSignature", back_populates="repo", cascade="all, delete-orphan")


# ── Scan ──────────────────────────────────────────────────
class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=False, index=True)
    commit_sha = Column(String(40), nullable=False)
    branch = Column(String(255), default="main")
    status = Column(String(50), default=ScanStatus.QUEUED.value)

    # Results (populated as the pipeline progresses)
    vulnerability_type = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True)       # WARNING, ERROR, etc.
    vulnerable_file = Column(String(500), nullable=True)
    exploit_output = Column(Text, nullable=True)       # Full exploit stdout
    patch_diff = Column(Text, nullable=True)            # The patched code
    pr_url = Column(String(500), nullable=True)         # GitHub PR link
    error_message = Column(Text, nullable=True)         # If pipeline failed

    # Agent identity (for real-time UI — which agent is working + what it's doing)
    original_code = Column(Text, nullable=True)         # Vulnerable code BEFORE patch (for diff view)
    exploit_script = Column(Text, nullable=True)        # The exploit code Agent 2 generated
    findings_json = Column(Text, nullable=True)         # JSON: all findings from Agent 1
    current_agent = Column(String(50), nullable=True)   # 'finder' | 'exploiter' | 'engineer' | 'safety_validator' | 'approval_gate'
    agent_message = Column(String(500), nullable=True)  # Current agent's latest status message
    patch_attempts = Column(Integer, default=0)         # How many Engineer retries

    # Regression tracking
    is_regression = Column(Boolean, default=False)      # True if this is a regression of a previously fixed vuln
    original_fix_scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)  # The scan that originally fixed it

    # Timing
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    repo = relationship("Repo", back_populates="scans")
    original_fix = relationship("Scan", remote_side="Scan.id", foreign_keys=[original_fix_scan_id])


# ── VulnSignature ─────────────────────────────────────────
class VulnSignature(Base):
    """
    Records a vulnerability that was successfully fixed by Aegis.
    Used for regression detection — if the same vuln type reappears
    in the same file, it's flagged as a regression.
    """
    __tablename__ = "vuln_signatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)     # Which file was fixed
    vuln_type = Column(String(100), nullable=False)     # e.g. "SQL Injection"
    severity = Column(String(20), nullable=True)        # CRITICAL, HIGH, etc.
    fix_commit = Column(String(40), nullable=True)      # Commit SHA of the fix
    fix_scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)  # The scan that fixed it
    fixed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    repo = relationship("Repo", back_populates="vuln_signatures")
    fix_scan = relationship("Scan", foreign_keys=[fix_scan_id])
