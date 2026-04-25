"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type ScanInfo, type ScanStatus, isActiveScan, parseFindingsJson } from "@/lib/api";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { AgentAvatar } from "@/components/AgentAvatar";
import { LiveTimer } from "@/components/LiveTimer";
import ExploitTerminal from "@/components/ExploitTerminal";
import CodeDiff from "@/components/CodeDiff";
import { FindingsPanel } from "@/components/FindingsPanel";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CriticalApprovalBanner } from "@/components/CriticalApprovalBanner";
import { ThemeToggle } from "@/components/ThemeToggle";

function M(p: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <span style={{ fontFamily: "var(--font-share-tech-mono,monospace)", ...p.style }}>{p.children}</span>;
}

function SevBadge({ severity }: { severity: string | null }) {
  if (!severity) return null;
  const s = severity.toUpperCase();
  const color = ["CRITICAL", "HIGH", "ERROR"].includes(s) ? "var(--red)" : s === "MEDIUM" ? "var(--amber)" : "var(--blue)";
  const bg = ["CRITICAL", "HIGH", "ERROR"].includes(s) ? "var(--red-dim)" : s === "MEDIUM" ? "var(--amber-dim)" : "var(--blue-dim)";
  return <span style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 10, padding: "2px 8px", background: bg, color, letterSpacing: "0.1em", textTransform: "uppercase" }}>{s}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, [string, string]> = {
    queued:            ["Queued",          "var(--muted)"],
    scanning:          ["Scanning",        "var(--agent-finder)"],
    exploiting:        ["Exploiting",      "var(--red)"],
    exploit_confirmed: ["Exploit Found",   "var(--red)"],
    patching:          ["Patching",        "var(--blue)"],
    verifying:         ["Verifying",       "var(--agent-verifier)"],
    awaiting_approval: ["Awaiting Approval","var(--amber)"],
    fixed:             ["Fixed ✓",        "var(--agent-verifier)"],
    false_positive:    ["False Positive",  "var(--amber)"],
    clean:             ["Clean ✓",        "var(--agent-verifier)"],
    failed:            ["Failed",          "var(--red)"],
    regression:        ["Regression",      "var(--red)"],
  };
  const [label, color] = m[status] ?? [status, "var(--muted)"];
  return <M style={{ fontSize: 10, padding: "2px 8px", background: `${color}18`, color, letterSpacing: "0.1em", textTransform: "uppercase" }}>{label}</M>;
}

function AgentWorkingPanel({ scan }: { scan: ScanInfo }) {
  const agent = scan.current_agent as "finder" | "exploiter" | "engineer" | "verifier" | null;
  if (!agent) return null;
  const agentColor = agent === "finder" ? "var(--agent-finder)" : agent === "exploiter" ? "var(--red)" : agent === "engineer" ? "var(--blue)" : "var(--agent-verifier)";
  return (
    <div style={{ border: `1px solid ${agentColor}30`, background: `${agentColor}08`, padding: 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 16, textAlign: "center" }}>
      <AgentAvatar agent={agent} size="lg" showRing={true} showLabel={false} />
      <div>
        <div style={{ fontFamily: "var(--font-syne,sans-serif)", fontWeight: 700, fontSize: 18, marginBottom: 8, textTransform: "capitalize" }}>{agent.replace("_", " ")} Active</div>
        <div style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 12, color: agentColor, maxWidth: 400, lineHeight: 1.6 }}>
          {scan.agent_message ?? `// ${agent} is analyzing...`}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 16px", border: "1px solid var(--border)", background: "var(--surface)" }}>
        <span style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 11, color: "var(--muted)" }}>Elapsed:</span>
        <LiveTimer startTime={scan.created_at} isActive={true} />
      </div>
    </div>
  );
}

function PRResultCard({ scan }: { scan: ScanInfo }) {
  if (!scan.pr_url) return null;
  return (
    <div className="aegis-gradient-border" style={{ padding: 1 }}>
      <div style={{ background: "var(--card)", padding: 20, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontFamily: "var(--font-syne,sans-serif)", fontWeight: 700, fontSize: 16, color: "var(--agent-verifier)", marginBottom: 4 }}>✓ Vulnerability Fixed</div>
          <div style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 11, color: "var(--muted)" }}>
            {scan.vulnerability_type} in <span style={{ color: "var(--blue)" }}>{scan.vulnerable_file}</span> has been patched.
          </div>
        </div>
        <a href={scan.pr_url} target="_blank" rel="noopener noreferrer" className="aegis-btn-shimmer" style={{
          fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 11, padding: "10px 20px",
          background: "var(--agent-verifier)", color: "var(--background)", textDecoration: "none",
          letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600,
        }}>
          Review PR on GitHub ↗
        </a>
      </div>
    </div>
  );
}

function ResultCard({ scan }: { scan: ScanInfo }) {
  const configs: Record<string, { color: string; icon: string; title: string; desc: string }> = {
    clean:          { color: "var(--agent-verifier)", icon: "✓", title: "Code is Clean",  desc: "No vulnerabilities found in this commit." },
    false_positive: { color: "var(--amber)",          icon: "⚠", title: "False Positive", desc: "The Exploiter could not confirm this vulnerability in the Docker sandbox." },
    failed:         { color: "var(--red)",            icon: "✕", title: "Pipeline Failed", desc: scan.error_message ?? "An error occurred. Human review required." },
  };
  const c = configs[scan.status];
  if (!c) return null;
  return (
    <div style={{ border: `1px solid ${c.color}30`, background: `${c.color}08`, padding: 20, display: "flex", alignItems: "flex-start", gap: 14 }}>
      <div style={{ width: 36, height: 36, border: `1px solid ${c.color}40`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, color: c.color, flexShrink: 0 }}>{c.icon}</div>
      <div>
        <div style={{ fontFamily: "var(--font-syne,sans-serif)", fontWeight: 700, fontSize: 15, color: c.color, marginBottom: 6 }}>{c.title}</div>
        <div style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 12, color: "var(--muted)", lineHeight: 1.6 }}>{c.desc}</div>
      </div>
    </div>
  );
}

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = Number(params.id);
  const [scan, setScan] = useState<ScanInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getScan(scanId).then(setScan).catch(() => {}).finally(() => setLoading(false));
    const es = api.connectLiveFeed((data) => {
      if (data.id === scanId) {
        setScan((prev) => (prev ? { ...prev, ...data } : data));
        if (["fixed", "failed", "false_positive", "clean", "awaiting_approval"].includes(data.status)) {
          api.getScan(scanId).then(setScan).catch(() => {});
        }
      }
    });
    return () => es.close();
  }, [scanId]);

  async function handleApprove() { if (scan) await api.approveScan(scan.id).catch(console.error); }
  async function handleReject(reason: string) { if (scan) await api.rejectScan(scan.id, reason).catch(console.error); }

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: 16 }}>
      <div style={{ fontFamily: "var(--font-syne,sans-serif)", fontWeight: 800, fontSize: 24 }}>AE<span style={{ color: "var(--green)" }}>G</span>IS</div>
      <M style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.15em", animation: "pulse 2s infinite" }}>// LOADING SCAN DATA...</M>
    </div>
  );

  if (!scan) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: 12 }}>
      <M style={{ fontSize: 14, color: "var(--red)" }}>// ERROR: Scan #{scanId} not found</M>
      <Link href="/dashboard" style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 11, color: "var(--muted)", padding: "8px 16px", border: "1px solid var(--border)", textDecoration: "none" }}>← Back to Dashboard</Link>
    </div>
  );

  const active = isActiveScan(scan.status as ScanStatus);
  const isTerminal = ["clean", "false_positive", "failed"].includes(scan.status);
  const findings = parseFindingsJson(scan.findings_json);

  return (
    <div style={{ minHeight: "100vh", background: "var(--background)" }}>
      {/* ── Header ── */}
      <header className="aegis-glass-nav" style={{ position: "sticky", top: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/dashboard" style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 11, color: "var(--muted)", textDecoration: "none", letterSpacing: "0.08em", padding: "5px 10px", border: "1px solid var(--border)" }}>← Dashboard</Link>
          <div style={{ width: 1, height: 16, background: "var(--border)" }} />
          <div style={{ fontFamily: "var(--font-syne,sans-serif)", fontWeight: 700, fontSize: 14 }}>Scan #{scan.id}</div>
          {scan.vulnerability_type && (
            <>
              <div style={{ width: 1, height: 16, background: "var(--border)" }} />
              <M style={{ fontSize: 12, color: "var(--foreground)" }}>{scan.vulnerability_type}</M>
              <SevBadge severity={scan.severity} />
            </>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ThemeToggle />
          {active && <LiveTimer startTime={scan.created_at} isActive={true} />}
          <StatusBadge status={scan.status} />
          {scan.vulnerability_type && (
            <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/scans/${scan.id}/sarif`} download
              style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 10, padding: "5px 12px", border: "1px solid var(--border)", color: "var(--muted)", textDecoration: "none", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              ↓ SARIF
            </a>
          )}
          {scan.pr_url && (
            <a href={scan.pr_url} target="_blank" rel="noopener noreferrer"
              style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 10, padding: "5px 12px", border: "1px solid var(--agent-verifier)", color: "var(--agent-verifier)", textDecoration: "none", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              View PR ↗
            </a>
          )}
        </div>
      </header>

      {/* ── Meta row ── */}
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "16px 28px", display: "flex", gap: 20, flexWrap: "wrap", borderBottom: "1px solid var(--border)" }}>
        {[
          { label: "COMMIT", val: scan.commit_sha.slice(0, 8) },
          { label: "BRANCH", val: scan.branch, color: "var(--blue)" },
          scan.vulnerable_file && { label: "FILE", val: scan.vulnerable_file, color: "var(--agent-finder)" },
          { label: "STARTED", val: new Date(scan.created_at).toLocaleString() },
        ].filter(Boolean).map((item: any) => (
          <div key={item.label} style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <M style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>{item.label}</M>
            <M style={{ fontSize: 11, color: item.color ?? "var(--foreground)" }}>{item.val}</M>
          </div>
        ))}
      </div>

      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "28px", display: "grid", gridTemplateColumns: "300px 1fr", gap: 1, background: "var(--border)", border: "1px solid var(--border)", margin: "24px auto", maxWidth: 1280 }}>
        {/* ── Left: Pipeline ── */}
        <div style={{ background: "var(--surface)", padding: 24 }}>
          <M style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase", display: "block", marginBottom: 20 }}>// Agent Pipeline</M>
          <ErrorBoundary fallbackTitle="Pipeline timeline failed">
            <PipelineTimeline scan={scan} />
          </ErrorBoundary>
          {findings.length > 0 && (
            <ErrorBoundary fallbackTitle="Findings panel failed">
              <div style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 24 }}>
                <FindingsPanel findings={findings} confirmedVulnType={scan.vulnerability_type} />
              </div>
            </ErrorBoundary>
          )}
          {isTerminal && (
            <div style={{ marginTop: 16 }}>
              <ResultCard scan={scan} />
            </div>
          )}
        </div>

        {/* ── Right: Active Content ── */}
        <div style={{ background: "var(--surface)", padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          {scan.status === "awaiting_approval" && (
            <CriticalApprovalBanner scan={scan} onApprove={handleApprove} onReject={handleReject} />
          )}

          {/* Active working state */}
          {active && !["exploit_confirmed", "awaiting_approval"].includes(scan.status) && !scan.exploit_output && !scan.patch_diff && (
            <AgentWorkingPanel scan={scan} />
          )}

          {/* Exploit output */}
          {scan.exploit_output && (
            <ErrorBoundary fallbackTitle="Terminal failed">
              <ExploitTerminal output={scan.exploit_output} exploitScript={scan.exploit_script} status={scan.status === "false_positive" ? "not_vulnerable" : "vulnerable"} title="Exploit Terminal — Docker Sandbox" />
            </ErrorBoundary>
          )}

          {/* Patch diff */}
          {scan.original_code && scan.patch_diff && (
            <ErrorBoundary fallbackTitle="Diff failed">
              <CodeDiff before={scan.original_code} after={scan.patch_diff} filename={scan.vulnerable_file ?? "patch"} language="python" />
            </ErrorBoundary>
          )}

          {/* PR card */}
          {scan.status === "fixed" && <PRResultCard scan={scan} />}

          {/* Error */}
          {scan.status === "failed" && scan.error_message && (
            <div style={{ border: "1px solid var(--red-dim)", background: "var(--red-dim)", padding: 16 }}>
              <M style={{ fontSize: 12, color: "var(--red)", display: "block", whiteSpace: "pre-wrap" }}>{scan.error_message}</M>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
