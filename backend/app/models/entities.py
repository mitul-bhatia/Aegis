from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True, nullable=False)
    github_username = Column(String(255), nullable=False)
    github_avatar_url = Column(String(512), nullable=True)
    github_installation_id = Column(Integer, nullable=True, index=True)
    access_token = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    full_name = Column(String(255), unique=True, index=True, nullable=False)
    installation_id = Column(Integer, nullable=True, index=True)
    is_indexed = Column(Boolean, default=False)
    status = Column(String(50), default="active")
    webhook_id = Column(Integer, nullable=True)
    html_url = Column(String(512), nullable=True)
    default_branch = Column(String(100), default="main")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    commit_sha = Column(String(64), default="HEAD")
    branch = Column(String(100), default="main")
    
    # Statuses: queued, scanning, exploiting, exploit_confirmed, patching, verifying, awaiting_approval, fixed, false_positive, clean, failed, regression
    status = Column(String(50), default="queued", index=True)
    
    vulnerability_type = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True) # CRITICAL, HIGH, MEDIUM, LOW
    pr_url = Column(String(512), nullable=True)
    
    vulnerable_file = Column(String(512), nullable=True)
    exploit_output = Column(Text, nullable=True)
    patch_diff = Column(Text, nullable=True)
    original_code = Column(Text, nullable=True)
    exploit_script = Column(Text, nullable=True)
    findings_json = Column(Text, nullable=True)
    
    current_agent = Column(String(50), nullable=True)
    agent_message = Column(Text, nullable=True)
    patch_attempts = Column(Integer, default=0)
    is_regression = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    repository = relationship("Repository", back_populates="scans")
    issues = relationship("Issue", back_populates="scan", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    vulnerability_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    file_path = Column(String(512), nullable=False)
    line_start = Column(Integer, default=1)
    line_end = Column(Integer, default=1)
    description = Column(Text, nullable=False)
    code_snippet = Column(Text, nullable=True)
    
    # Status: open, verifying, fixed, dismissed
    status = Column(String(50), default="open", index=True)
    reproduction_cmd = Column(Text, nullable=True)
    user_context = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scan = relationship("Scan", back_populates="issues")
    repository = relationship("Repository", back_populates="issues")
