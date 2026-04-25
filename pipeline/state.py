"""
Aegis Pipeline State

This is the single shared data structure that flows through every node
in the LangGraph pipeline. Each node reads from it and returns a partial
update — LangGraph merges the updates automatically.

Think of it like a baton in a relay race: each agent picks it up,
adds their results, and passes it to the next.

TypedDict is used (not a dataclass) because LangGraph requires it.
All fields are Optional so nodes only need to return what they changed.
"""

from typing import TypedDict, Optional, List


class AegisPipelineState(TypedDict):
    """Full state of one Aegis pipeline run."""

    # ── Input (set once at pipeline start) ───────────────
    repo_full_name: str          # e.g. "user/my-app"
    commit_sha: str              # the commit that triggered the scan
    branch: str                  # e.g. "main"
    push_info: dict              # raw push_info dict from the webhook
    scan_id: Optional[int]       # DB scan record ID (None if repo not in DB)

    # ── Pre-processing results ────────────────────────────
    local_repo_path: str         # absolute path to cloned repo on disk
    diff: dict                   # git diff with changed_files list
    semgrep_findings: List[dict] # raw Semgrep output (may be empty)
    rag_context: str             # related code from ChromaDB
    dependency_vulns: List[dict] # vulnerable packages found by dependency scanner

    # ── Finder output ─────────────────────────────────────
    vulnerability_findings: List[dict]  # serialized VulnerabilityFinding dicts

    # ── Exploiter output ──────────────────────────────────
    confirmed_vulnerabilities: List[dict]  # vulns confirmed by sandbox exploit

    # ── Per-vulnerability fix tracking ───────────────────
    # Index into confirmed_vulnerabilities — which one we're fixing right now
    current_vuln_index: int

    # ── Engineer / Verifier output ────────────────────────
    patched_code: Optional[str]   # the patch for the current vulnerability
    test_code: Optional[str]      # the test file for the current vulnerability
    original_code: Optional[str]  # the original vulnerable code (for diff view)

    # ── Verifier result ───────────────────────────────────
    verification_passed: bool     # True if tests pass AND exploit is blocked
    retry_count: int              # how many Engineer retries so far
    max_retries: int              # max allowed retries (from config)

    # ── PR tracking ───────────────────────────────────────
    pr_urls: List[str]            # PRs opened so far (one per fixed vuln)

    # ── Shared Artifact Store ─────────────────────────────
    exploit_artifacts: List[dict] # PoC scripts + sandbox outputs per finding
    patch_artifacts: List[dict]   # patch diffs + test results per vuln
    safety_report: Optional[dict] # output of the Safety Validator node

    # ── Post-patch re-scan control ────────────────────────
    rescan_needed: bool           # True if Safety Validator wants a re-scan
    rescan_count: int             # number of post-patch re-scans done (cap at 1)

    # ── Control flow ──────────────────────────────────────
    pipeline_status: str          # current high-level status string
    error: Optional[str]          # error message if something went wrong
    awaiting_approval: bool       # True when CRITICAL vuln is paused for human review
