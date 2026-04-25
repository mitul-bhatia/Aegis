"""
Aegis — Agent I/O Schemas

Single source of truth for all Pydantic models used across agents.
Import from here instead of defining models in individual agent files.

Why centralize?
- Prevents duplicate definitions drifting out of sync
- Makes it easy to see all agent contracts in one place
- Shared models (e.g. VulnerabilityFinding) used by multiple agents
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Agent 1: Finder ───────────────────────────────────────

class VulnerabilityFinding(BaseModel):
    """One vulnerability found by the Finder agent."""
    file: str = Field(description="Affected file path")
    line_start: int = Field(description="Starting line number")
    vuln_type: str = Field(description="e.g. SQL Injection, XSS, Path Traversal")
    severity: str = Field(description="CRITICAL, HIGH, MEDIUM, or LOW")
    description: str = Field(description="1-2 sentence explanation")
    relevant_code: str = Field(description="The vulnerable code snippet")
    confidence: str = Field(description="HIGH, MEDIUM, or LOW")
    # CVSS fields — populated after Finder returns, before pipeline continues
    cvss_vector: Optional[str] = Field(default=None, description="CVSS 3.1 vector string")
    cvss_score: Optional[float] = Field(default=None, description="Calculated CVSS base score 0.0-10.0")


# ── Agent 2: Exploiter ────────────────────────────────────

class ExploitResult(BaseModel):
    """Output from the Exploiter agent."""
    exploit_script: str = Field(description="Runnable Python exploit script")
    vulnerability_type: str = Field(description="Human-readable vuln name")
    reasoning: str = Field(description="Which model generated this")
    files_analyzed: List[str] = Field(
        default_factory=list,
        description="Filenames from the diff that were analyzed",
    )


# ── Agent 3: Engineer ─────────────────────────────────────

class EngineerOutput(BaseModel):
    """Output from the Engineer agent."""
    patched_code: str = Field(description="Complete fixed file content")
    test_code: str = Field(
        default="",
        description="Complete pytest test file (may be empty)",
    )


# ── Agent 4: Reviewer ─────────────────────────────────────

class ReviewerDiagnosis(BaseModel):
    """Structured diagnosis from the Reviewer agent when a patch fails."""
    root_cause: str = Field(
        description="One sentence: why the patch failed"
    )
    what_to_fix: str = Field(
        description="Specific instruction for the Engineer"
    )
    suggested_approach: str = Field(
        description="Best technical approach to fix this correctly"
    )
    confidence: str = Field(description="HIGH, MEDIUM, or LOW")
    test_issues: List[str] = Field(
        default_factory=list,
        description="Individual test failures explained in plain English",
    )
    exploit_still_works: bool = Field(
        default=False,
        description="True if the failure was because the exploit still succeeded",
    )
