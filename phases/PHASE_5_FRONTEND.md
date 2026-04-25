# Phase 5 — Frontend Overhaul

> **Depends on:** Phases 3 + 4 complete (new API contracts, event-driven SSE)
>
> **Estimated effort:** 4-5 days
>
> **Goal:** Transform the frontend from "functional" to "impressive" — real-time pipeline visualization, proper diff viewer, error boundaries, human-in-the-loop approval, and intelligence dashboard.

---

## Task 5.1: Add React Error Boundaries

**Files:** NEW `components/ErrorBoundary.tsx`, `app/scans/[id]/page.tsx`, `app/dashboard/page.tsx`

**Current problem:** Any unhandled error (e.g., malformed `findings_json`) crashes the entire page.

**Steps:**
- [ ] Create `components/ErrorBoundary.tsx`:
  ```tsx
  "use client";
  import React from "react";
  import { Shield, RefreshCw } from "lucide-react";
  import { Button } from "@/components/ui/button";
  
  export class ErrorBoundary extends React.Component<
    { children: React.ReactNode; fallbackTitle?: string },
    { hasError: boolean; error: Error | null }
  > {
    state = { hasError: false, error: null as Error | null };
    
    static getDerivedStateFromError(error: Error) {
      return { hasError: true, error };
    }
    
    render() {
      if (this.state.hasError) {
        return (
          <div className="rounded-xl border border-red-500/30 bg-red-950/10 p-6 text-center">
            <Shield className="mx-auto h-8 w-8 text-red-400 mb-3" />
            <p className="font-semibold text-red-300 mb-1">
              {this.props.fallbackTitle || "Something went wrong"}
            </p>
            <p className="text-xs text-zinc-500 mb-3">{this.state.error?.message}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry
            </Button>
          </div>
        );
      }
      return this.props.children;
    }
  }
  ```
- [ ] Wrap the scan detail page content with `<ErrorBoundary>`
- [ ] Wrap the dashboard page content with `<ErrorBoundary>`
- [ ] Wrap individual components (CodeDiff, ExploitTerminal, FindingsPanel) with their own boundaries

**Verification:**
- Deliberately pass malformed data to a component → error boundary shows, rest of page works
- Click "Retry" → component re-renders

---

## Task 5.2: Upgrade Pipeline Timeline Visualization

**Files:** `components/PipelineTimeline.tsx`

**Current state:** Basic vertical timeline with agent names. Needs to be a live mission-control panel.

**Steps:**
- [ ] Redesign to show per-agent cards with:
  - State indicator: waiting (gray) | running (pulse) | success (green) | failed (red)
  - Elapsed time counter per phase
  - Last 2-3 log lines from that agent (from `agent_message`)
  - Expand/collapse for full output

- [ ] Add animated transitions between states (CSS `transition-all`)
- [ ] Show retry counter for Engineer: "Attempt 2/3"
- [ ] Show the Reviewer's diagnosis inline when available

**Verification:**
- During a live scan, each agent card lights up in sequence
- Elapsed time ticks up while agent is working
- Completed agents show green checkmark with total time

---

## Task 5.3: Upgrade Code Diff Viewer

**Files:** `components/CodeDiff.tsx`, `package.json`

**Current state:** Basic before/after side-by-side view. No syntax highlighting, no line numbers, no unified view.

**Steps:**
- [ ] Install `react-diff-viewer-continued`:
  ```bash
  npm install react-diff-viewer-continued
  ```
- [ ] Replace the custom CodeDiff with a proper diff viewer:
  ```tsx
  import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
  
  export default function CodeDiff({ before, after, filename, language }: Props) {
    return (
      <div className="rounded-xl border border-border/50 overflow-hidden">
        <div className="bg-card/80 px-4 py-2 border-b border-border/50 text-xs text-muted-foreground">
          {filename}
        </div>
        <ReactDiffViewer
          oldValue={before}
          newValue={after}
          splitView={true}
          useDarkTheme={true}
          compareMethod={DiffMethod.WORDS}
          styles={{
            variables: { dark: { diffViewerBackground: "#0a0a0a", ... } }
          }}
        />
      </div>
    );
  }
  ```
- [ ] Add toggle: Split view ↔ Unified view
- [ ] Highlight the vulnerability location with a special marker

**Verification:**
- Diff shows proper syntax-highlighted additions (green) and removals (red)
- Line numbers visible
- Toggle between split and unified works

---

## Task 5.4: Add Human-in-the-Loop Approval for CRITICAL

**Files:** NEW `components/CriticalApprovalBanner.tsx`, `app/scans/[id]/page.tsx`, backend routes

**Steps:**
- [ ] Backend: Add new scan status `AWAITING_APPROVAL`:
  ```python
  AWAITING_APPROVAL = "awaiting_approval"
  ```
- [ ] Backend: Add approval endpoint:
  ```python
  @router.post("/api/v1/scans/{scan_id}/approve")
  async def approve_critical_fix(scan_id: int):
      # Resume the pipeline...
  
  @router.post("/api/v1/scans/{scan_id}/reject")
  async def reject_fix(scan_id: int, reason: str = ""):
      # Mark as failed with reason...
  ```
- [ ] In the LangGraph pipeline (Phase 3), add interrupt before `pr_creator` for CRITICAL severity
- [ ] Frontend: Show approval banner when status is `awaiting_approval`:
  ```tsx
  function CriticalApprovalBanner({ scan, onApprove, onReject }) {
    return (
      <div className="border-2 border-amber-500/50 bg-amber-500/5 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="h-8 w-8 text-amber-400" />
          <div>
            <p className="font-bold text-amber-300">Critical Vulnerability — Approval Required</p>
            <p className="text-sm text-muted-foreground">
              Aegis found and patched a {scan.vulnerability_type} vulnerability. 
              Review the patch before creating the PR.
            </p>
          </div>
        </div>
        {/* Show: exploit proof, patch diff, test results */}
        <div className="flex gap-3 mt-4">
          <Button onClick={onApprove} className="bg-emerald-500 hover:bg-emerald-600">
            ✅ Approve & Create PR
          </Button>
          <Button onClick={onReject} variant="outline" className="text-red-400 border-red-500/30">
            ❌ Reject
          </Button>
        </div>
      </div>
    );
  }
  ```

**Verification:**
- CRITICAL vulnerability scan pauses after patching → shows approval banner
- Click Approve → PR is created
- Click Reject → scan marked as failed with reason

---

## Task 5.5: Add Browser Push Notifications

**Files:** NEW `components/NotificationManager.tsx`, `app/dashboard/page.tsx`

**Steps:**
- [ ] Request notification permission on dashboard mount
- [ ] When a scan reaches terminal state via SSE, trigger browser notification:
  ```tsx
  function notifyUser(scan: ScanInfo) {
    if (Notification.permission !== "granted") return;
    
    const title = scan.status === "fixed"
      ? `🛡️ Vulnerability Fixed`
      : scan.status === "failed"
      ? `❌ Scan Failed`
      : `📊 Scan Complete`;
    
    new Notification(title, {
      body: scan.vulnerability_type
        ? `${scan.vulnerability_type} in ${scan.vulnerable_file}`
        : `Scan #${scan.id} completed`,
      tag: `scan-${scan.id}`,
    });
  }
  ```

**Verification:**
- User grants notification permission
- Scan completes → browser notification appears
- Clicking notification focuses the dashboard

---

## Task 5.6: Add Search & Filter to Scan History

**Files:** `app/dashboard/page.tsx` or NEW `app/scans/page.tsx`

**Steps:**
- [ ] Add filter bar above scan list:
  - Status dropdown: All, Fixed, Failed, Clean, False Positive
  - Severity dropdown: All, Critical, High, Medium, Low
  - Free text search (vulnerability type)
  - Date range picker
- [ ] Pass filters as query params to paginated API
- [ ] Add sort options: Most Recent, Severity, Status

**Verification:**
- Filtering by "fixed" shows only fixed scans
- Searching for "SQL" shows only SQL injection scans
- Pagination works with filters

---

## Task 5.7: Add Exploit Code Viewer with Warning Gate

**Files:** `components/ExploitTerminal.tsx`

**Steps:**
- [ ] The exploit terminal already shows output. Add a toggle to view the actual exploit script:
  ```tsx
  const [showScript, setShowScript] = useState(false);
  
  {exploitScript && (
    <div className="mt-3">
      <button
        onClick={() => setShowScript(!showScript)}
        className="text-xs text-amber-400 flex items-center gap-1"
      >
        {showScript ? "Hide" : "Show"} Exploit Code
        <ChevronDown className={`h-3 w-3 transition ${showScript ? 'rotate-180' : ''}`} />
      </button>
      {showScript && (
        <div className="mt-2">
          <div className="bg-amber-500/10 border border-amber-500/20 rounded p-2 text-xs text-amber-300 mb-2">
            ⚠️ This is the exploit code Aegis generated to prove the vulnerability. 
            Shown for transparency only.
          </div>
          <pre className="bg-black/50 p-3 rounded text-xs text-green-400 overflow-x-auto">
            {exploitScript}
          </pre>
        </div>
      )}
    </div>
  )}
  ```

**Verification:**
- Exploit code is hidden by default
- Clicking "Show" reveals it with warning
- Code is syntax-highlighted and scrollable

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 5.1 | Error boundaries | 🔴 Critical | NEW `ErrorBoundary.tsx` |
| 5.2 | Pipeline timeline upgrade | 🟠 High | `PipelineTimeline.tsx` |
| 5.3 | Diff viewer upgrade | 🟠 High | `CodeDiff.tsx` |
| 5.4 | HITL approval for CRITICAL | 🟠 High | NEW `CriticalApprovalBanner.tsx`, backend |
| 5.5 | Push notifications | 🟡 Medium | NEW `NotificationManager.tsx` |
| 5.6 | Search & filter | 🟡 Medium | Dashboard page |
| 5.7 | Exploit code viewer | 🟡 Medium | `ExploitTerminal.tsx` |
