"""
Aegis — Dependency Vulnerability Scanner

Scans dependency files (requirements.txt, package.json, go.mod, Gemfile)
for known CVEs using the OSV.dev API (https://osv.dev).

OSV is free, no API key required, and covers PyPI, npm, Go, RubyGems,
Maven, and more.
"""

import json
import logging
import os
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

OSV_API = "https://api.osv.dev/v1/query"
OSV_TIMEOUT = 8  # seconds per package query


# ── Public entry point ────────────────────────────────────

def scan_dependencies(repo_path: str) -> list[dict]:
    """
    Scan all dependency files found in the repo for known CVEs.

    Returns a list of vulnerability dicts, each with:
        source    : which dependency file (e.g. "requirements.txt")
        package   : package name
        version   : installed version
        ecosystem : "PyPI" | "npm" | "Go" | "RubyGems"
        cves      : list of CVE IDs
        severity  : highest severity across all CVEs ("CRITICAL"|"HIGH"|"MEDIUM"|"LOW")
        summary   : short description of the worst CVE
    """
    all_vulns: list[dict] = []

    # Python
    req_file = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(req_file):
        all_vulns.extend(_scan_requirements_txt(req_file))

    # Node
    pkg_file = os.path.join(repo_path, "package.json")
    if os.path.exists(pkg_file):
        all_vulns.extend(_scan_package_json(pkg_file))

    # Go
    go_file = os.path.join(repo_path, "go.mod")
    if os.path.exists(go_file):
        all_vulns.extend(_scan_go_mod(go_file))

    # Ruby
    gemfile = os.path.join(repo_path, "Gemfile.lock")
    if os.path.exists(gemfile):
        all_vulns.extend(_scan_gemfile_lock(gemfile))

    if all_vulns:
        logger.warning(
            f"Dependency scan: {len(all_vulns)} vulnerable package(s) found"
        )
    else:
        logger.info("Dependency scan: no known vulnerabilities found")

    return all_vulns


# ── Per-ecosystem parsers ─────────────────────────────────

def _scan_requirements_txt(file_path: str) -> list[dict]:
    """Parse requirements.txt and query OSV for each pinned package."""
    results = []
    try:
        with open(file_path) as f:
            lines = f.readlines()
    except OSError:
        return []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        pkg, version = _parse_requirement_line(line)
        if not pkg or not version:
            continue

        vulns = _query_osv(pkg, version, "PyPI")
        if vulns:
            results.append(_build_result("requirements.txt", pkg, version, "PyPI", vulns))

    return results


def _scan_package_json(file_path: str) -> list[dict]:
    """Parse package.json dependencies and query OSV for each."""
    results = []
    try:
        with open(file_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    deps = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))

    for pkg, version_spec in deps.items():
        # Strip semver range operators: ^1.2.3 → 1.2.3
        version = re.sub(r"^[\^~>=<]", "", version_spec).strip()
        if not version or not re.match(r"^\d", version):
            continue

        vulns = _query_osv(pkg, version, "npm")
        if vulns:
            results.append(_build_result("package.json", pkg, version, "npm", vulns))

    return results


def _scan_go_mod(file_path: str) -> list[dict]:
    """Parse go.mod require directives and query OSV."""
    results = []
    try:
        with open(file_path) as f:
            content = f.read()
    except OSError:
        return []

    # Match: require github.com/foo/bar v1.2.3
    for m in re.finditer(r"^\s*(\S+)\s+v([\d.]+)", content, re.MULTILINE):
        pkg = m.group(1)
        version = m.group(2)

        vulns = _query_osv(pkg, version, "Go")
        if vulns:
            results.append(_build_result("go.mod", pkg, version, "Go", vulns))

    return results


def _scan_gemfile_lock(file_path: str) -> list[dict]:
    """Parse Gemfile.lock GEM specs and query OSV."""
    results = []
    try:
        with open(file_path) as f:
            content = f.read()
    except OSError:
        return []

    # Match lines like:    rack (2.2.3)
    for m in re.finditer(r"^\s{4}(\S+)\s+\(([\d.]+)\)", content, re.MULTILINE):
        pkg = m.group(1)
        version = m.group(2)

        vulns = _query_osv(pkg, version, "RubyGems")
        if vulns:
            results.append(_build_result("Gemfile.lock", pkg, version, "RubyGems", vulns))

    return results


# ── OSV API ───────────────────────────────────────────────

def _query_osv(package: str, version: str, ecosystem: str) -> list[dict]:
    """
    Query OSV.dev for known vulnerabilities in a specific package version.
    Returns a list of OSV vulnerability objects (may be empty).
    """
    try:
        resp = requests.post(
            OSV_API,
            json={
                "version": version,
                "package": {"name": package, "ecosystem": ecosystem},
            },
            timeout=OSV_TIMEOUT,
        )
        if resp.ok:
            return resp.json().get("vulns", [])
    except requests.RequestException as e:
        logger.debug(f"OSV query failed for {package}@{version}: {e}")
    return []


# ── Helpers ───────────────────────────────────────────────

def _parse_requirement_line(line: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse a requirements.txt line into (package, version).
    Handles: flask==2.0.1, flask>=2.0,<3, flask~=2.0.1
    Returns (None, None) for lines without a pinned version.
    """
    # Remove extras: package[extra]==1.0 → package==1.0
    line = re.sub(r"\[.*?\]", "", line)
    # Remove environment markers: package==1.0; python_version>="3.8"
    line = line.split(";")[0].strip()

    # Exact pin: package==1.2.3
    m = re.match(r"^([A-Za-z0-9_\-\.]+)==([\d.]+)", line)
    if m:
        return m.group(1), m.group(2)

    # Compatible release: package~=1.2.3
    m = re.match(r"^([A-Za-z0-9_\-\.]+)~=([\d.]+)", line)
    if m:
        return m.group(1), m.group(2)

    return None, None


def _build_result(
    source: str,
    package: str,
    version: str,
    ecosystem: str,
    osv_vulns: list[dict],
) -> dict:
    """Build a standardised vulnerability result dict from OSV data."""
    cves = []
    summaries = []
    severity = "LOW"
    severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    for vuln in osv_vulns:
        # Extract CVE IDs from aliases
        for alias in vuln.get("aliases", []):
            if alias.startswith("CVE-"):
                cves.append(alias)

        # Extract severity from database_specific or severity field
        for sev_entry in vuln.get("severity", []):
            score = sev_entry.get("score", "")
            # CVSS score → severity bucket
            detected = _cvss_score_to_severity(score)
            if severity_order.get(detected, 0) > severity_order.get(severity, 0):
                severity = detected

        summary = vuln.get("summary", "")
        if summary:
            summaries.append(summary)

    return {
        "source": source,
        "package": package,
        "version": version,
        "ecosystem": ecosystem,
        "cves": cves or [v.get("id", "UNKNOWN") for v in osv_vulns[:3]],
        "severity": severity,
        "summary": summaries[0] if summaries else f"Known vulnerability in {package} {version}",
        "vuln_count": len(osv_vulns),
    }


def _cvss_score_to_severity(score_str: str) -> str:
    """Convert a CVSS score string to a severity bucket."""
    try:
        score = float(score_str)
        if score >= 9.0:
            return "CRITICAL"
        elif score >= 7.0:
            return "HIGH"
        elif score >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"
    except (ValueError, TypeError):
        return "MEDIUM"
