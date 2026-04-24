# Aegis — Complete Implementation Plan (Backend + Frontend)

> **Goal**: Transform Aegis from a functional system into a hackathon-winning product. The backend needs richer data for the frontend to tell the agent story. The frontend needs a cinematic, real-time UI that makes judges feel like they're watching a security operation unfold.

---

## Part A: Backend Changes Required

The current backend works, but the SSE events are too simple (just status string), the DB doesn't store enough data for the UI (no original code, no agent logs, no scan duration), and there's no stats endpoint. These changes are **required before** the frontend can be premium.

---

### A1. Database Schema Enhancements

#### [MODIFY] [models.py](file:///Users/jivitrana/Desktop/Aegis/database/models.py)

**Add to the `Scan` model:**

```python
# New fields on Scan table
original_code = Column(Text, nullable=True)        # Vulnerable code BEFORE patch (for diff view)
exploit_script = Column(Text, nullable=True)        # The exploit code Agent 2 generated
findings_json = Column(Text, nullable=True)         # JSON: all findings from Agent 1
current_agent = Column(String(50), nullable=True)   # 'finder' | 'exploiter' | 'engineer' | 'verifier'
agent_message = Column(String(500), nullable=True)  # Current agent's latest status message
patch_attempts = Column(Integer, default=0)         # How many Engineer retries
```

**Why**: The frontend scan detail page needs `original_code` to show before/after diff. It needs `current_agent` + `agent_message` to show which agent is working and what it's doing. `exploit_script` is needed to display the generated exploit code. `findings_json` lets us show all findings from the Finder agent.

**Migration**: Since this is SQLite for a hackathon, just delete `aegis.db` and restart — tables auto-recreate via `init_db()`.

---

### A2. Richer SSE Events from Orchestrator

#### [MODIFY] [orchestrator.py](file:///Users/jivitrana/Desktop/Aegis/orchestrator.py)

The orchestrator currently only sets `scan.status`. It must also set `current_agent` and `agent_message` at each pipeline step for the frontend to show which agent is active.

**Changes at each pipeline phase:**

```python
# Phase 2 (Scanning):
update_scan_status(scan.id, ScanStatus.SCANNING.value, {
    "current_agent": "finder",
    "agent_message": f"Semgrep scanning {len(file_paths)} file(s)..."
})

# Phase 4 (Finder complete):
update_scan_status(scan.id, ScanStatus.SCANNING.value, {
    "current_agent": "finder",
    "agent_message": f"Found {len(findings)} potential vulnerabilities",
    "vulnerability_type": critical_finding.vuln_type,
    "severity": critical_finding.severity,
    "vulnerable_file": critical_finding.file,
    "findings_json": json.dumps([f.dict() for f in findings])
})

# Phase 5 (Exploiting):
update_scan_status(scan.id, ScanStatus.EXPLOITING.value, {
    "current_agent": "exploiter",
    "agent_message": f"Testing {finding.vuln_type} in Docker sandbox..."
})

# Phase 5 (Exploit confirmed):
update_scan_status(scan.id, ScanStatus.EXPLOIT_CONFIRMED.value, {
    "current_agent": "exploiter",
    "agent_message": f"CONFIRMED: {vulnerability_type} is exploitable",
    "exploit_output": exploit_test["stdout"],
    "exploit_script": exploit_script
})

# Phase 6 (Patching):
update_scan_status(scan.id, ScanStatus.PATCHING.value, {
    "current_agent": "engineer",
    "agent_message": f"Writing security patch for {vulnerable_file}...",
    "original_code": original_code
})

# Phase 7 (Verifying):
update_scan_status(scan.id, ScanStatus.VERIFYING.value, {
    "current_agent": "verifier",
    "agent_message": "Running tests + re-exploit against patched code..."
})

# Phase 8 (Fixed):
update_scan_status(scan.id, ScanStatus.FIXED.value, {
    "current_agent": None,
    "agent_message": "Vulnerability fixed and PR opened",
    "patch_diff": remediation["patched_code"],
    "pr_url": pr_url,
    "patch_attempts": remediation.get("attempts", 1)
})
```

**Also update `_broadcast()` to include new fields:**
```python
def _broadcast(scan: Scan):
    try:
        from routes.scans import notify_scan_update_sync
        notify_scan_update_sync({
            "id": scan.id,
            "repo_id": scan.repo_id,
            "commit_sha": scan.commit_sha,
            "branch": scan.branch,
            "status": scan.status,
            "vulnerability_type": scan.vulnerability_type,
            "severity": scan.severity,
            "vulnerable_file": scan.vulnerable_file,
            "current_agent": scan.current_agent,
            "agent_message": scan.agent_message,
            "pr_url": scan.pr_url,
            "created_at": str(scan.created_at),
        })
    except Exception:
        pass
```

**Also update `update_scan_status()` to handle new fields** — add to the `if extra:` block:
```python
if "current_agent" in extra:
    scan.current_agent = extra["current_agent"]
if "agent_message" in extra:
    scan.agent_message = extra["agent_message"]
if "original_code" in extra:
    scan.original_code = extra["original_code"]
if "exploit_script" in extra:
    scan.exploit_script = extra["exploit_script"]
if "findings_json" in extra:
    scan.findings_json = extra["findings_json"]
if "patch_attempts" in extra:
    scan.patch_attempts = extra["patch_attempts"]
if "error_message" in extra:
    scan.error_message = extra["error_message"]
```

---

### A3. Stats Endpoint

#### [MODIFY] [scans.py](file:///Users/jivitrana/Desktop/Aegis/routes/scans.py)

Add a new `GET /api/stats?user_id=X` endpoint that returns:
```json
{
  "total_repos": 4,
  "active_scans": 2,
  "vulns_fixed": 127,
  "total_scans": 340,
  "false_positives": 15,
  "last_scan_at": "2026-04-24T12:00:00Z"
}
```

Uses SQLAlchemy `count()` queries filtered by user's repo IDs.

---

### A4. Enhanced Scan Responses

#### [MODIFY] [scans.py](file:///Users/jivitrana/Desktop/Aegis/routes/scans.py) — `get_scan()`, `list_scans()`, SSE generator

Add new fields to all scan response payloads:
- `original_code`, `exploit_script`, `findings_json`
- `current_agent`, `agent_message`, `patch_attempts`
- `error_message`

---

## Part B: Frontend Changes

---

### B1. Install Dependencies

Add `react-syntax-highlighter` for code highlighting in ExploitTerminal and CodeDiff.

---

### B2. Design System

#### [MODIFY] [globals.css](file:///Users/jivitrana/Desktop/Aegis/aegis-frontend/app/globals.css)

- Replace dark mode palette with deep navy background + agent-identity accent colors
- Add CSS custom properties: `--agent-finder` (violet), `--agent-exploiter` (red), `--agent-engineer` (amber), `--agent-verifier` (emerald)
- Add keyframe animations: `pulse-ring`, `pipeline-fill`, `scanline-drift`, `typewriter`, `status-glow`
- Add utility classes: `.aegis-terminal`, `.aegis-pipeline-node`, `.aegis-gradient-border`

---

### B3. New Atomic Components

#### [NEW] `components/AgentAvatar.tsx`
Agent identity component with icon, color, label, pulse ring animation. Sizes: sm/md/lg.

#### [NEW] `components/LiveTimer.tsx`
Elapsed time counter that updates every second. Shows "Xs" or "Xm Ys" format.

#### [NEW] `components/StatCard.tsx`
Glassmorphism stat card with icon, value, label. Optional pulsing indicator.

---

### B4. Feature Components

#### [NEW] `components/PipelineTimeline.tsx`
Vertical animated pipeline for scan detail. Steps: Finder → Exploiter → Engineer → Verifier. Active step has pulse ring + LiveTimer. Completed steps show duration. Connecting lines fill with gradient animation.

#### [NEW] `components/ExploitTerminal.tsx`
Terminal-style output display. Near-black background, scanline overlay, green-tinted monospace text, "VULNERABLE" in red, typewriter animation on first load, copy button.

#### [NEW] `components/CodeDiff.tsx`
Before/after code diff viewer. Line-by-line diff computed client-side, red background for removed lines, green for added, syntax highlighting via react-syntax-highlighter, line numbers.

---

### B5. Page Redesigns

#### [MODIFY] [page.tsx](file:///Users/jivitrana/Desktop/Aegis/aegis-frontend/app/page.tsx) — Landing
- Animated shield hero with pulse rings
- 2×2 Agent Showcase cards (Finder/Exploiter/Engineer/Verifier with colors)
- Auto-playing pipeline demo (6-second loop)
- Stats bar with hardcoded numbers

#### [MODIFY] [dashboard/page.tsx](file:///Users/jivitrana/Desktop/Aegis/aegis-frontend/app/dashboard/page.tsx)
- Stats row (4 StatCards from `/api/stats`)
- 2-column layout: Repos (left 40%) + Live Scan Feed (right 60%)
- Active scans at top with glowing border, AgentAvatar, LiveTimer
- Completed scans below with muted styling

#### [MODIFY] [scans/[id]/page.tsx](file:///Users/jivitrana/Desktop/Aegis/aegis-frontend/app/scans/%5Bid%5D/page.tsx)
- 2-panel layout: PipelineTimeline (left 35%) + Active Content (right 65%)
- Right panel shows ExploitTerminal, CodeDiff, or agent-working animation based on status
- PR CTA card with animated gradient border when fixed

#### [MODIFY] [api.ts](file:///Users/jivitrana/Desktop/Aegis/aegis-frontend/lib/api.ts)
- Add `getStats()`, `triggerScan()` methods
- Add `StatsInfo` type, enhance `ScanInfo` with new fields

#### [MODIFY] [VulnCard.tsx](file:///Users/jivitrana/Desktop/Aegis/aegis-frontend/components/VulnCard.tsx)
- Add AgentAvatar for active scans showing `current_agent`
- Add LiveTimer for active scans
- Add `agent_message` text display
- Active scans get `status-glow` animation

---

## Part C: Execution Order

| Phase | Priority | Files | Description | Est. |
|-------|----------|-------|-------------|------|
| **1** | 🔴 | `database/models.py` | Add new columns to Scan model | 15min |
| **2** | 🔴 | `orchestrator.py` | Set current_agent + agent_message at each pipeline step | 30min |
| **3** | 🔴 | `routes/scans.py` | Stats endpoint + new fields in responses + SSE | 30min |
| **4** | 🔴 | Delete `aegis.db`, restart | Apply schema changes | 5min |
| **5** | 🔴 | `globals.css` | Agent colors, keyframes, utility classes | 45min |
| **6** | 🔴 | `AgentAvatar.tsx`, `LiveTimer.tsx`, `StatCard.tsx` | Atomic components | 1hr |
| **7** | 🔴 | `api.ts` | New types, getStats(), triggerScan() | 20min |
| **8** | 🟡 | `PipelineTimeline.tsx` | Vertical animated pipeline | 1.5hr |
| **9** | 🟡 | `ExploitTerminal.tsx` | Terminal with typewriter + syntax highlighting | 1.5hr |
| **10** | 🟡 | `CodeDiff.tsx` | Before/after diff viewer | 1.5hr |
| **11** | 🟡 | `scans/[id]/page.tsx` | Scan detail redesign | 2hr |
| **12** | 🟡 | `dashboard/page.tsx` | Mission control dashboard | 2hr |
| **13** | 🟡 | `VulnCard.tsx` | Agent avatar + live timer | 45min |
| **14** | 🟢 | `page.tsx` (landing) | Agent showcase + pipeline demo | 2hr |
| **15** | 🟢 | `AddRepoModal.tsx` | Progress steps + URL validation | 30min |
| **16** | ⚪ | Polish | Responsive, edge cases, loading skeletons | 1hr |

**Total: ~16 hours** | **Critical path**: 1→4 (backend) → 5→7 (design system) → 8→11 (scan detail) → 12→14 (dashboard + landing)

---

## Part D: Verification Plan

### Backend (Phases 1-4)
```bash
rm aegis.db && python main.py
curl http://localhost:8000/health
curl "http://localhost:8000/api/stats?user_id=1"
curl -X POST "http://localhost:8000/api/scans/trigger?repo_id=1"
curl http://localhost:8000/api/scans  # Verify current_agent, agent_message fields
```

### Frontend (Phases 5-16)
```bash
cd aegis-frontend && npm run build  # Must pass
npm run dev  # Manual check each page
```

### Browser Testing
- Screenshot each page
- Verify animations (pipeline fill, typewriter, pulse rings)
- Test scan detail with each status (clean, fixed, failed, in-progress)
- Verify SSE real-time updates during active scan

---

## Part E: The Differentiating Principle

Every security tool shows statuses. **None of them show agents with identity.**

- **Finder** (violet) = analysis, cerebral
- **Exploiter** (red) = danger, offensive
- **Engineer** (amber) = building, constructive
- **Verifier** (emerald) = safety, confirmation

When the UI turns red with a crosshair icon, judges *feel* the exploit. When it turns green with a shield check, they feel relief. This emotional arc — danger → resolution — is what wins hackathons.
