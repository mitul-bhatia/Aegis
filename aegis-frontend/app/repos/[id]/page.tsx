/* eslint-disable react/jsx-no-comment-textnodes */
"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  api,
  type RepoInfo,
  type ScanInfo,
  type ScanStatus,
  isActiveScan,
  parseFindingsJson,
  type FindingInfo,
} from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AgentAvatar } from "@/components/AgentAvatar";
import { LiveTimer } from "@/components/LiveTimer";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import {
  Shield,
  Play,
  ExternalLink,
  Trash2,
  ArrowLeft,
  RefreshCw,
  GitBranch,
  CheckCircle2,
  AlertTriangle,
  FileCode2,
  Clock,
  Terminal,
  Settings,
  Lock,
} from "lucide-react";

function M({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", ...style }}>
      {children}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string; bg: string }> = {
    queued:            { label: "Queued",          color: "var(--muted)",          bg: "rgba(255,255,255,0.04)" },
    scanning:          { label: "Scanning",        color: "var(--agent-finder)",   bg: "var(--violet-dim)" },
    exploiting:        { label: "Exploiting",      color: "var(--red)",            bg: "var(--red-dim)" },
    exploit_confirmed: { label: "Exploit Found",   color: "var(--red)",            bg: "var(--red-dim)" },
    patching:          { label: "Patching",        color: "var(--blue)",           bg: "var(--blue-dim)" },
    verifying:         { label: "Verifying",       color: "var(--agent-verifier)", bg: "var(--green-dim)" },
    awaiting_approval: { label: "Awaiting Approval", color: "var(--amber)",        bg: "var(--amber-dim)" },
    fixed:             { label: "Fixed ✓",        color: "var(--agent-verifier)", bg: "var(--green-dim)" },
    false_positive:    { label: "False Positive",  color: "var(--amber)",          bg: "var(--amber-dim)" },
    clean:             { label: "Clean ✓",        color: "var(--agent-verifier)", bg: "var(--green-dim)" },
    failed:            { label: "Failed",          color: "var(--red)",            bg: "var(--red-dim)" },
    monitoring:        { label: "Monitoring",      color: "var(--agent-verifier)", bg: "var(--green-dim)" },
    active:            { label: "Active",          color: "var(--agent-verifier)", bg: "var(--green-dim)" },
  };
  const c = map[status] ?? { label: status, color: "var(--muted)", bg: "rgba(255,255,255,0.04)" };
  return (
    <span
      style={{
        fontFamily: "var(--font-share-tech-mono, monospace)",
        fontSize: 10,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        padding: "2px 8px",
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.color}30`,
        whiteSpace: "nowrap",
      }}
    >
      {c.label}
    </span>
  );
}

function SevBadge({ severity }: { severity: string | null }) {
  if (!severity) return null;
  const s = severity.toUpperCase();
  const color = ["CRITICAL", "HIGH", "ERROR"].includes(s)
    ? "var(--red)"
    : s === "MEDIUM"
    ? "var(--amber)"
    : "var(--blue)";
  const bg = ["CRITICAL", "HIGH", "ERROR"].includes(s)
    ? "var(--red-dim)"
    : s === "MEDIUM"
    ? "var(--amber-dim)"
    : "var(--blue-dim)";
  return (
    <span
      style={{
        fontFamily: "var(--font-share-tech-mono, monospace)",
        fontSize: 10,
        padding: "2px 8px",
        background: bg,
        color,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        border: `1px solid ${color}40`,
      }}
    >
      {s}
    </span>
  );
}

export default function RepoDashboardPage() {
  const params = useParams();
  const repoId = Number(params?.id);
  const router = useRouter();

  const [repo, setRepo] = useState<RepoInfo | null>(null);
  const [scans, setScans] = useState<ScanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [activeTab, setActiveTab] = useState<"scans" | "vulnerabilities" | "config">("scans");

  const loadData = useCallback(async () => {
    if (isNaN(repoId)) return;
    try {
      const [repoData, scanData] = await Promise.all([
        api.getRepo(repoId),
        api.listScans(repoId, 1, 50),
      ]);
      setRepo(repoData);
      setScans(scanData.data || []);
    } catch (err) {
      console.error("Failed to load repo data:", err);
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    loadData();

    // Subscribe to SSE updates for this repo
    const es = api.connectLiveFeed((scanData) => {
      if (scanData.repo_id === repoId) {
        setScans((prev) => {
          const idx = prev.findIndex((s) => s.id === scanData.id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], ...scanData };
            return updated;
          }
          return [scanData, ...prev];
        });
      }
    });

    const interval = setInterval(loadData, 15000);
    return () => {
      es.close();
      clearInterval(interval);
    };
  }, [loadData, repoId]);

  async function handleTriggerScan() {
    if (!repo) return;
    setTriggering(true);
    try {
      await api.triggerScan(repo.id);
      await loadData();
    } catch (err) {
      console.error("Scan trigger failed:", err);
    } finally {
      setTimeout(() => setTriggering(false), 2000);
    }
  }

  async function handleDeleteRepo() {
    if (!repo) return;
    if (confirm(`Are you sure you want to stop monitoring ${repo.full_name}?`)) {
      try {
        await api.deleteRepo(repo.id);
        router.push("/dashboard");
      } catch (err) {
        alert("Failed to delete repository");
      }
    }
  }

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: 16 }}>
        <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 800, fontSize: 24 }}>
          AE<span style={{ color: "var(--green)" }}>G</span>IS
        </div>
        <M style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.15em", animation: "pulse 2s infinite" }}>
          // CONNECTING REPOSITORY TELEMETRY...
        </M>
      </div>
    );
  }

  if (!repo) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: 16 }}>
        <M style={{ fontSize: 14, color: "var(--red)" }}>// ERROR: Repository #{repoId} not found</M>
        <Link
          href="/dashboard"
          style={{
            fontFamily: "var(--font-share-tech-mono, monospace)",
            fontSize: 11,
            color: "var(--muted)",
            padding: "8px 16px",
            border: "1px solid var(--border)",
            textDecoration: "none",
          }}
        >
          ← Return to Mission Control
        </Link>
      </div>
    );
  }

  // Aggregate vulnerability findings from scans
  const allFindings: { finding: FindingInfo; scanId: number }[] = [];
  scans.forEach((s) => {
    const list = parseFindingsJson(s.findings_json);
    list.forEach((f) => {
      allFindings.push({ finding: f, scanId: s.id });
    });
  });

  const activeScansCount = scans.filter((s) => isActiveScan(s.status as ScanStatus)).length;
  const fixedCount = scans.filter((s) => s.status === "fixed").length;
  const hasVulnerabilities = scans.some((s) => ["awaiting_approval", "exploit_confirmed"].includes(s.status));

  return (
    <div style={{ minHeight: "100vh", background: "var(--background)", color: "var(--foreground)" }}>
      {/* ── Top Bar ── */}
      <header
        className="aegis-glass-nav"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 32px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Link
            href="/dashboard"
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 11,
              color: "var(--muted)",
              textDecoration: "none",
              letterSpacing: "0.08em",
              padding: "5px 12px",
              border: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "border-color 0.2s, color 0.2s",
            }}
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Mission Control
          </Link>
          <div style={{ width: 1, height: 16, background: "var(--border)" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16 }}>
              {repo.full_name}
            </span>
            <StatusBadge status={repo.status} />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ThemeToggle />
          <button
            onClick={handleTriggerScan}
            disabled={triggering}
            className="aegis-btn-shimmer"
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 11,
              padding: "7px 18px",
              background: "var(--green)",
              color: "#050709",
              border: "none",
              cursor: triggering ? "not-allowed" : "pointer",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            {triggering ? "Dispatching..." : "Scan Repo"}
          </button>
          <a
            href={repo.html_url || `https://github.com/${repo.full_name}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 11,
              padding: "6px 12px",
              border: "1px solid var(--border)",
              color: "var(--muted)",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <ExternalLink className="h-3.5 w-3.5" /> GitHub
          </a>
          <button
            onClick={handleDeleteRepo}
            title="Unlink repository"
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 11,
              padding: "6px 10px",
              border: "1px solid var(--border)",
              background: "transparent",
              color: "var(--muted)",
              cursor: "pointer",
              transition: "color 0.2s, border-color 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "var(--red)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--red)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "var(--muted)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {/* ── Subheader / Repository Telemetry ── */}
      <div
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--surface)",
          padding: "24px 32px",
        }}
      >
        <div style={{ maxWidth: 1400, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 20 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <Shield className="h-5 w-5 text-emerald-400" />
                <h1 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 800, fontSize: 24, margin: 0 }}>
                  {repo.full_name}
                </h1>
              </div>
              <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)", margin: 0 }}>
                Autonomous security monitoring active via GitHub App installation. AST indexed & monitored.
              </p>
            </div>

            <div style={{ display: "flex", gap: 16 }}>
              <div style={{ padding: "12px 20px", background: "var(--card)", border: "1px solid var(--border)", minWidth: 120 }}>
                <M style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  SECURITY STATUS
                </M>
                <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16, color: hasVulnerabilities ? "var(--amber)" : "var(--green)" }}>
                  {hasVulnerabilities ? "Action Required" : "Protected"}
                </div>
              </div>

              <div style={{ padding: "12px 20px", background: "var(--card)", border: "1px solid var(--border)", minWidth: 110 }}>
                <M style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  TOTAL SCANS
                </M>
                <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16 }}>
                  {scans.length}
                </div>
              </div>

              <div style={{ padding: "12px 20px", background: "var(--card)", border: "1px solid var(--border)", minWidth: 110 }}>
                <M style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  FIXED FLAWS
                </M>
                <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16, color: "var(--green)" }}>
                  {fixedCount}
                </div>
              </div>

              <div style={{ padding: "12px 20px", background: "var(--card)", border: "1px solid var(--border)", minWidth: 110 }}>
                <M style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  BRANCH
                </M>
                <div style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 13, color: "var(--blue)" }}>
                  main
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Workspace ── */}
      <main className="max-w-[1400px] mx-auto px-4 md:px-8 py-7">
        {/* Navigation Tabs */}
        <div style={{ display: "flex", gap: 12, borderBottom: "1px solid var(--border)", marginBottom: 24, overflowX: "auto" }}>
          <button
            onClick={() => setActiveTab("scans")}
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 12,
              padding: "10px 18px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "scans" ? "2px solid var(--green)" : "2px solid transparent",
              color: activeTab === "scans" ? "var(--green)" : "var(--muted)",
              cursor: "pointer",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              gap: 8,
              whiteSpace: "nowrap",
            }}
          >
            <Clock className="h-3.5 w-3.5" /> Pipeline Scans ({scans.length})
          </button>
          <button
            onClick={() => setActiveTab("vulnerabilities")}
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 12,
              padding: "10px 18px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "vulnerabilities" ? "2px solid var(--green)" : "2px solid transparent",
              color: activeTab === "vulnerabilities" ? "var(--green)" : "var(--muted)",
              cursor: "pointer",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              gap: 8,
              whiteSpace: "nowrap",
            }}
          >
            <AlertTriangle className="h-3.5 w-3.5" /> Detected Findings ({allFindings.length})
          </button>
          <button
            onClick={() => setActiveTab("config")}
            style={{
              fontFamily: "var(--font-share-tech-mono, monospace)",
              fontSize: 12,
              padding: "10px 18px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "config" ? "2px solid var(--green)" : "2px solid transparent",
              color: activeTab === "config" ? "var(--green)" : "var(--muted)",
              cursor: "pointer",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              gap: 8,
              whiteSpace: "nowrap",
            }}
          >
            <Settings className="h-3.5 w-3.5" /> Integration & Guardrails
          </button>
        </div>

        {/* Tab 1: Scans Feed */}
        {activeTab === "scans" && (
          <div>
            {scans.length === 0 ? (
              <div
                style={{
                  border: "1px dashed var(--border)",
                  padding: 48,
                  textAlign: "center",
                  background: "var(--card)",
                }}
              >
                <Shield className="h-8 w-8 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16, marginBottom: 8 }}>
                  No security scans executed yet
                </h3>
                <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)", marginBottom: 20 }}>
                  Trigger an autonomous scan to analyze this repository with Semgrep and our 4-agent security pipeline.
                </p>
                <button
                  onClick={handleTriggerScan}
                  disabled={triggering}
                  style={{
                    fontFamily: "var(--font-share-tech-mono, monospace)",
                    fontSize: 11,
                    padding: "8px 22px",
                    background: "var(--green)",
                    color: "#050709",
                    border: "none",
                    cursor: "pointer",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                  }}
                >
                  ▶ Dispatch Initial Scan
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {scans.map((scan) => {
                  const active = isActiveScan(scan.status as ScanStatus);
                  return (
                    <div
                      key={scan.id}
                      onClick={() => router.push(`/scans/${scan.id}`)}
                      style={{
                        border: "1px solid var(--border)",
                        background: "var(--card)",
                        padding: "16px 20px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 16,
                        transition: "border-color 0.2s, background 0.2s",
                      }}
                      onMouseEnter={(e) => {
                        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--green)";
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)";
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                        <div style={{ flexShrink: 0 }}>
                          <AgentAvatar
                            agent={scan.current_agent as "finder" | "exploiter" | "engineer" | "verifier" | null}
                            size="md"
                            showRing={active}
                            showLabel={false}
                          />
                        </div>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                            <span style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 14 }}>
                              Scan #{scan.id}
                            </span>
                            <M style={{ fontSize: 11, color: "var(--blue)" }}>
                              [{scan.branch}]
                            </M>
                            <M style={{ fontSize: 11, color: "var(--muted)" }}>
                              commit: {scan.commit_sha.slice(0, 8)}
                            </M>
                          </div>
                          <div style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)" }}>
                            {scan.agent_message || (scan.vulnerability_type ? `${scan.vulnerability_type} in ${scan.vulnerable_file}` : "Scan initialized")}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                        {scan.severity && <SevBadge severity={scan.severity} />}
                        <StatusBadge status={scan.status} />
                        {active && <LiveTimer startTime={scan.created_at} isActive={true} />}
                        <M style={{ fontSize: 11, color: "var(--muted)" }}>
                          {new Date(scan.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </M>
                        <span style={{ color: "var(--muted)", fontSize: 14 }}>→</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Aggregated Findings */}
        {activeTab === "vulnerabilities" && (
          <div>
            {allFindings.length === 0 ? (
              <div style={{ border: "1px dashed var(--border)", padding: 48, textAlign: "center", background: "var(--card)" }}>
                <CheckCircle2 className="h-8 w-8 mx-auto mb-4 text-emerald-400 opacity-60" />
                <h3 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16, marginBottom: 8 }}>
                  Zero active vulnerabilities
                </h3>
                <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)" }}>
                  No security flaws detected across previous scans for this repository.
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {allFindings.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => router.push(`/scans/${item.scanId}`)}
                    style={{
                      border: "1px solid var(--border)",
                      background: "var(--card)",
                      padding: "16px 20px",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      transition: "border-color 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLDivElement).style.borderColor = "var(--green)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)";
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <SevBadge severity={item.finding.severity} />
                        <span style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 14 }}>
                          {item.finding.vuln_type}
                        </span>
                      </div>
                      <M style={{ fontSize: 11, color: "var(--muted)" }}>
                        From Scan #{item.scanId} ↗
                      </M>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, color: "var(--muted)" }}>
                      <span style={{ display: "flex", alignItems: "center", gap: 4, fontFamily: "var(--font-share-tech-mono, monospace)" }}>
                        <FileCode2 className="h-3.5 w-3.5 text-muted-foreground" />
                        <code style={{ color: "var(--green)" }}>
                          {item.finding.file}:{item.finding.line_start}
                        </code>
                      </span>
                      <span>•</span>
                      <M style={{ fontSize: 11 }}>Confidence: {item.finding.confidence}</M>
                    </div>

                    <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)", margin: 0 }}>
                      {item.finding.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Integration & Guardrails */}
        {activeTab === "config" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
            {/* GitHub App & Webhook */}
            <div style={{ border: "1px solid var(--border)", background: "var(--card)", padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <Terminal className="h-4 w-4 text-emerald-400" />
                <h3 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 15, margin: 0 }}>
                  GitHub App Webhook
                </h3>
              </div>
              <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
                Active webhook endpoint receiving GitHub events for this repository with SHA-256 HMAC verification.
              </p>
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", padding: "10px 14px", marginBottom: 14 }}>
                <M style={{ fontSize: 10, color: "var(--muted)", display: "block", marginBottom: 4 }}>ENDPOINT URL</M>
                <code style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--green)", wordBreak: "break-all" }}>
                  https://aegis-wpeu.onrender.com/api/v1/github/webhook
                </code>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <M style={{ color: "var(--muted)" }}>Trigger Events</M>
                  <M style={{ color: "var(--foreground)" }}>push, pull_request</M>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <M style={{ color: "var(--muted)" }}>Signature Auth</M>
                  <M style={{ color: "var(--green)" }}>HMAC SHA-256 Validated</M>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <M style={{ color: "var(--muted)" }}>Installation Status</M>
                  <M style={{ color: "var(--green)" }}>Installed & Linked</M>
                </div>
              </div>
            </div>

            {/* Autonomous Remediation Policy */}
            <div style={{ border: "1px solid var(--border)", background: "var(--card)", padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <Lock className="h-4 w-4 text-amber-400" />
                <h3 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 15, margin: 0 }}>
                  Safety Guardrails & Policy
                </h3>
              </div>
              <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
                Deterministic enforcement gates preventing unauthorized code modifications.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ padding: "12px 14px", background: "var(--surface)", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 600, fontSize: 13 }}>Human Approval Gate</span>
                    <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--amber)", background: "var(--amber-dim)", padding: "2px 6px" }}>ACTIVE</span>
                  </div>
                  <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)", margin: 0 }}>
                    Critical and High severity exploits require interactive human authorization before GitHub PR dispatch.
                  </p>
                </div>
                <div style={{ padding: "12px 14px", background: "var(--surface)", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 600, fontSize: 13 }}>Docker Sandbox Verification</span>
                    <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--green)", background: "var(--green-dim)", padding: "2px 6px" }}>ENFORCED</span>
                  </div>
                  <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)", margin: 0 }}>
                    Isolated Docker sandbox executes exploit proof before and after patch application to guarantee 0 regressions.
                  </p>
                </div>
              </div>
            </div>

            {/* Target Repository Specs */}
            <div style={{ border: "1px solid var(--border)", background: "var(--card)", padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <GitBranch className="h-4 w-4 text-sky-400" />
                <h3 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 15, margin: 0 }}>
                  Repository Metadata
                </h3>
              </div>
              <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
                Monitored branch targets and AST indexing status.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
                  <M style={{ color: "var(--muted)" }}>Repository ID</M>
                  <M style={{ color: "var(--foreground)" }}>#{repo.id}</M>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
                  <M style={{ color: "var(--muted)" }}>Monitored Branch</M>
                  <M style={{ color: "var(--blue)" }}>main</M>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
                  <M style={{ color: "var(--muted)" }}>AST Semantic Index</M>
                  <M style={{ color: "var(--green)" }}>Synced</M>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <M style={{ color: "var(--muted)" }}>Connected Since</M>
                  <M style={{ color: "var(--muted)" }}>{new Date(repo.created_at).toLocaleDateString()}</M>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
