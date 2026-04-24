"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  api,
  type ScanInfo,
  type ScanStatus,
  isActiveScan,
  parseFindingsJson,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { AgentAvatar } from "@/components/AgentAvatar";
import { LiveTimer } from "@/components/LiveTimer";
import ExploitTerminal from "@/components/ExploitTerminal";
import CodeDiff from "@/components/CodeDiff";
import { FindingsPanel } from "@/components/FindingsPanel";
import {
  Shield,
  ArrowLeft,
  ExternalLink,
  GitCommit,
  GitBranch,
  FileCode2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  Zap,
} from "lucide-react";

// ── Severity badge ────────────────────────────────────────
function SeverityBadge({ severity }: { severity: string | null }) {
  if (!severity) return null;
  const s = severity.toUpperCase();
  const cls =
    s === "ERROR" || s === "CRITICAL" || s === "HIGH"
      ? "bg-red-500/15 text-red-400 border-red-500/30"
      : s === "WARNING" || s === "MEDIUM"
      ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
      : "bg-blue-500/15 text-blue-400 border-blue-500/30";
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {s}
    </span>
  );
}

// ── Status badge ──────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    queued:            { label: "Queued",        cls: "bg-white/5 text-muted-foreground border-white/10" },
    scanning:          { label: "Scanning",      cls: "bg-violet-500/15 text-violet-400 border-violet-500/30" },
    exploiting:        { label: "Exploiting",    cls: "bg-red-500/15 text-red-400 border-red-500/30 status-pulse" },
    exploit_confirmed: { label: "Exploit Found", cls: "bg-red-500/20 text-red-300 border-red-500/50 font-bold" },
    patching:          { label: "Patching",      cls: "bg-amber-500/15 text-amber-400 border-amber-500/30 status-pulse" },
    verifying:         { label: "Verifying",     cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 status-pulse" },
    fixed:             { label: "Fixed",         cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
    false_positive:    { label: "False Positive",cls: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
    clean:             { label: "Clean",         cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
    failed:            { label: "Failed",        cls: "bg-red-500/15 text-red-400 border-red-500/30" },
  };
  const c = map[status] ?? { label: status, cls: "bg-white/5 text-muted-foreground border-white/10" };
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold ${c.cls}`}>
      {c.label}
    </span>
  );
}

// ── Agent Working Panel ───────────────────────────────────
function AgentWorkingPanel({ scan }: { scan: ScanInfo }) {
  const agent = scan.current_agent as "finder" | "exploiter" | "engineer" | "verifier" | null;
  if (!agent) return null;
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
      <AgentAvatar agent={agent} size="lg" showRing={true} showLabel={true} />
      <div className="space-y-1.5">
        <p className="text-sm font-medium text-foreground">
          {scan.agent_message ?? `The ${agent} is working...`}
        </p>
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <LiveTimer startTime={scan.created_at} isActive={true} />
        </div>
      </div>
    </div>
  );
}

// ── Exploit Confirmed — dramatic moment ───────────────────
function ExploitConfirmedBanner({ scan }: { scan: ScanInfo }) {
  return (
    <div className="rounded-xl border border-red-500/40 bg-red-500/8 p-5 aegis-glow-red">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-10 w-10 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center">
          <Zap className="h-5 w-5 text-red-400" />
        </div>
        <div>
          <p className="font-bold text-red-400">Exploit Confirmed</p>
          <p className="text-xs text-muted-foreground">
            {scan.vulnerability_type} proven exploitable in Docker sandbox
          </p>
        </div>
      </div>
      {scan.exploit_output && (
        <ExploitTerminal
          output={scan.exploit_output}
          exploitScript={scan.exploit_script}
          status="vulnerable"
          title="Live Exploit — Docker Sandbox"
        />
      )}
    </div>
  );
}

// ── Right panel (context-aware by status) ────────────────
function ActivePanel({ scan }: { scan: ScanInfo }) {
  const status = scan.status;

  // Exploit just confirmed — dramatic moment
  if (status === "exploit_confirmed") {
    return <ExploitConfirmedBanner scan={scan} />;
  }

  // Still scanning/exploiting with no output yet
  if (isActiveScan(status as ScanStatus) && !scan.exploit_output && !scan.patch_diff) {
    return <AgentWorkingPanel scan={scan} />;
  }

  // Patching — show terminal + agent working
  if (status === "patching") {
    return (
      <div className="space-y-4">
        {scan.exploit_output && (
          <ExploitTerminal
            output={scan.exploit_output}
            exploitScript={scan.exploit_script}
            status="vulnerable"
          />
        )}
        <AgentWorkingPanel scan={scan} />
      </div>
    );
  }

  // Verifying — show terminal + diff if available
  if (status === "verifying") {
    return (
      <div className="space-y-4">
        {scan.exploit_output && (
          <ExploitTerminal
            output={scan.exploit_output}
            exploitScript={scan.exploit_script}
            status="vulnerable"
          />
        )}
        {scan.original_code && scan.patch_diff ? (
          <CodeDiff
            before={scan.original_code}
            after={scan.patch_diff}
            filename={scan.vulnerable_file ?? "patch"}
            language="python"
          />
        ) : (
          <AgentWorkingPanel scan={scan} />
        )}
      </div>
    );
  }

  // Fallback for other active states
  return <AgentWorkingPanel scan={scan} />;
}

// ── PR Result Card ────────────────────────────────────────
function PRResultCard({ scan }: { scan: ScanInfo }) {
  if (!scan.pr_url) return null;
  return (
    <div className="aegis-gradient-border rounded-xl p-px">
      <div className="rounded-xl bg-card p-5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
              <Sparkles className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="font-semibold text-emerald-400">Vulnerability Fixed!</p>
              <p className="text-sm text-muted-foreground">
                {scan.vulnerability_type} in{" "}
                <code className="text-primary">{scan.vulnerable_file}</code> has been patched.
              </p>
            </div>
          </div>
          <a href={scan.pr_url} target="_blank" rel="noopener noreferrer">
            <Button className="shrink-0 gap-2 bg-emerald-500/90 hover:bg-emerald-500 text-black font-semibold aegis-glow-emerald">
              <ExternalLink className="h-4 w-4" />
              Review PR on GitHub
            </Button>
          </a>
        </div>
      </div>
    </div>
  );
}

// ── Terminal result cards ─────────────────────────────────
function ResultCard({ scan }: { scan: ScanInfo }) {
  if (scan.status === "clean") {
    return (
      <div className="flex items-center gap-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
        <CheckCircle2 className="h-8 w-8 text-emerald-400 shrink-0" />
        <div>
          <p className="font-semibold text-emerald-400">Code is clean!</p>
          <p className="text-sm text-muted-foreground">No vulnerabilities found in this commit.</p>
        </div>
      </div>
    );
  }
  if (scan.status === "false_positive") {
    return (
      <div className="flex items-center gap-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-5">
        <AlertTriangle className="h-8 w-8 text-amber-400 shrink-0" />
        <div>
          <p className="font-semibold text-amber-400">False Positive</p>
          <p className="text-sm text-muted-foreground">
            The Finder flagged a potential issue, but the Exploiter could not confirm it was
            exploitable in the Docker sandbox.
          </p>
        </div>
      </div>
    );
  }
  if (scan.status === "failed") {
    return (
      <div className="flex items-center gap-4 rounded-xl border border-red-500/20 bg-red-500/5 p-5">
        <XCircle className="h-8 w-8 text-red-400 shrink-0" />
        <div>
          <p className="font-semibold text-red-400">Pipeline Failed</p>
          <p className="text-sm text-muted-foreground">
            {scan.error_message ?? "An error occurred during the scan. Human review required."}
          </p>
        </div>
      </div>
    );
  }
  return null;
}

// ── Main Page ─────────────────────────────────────────────
export default function ScanDetailPage() {
  const params = useParams();
  const scanId = Number(params.id);
  const [scan, setScan] = useState<ScanInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initial fetch
    api.getScan(scanId)
      .then(setScan)
      .catch(() => {})
      .finally(() => setLoading(false));

    // Use SSE for live updates — merge to preserve fields not in SSE payload
    const es = api.connectLiveFeed((data) => {
      if (data.id === scanId) {
        setScan(prev => prev ? { ...prev, ...data } : data);
        // When scan reaches terminal state, do a full REST fetch to get all fields
        // (exploit_script, original_code, patch_diff, findings_json not in SSE)
        if (["fixed", "failed", "false_positive", "clean"].includes(data.status)) {
          api.getScan(scanId).then(setScan).catch(() => {});
        }
      }
    });

    return () => es.close();
  }, [scanId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Shield className="h-12 w-12 text-primary status-pulse" />
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center space-y-3">
          <XCircle className="mx-auto h-10 w-10 text-destructive" />
          <p className="text-muted-foreground">Scan not found</p>
          <Link href="/dashboard">
            <Button variant="outline" size="sm">Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  const active = isActiveScan(scan.status as ScanStatus);
  const showResultCard = ["clean", "false_positive", "failed"].includes(scan.status);
  const findings = parseFindingsJson(scan.findings_json);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Button>
            </Link>
            <div className="h-4 w-px bg-border" />
            <Shield className="h-5 w-5 text-primary" />
            <span className="font-semibold text-sm">Scan #{scan.id}</span>
            {scan.vulnerability_type && (
              <>
                <div className="h-4 w-px bg-border" />
                <span className="text-sm text-muted-foreground">{scan.vulnerability_type}</span>
                <SeverityBadge severity={scan.severity} />
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            {active && <LiveTimer startTime={scan.created_at} isActive={true} />}
            <StatusBadge status={scan.status} />
            {scan.pr_url && (
              <a href={scan.pr_url} target="_blank" rel="noopener noreferrer">
                <Button size="sm" variant="outline" className="gap-1.5 text-emerald-400 border-emerald-500/30">
                  <ExternalLink className="h-3.5 w-3.5" />
                  View PR
                </Button>
              </a>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Meta row */}
        <div className="mb-6 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <GitCommit className="h-3.5 w-3.5" />
            <code className="font-mono">{scan.commit_sha.slice(0, 8)}</code>
          </span>
          <span className="flex items-center gap-1.5">
            <GitBranch className="h-3.5 w-3.5" />
            <code className="font-mono text-primary">{scan.branch}</code>
          </span>
          {scan.vulnerable_file && (
            <span className="flex items-center gap-1.5">
              <FileCode2 className="h-3.5 w-3.5" />
              <code className="font-mono text-primary">{scan.vulnerable_file}</code>
            </span>
          )}
          <span>{new Date(scan.created_at).toLocaleString()}</span>
        </div>

        {/* Two-panel layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">

          {/* Left: Pipeline + findings */}
          <div className="space-y-4">
            <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-sm">
              <h2 className="mb-5 text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                Agent Pipeline
              </h2>
              <PipelineTimeline scan={scan} />
            </div>

            {/* All findings from Finder */}
            {findings.length > 0 && (
              <FindingsPanel
                findings={findings}
                confirmedVulnType={scan.vulnerability_type}
              />
            )}

            {showResultCard && <ResultCard scan={scan} />}
          </div>

          {/* Right: Active content */}
          <div className="space-y-4">
            {/* Active states */}
            {!showResultCard && scan.status !== "fixed" && (
              <ActivePanel scan={scan} />
            )}

            {/* Fixed: full story — terminal + diff + PR */}
            {scan.status === "fixed" && (
              <>
                {scan.exploit_output && (
                  <ExploitTerminal
                    output={scan.exploit_output}
                    exploitScript={scan.exploit_script}
                    status="vulnerable"
                    title="Exploit Proof — Docker Sandbox"
                  />
                )}
                {scan.original_code && scan.patch_diff && (
                  <CodeDiff
                    before={scan.original_code}
                    after={scan.patch_diff}
                    filename={scan.vulnerable_file ?? "patch"}
                    language="python"
                  />
                )}
                <PRResultCard scan={scan} />
              </>
            )}

            {/* False positive terminal */}
            {scan.status === "false_positive" && scan.exploit_output && (
              <ExploitTerminal
                output={scan.exploit_output}
                exploitScript={scan.exploit_script}
                status="not_vulnerable"
                title="Exploit Output — Not Confirmed"
              />
            )}

            {/* Failed error */}
            {scan.status === "failed" && scan.error_message && (
              <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
                <p className="text-xs font-mono text-red-400 whitespace-pre-wrap">{scan.error_message}</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
