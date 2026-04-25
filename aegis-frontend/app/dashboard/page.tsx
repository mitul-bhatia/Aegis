"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type RepoInfo, type ScanInfo, type ScanStatus, type StatsInfo, isActiveScan } from "@/lib/api";
import { AddRepoModal } from "@/components/AddRepoModal";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AgentAvatar } from "@/components/AgentAvatar";
import { LiveTimer } from "@/components/LiveTimer";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { NotificationPermissionBanner, NotificationToggle, notifyScanComplete } from "@/components/NotificationManager";

// ── Helpers ───────────────────────────────────────────────
function mono(text: string, style?: React.CSSProperties) {
  return <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", ...style }}>{text}</span>;
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
    setting_up:        { label: "Setting Up",      color: "var(--muted)",          bg: "rgba(255,255,255,0.04)" },
    error:             { label: "Error",           color: "var(--red)",            bg: "var(--red-dim)" },
    regression:        { label: "Regression",      color: "var(--red)",            bg: "var(--red-dim)" },
  };
  const c = map[status] ?? { label: status, color: "var(--muted)", bg: "rgba(255,255,255,0.04)" };
  return (
    <span style={{
      fontFamily: "var(--font-share-tech-mono, monospace)",
      fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase",
      padding: "2px 8px", background: c.bg, color: c.color, whiteSpace: "nowrap",
    }}>
      {c.label}
    </span>
  );
}

function StatCell({ value, label, bg, color = "var(--green)" }: { value: string | number; label: string; bg: string; color?: string }) {
  return (
    <div style={{ background: "var(--surface)", padding: "32px 24px", position: "relative", overflow: "hidden", flex: 1 }}>
      <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 800, fontSize: 44, lineHeight: 1, marginBottom: 6 }}>
        <span style={{ color }}>{value}</span>
      </div>
      <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase" }}>
        {label}
      </span>
      <div style={{ position: "absolute", right: -6, top: -6, fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 80, color: "rgba(255,255,255,0.025)", lineHeight: 1, pointerEvents: "none" }}>
        {bg}
      </div>
    </div>
  );
}

function RepoCard({ repo, onDelete, onTriggerScan }: { repo: RepoInfo; onDelete: (id: number) => void; onTriggerScan: (id: number) => void }) {
  const [triggering, setTriggering] = useState(false);
  const isMonitoring = repo.status === "monitoring";
  const borderHover = isMonitoring ? "var(--agent-verifier)" : "var(--red)";

  return (
    <div style={{ border: "1px solid var(--border)", background: "var(--card)", padding: "14px 16px", transition: "border-color 0.2s" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = borderHover)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <Link href={`/repos/${repo.id}`} style={{ textDecoration: "none" }}>
            <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 600, fontSize: 14, color: "var(--foreground)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {repo.full_name}
            </div>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <StatusBadge status={repo.status} />
            <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--muted)" }}>
              Added {new Date(repo.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
          <button onClick={async () => { setTriggering(true); try { await onTriggerScan(repo.id); } finally { setTimeout(() => setTriggering(false), 2000); } }}
            disabled={triggering}
            style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, padding: "5px 12px", border: "1px solid var(--border)", background: "transparent", color: triggering ? "var(--muted)" : "var(--blue)", cursor: "pointer", letterSpacing: "0.08em", textTransform: "uppercase", transition: "border-color 0.2s" }}>
            {triggering ? "Starting..." : "▶ Scan"}
          </button>
          <button onClick={() => onDelete(repo.id)} title="Remove"
            style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, padding: "5px 10px", border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", cursor: "pointer", transition: "color 0.2s, border-color 0.2s" }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "var(--red)"; (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--red)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "var(--muted)"; (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)"; }}>
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}

function ScanFeedCard({ scan }: { scan: ScanInfo }) {
  const router = useRouter();
  const active = isActiveScan(scan.status as ScanStatus);
  const agent = scan.current_agent as "finder" | "exploiter" | "engineer" | "verifier" | null;

  return (
    <div role="button" tabIndex={0} onClick={() => router.push(`/scans/${scan.id}`)}
      onKeyDown={(e) => { if (e.key === "Enter") router.push(`/scans/${scan.id}`); }}
      className={active ? "aegis-active-scan" : ""}
      style={{
        border: "1px solid var(--border)", background: "var(--card)",
        padding: "12px 14px", cursor: "pointer", transition: "border-color 0.2s, background 0.2s",
        display: "flex", alignItems: "flex-start", gap: 12,
      }}
      onMouseEnter={(e) => { if (!active) { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--muted)"; (e.currentTarget as HTMLDivElement).style.background = "#161E27"; } }}
      onMouseLeave={(e) => { if (!active) { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLDivElement).style.background = "var(--card)"; } }}>
      {/* Avatar */}
      <div style={{ flexShrink: 0, marginTop: 2 }}>
        {active && agent
          ? <AgentAvatar agent={agent} size="sm" showRing={true} />
          : <div style={{ width: 28, height: 28, borderRadius: "50%", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "var(--muted)" }}>
              {scan.status === "fixed" || scan.status === "clean" ? "✓" : scan.status === "failed" ? "✕" : "○"}
            </div>}
      </div>
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
          <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)" }}>{scan.commit_sha.slice(0, 8)}</span>
          <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)" }}>on</span>
          <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--blue)" }}>{scan.branch}</span>
        </div>
        <div style={{ fontSize: 13, color: "var(--foreground)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {active && scan.agent_message ? scan.agent_message
            : scan.vulnerability_type ? `${scan.vulnerability_type}${scan.vulnerable_file ? ` · ${scan.vulnerable_file}` : ""}` : "No vulnerability detected"}
        </div>
      </div>
      {/* Right */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
        <StatusBadge status={scan.status} />
        {active ? <LiveTimer startTime={scan.created_at} isActive={true} />
          : <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--muted)" }}>
              {new Date(scan.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>}
        {scan.pr_url && (
          <a href={scan.pr_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
            style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--agent-verifier)", textDecoration: "none" }}>
            View PR ↗
          </a>
        )}
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [scans, setScans] = useState<ScanInfo[]>([]);
  const [stats, setStats] = useState<StatsInfo | null>(null);
  const [userId, setUserId] = useState(0);
  const [username, setUsername] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [sessionReady, setSessionReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [openAddRepo, setOpenAddRepo] = useState(false);
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    api.getMe().then((user) => {
      if (user) {
        setUserId(user.id);
        localStorage.setItem("aegis_user_id", String(user.id));
        setUsername(localStorage.getItem("aegis_username") || user.github_username);
        setAvatarUrl(localStorage.getItem("aegis_avatar") || user.github_avatar_url);
      } else {
        const cachedId = localStorage.getItem("aegis_user_id");
        if (cachedId) { setUserId(parseInt(cachedId, 10)); setUsername(localStorage.getItem("aegis_username") || ""); setAvatarUrl(localStorage.getItem("aegis_avatar") || ""); }
      }
      setSessionReady(true);
    });
  }, []);

  const fetchData = useCallback(async () => {
    if (!userId) return;
    try {
      const [repoData, scanData, statsData] = await Promise.all([api.listRepos(userId), api.listScans(), api.getStats(userId).catch(() => null)]);
      setRepos(repoData.data ?? repoData);
      setScans(scanData.data ?? scanData);
      if (statsData) setStats(statsData);
    } catch (err) { console.error(err); }
  }, [userId]);

  useEffect(() => {
    if (!sessionReady) return;
    if (!userId) { router.push("/"); return; }
    fetchData().finally(() => setLoading(false));
    const es = api.connectLiveFeed((scanData) => {
      setScans((prev) => {
        const idx = prev.findIndex((s) => s.id === scanData.id);
        if (idx >= 0) { const u = [...prev]; u[idx] = { ...u[idx], ...scanData }; return u; }
        return [scanData, ...prev];
      });
      if (["fixed", "failed", "clean", "awaiting_approval"].includes(scanData.status)) notifyScanComplete(scanData);
    });
    const interval = setInterval(fetchData, 10000);
    return () => { es.close(); clearInterval(interval); };
  }, [sessionReady, userId, router, fetchData]);

  const activeCount = scans.filter((s) => isActiveScan(s.status as ScanStatus)).length;
  const sortedScans = [...scans].sort((a, b) => (isActiveScan(b.status as ScanStatus) ? 1 : 0) - (isActiveScan(a.status as ScanStatus) ? 1 : 0));
  const filteredScans = sortedScans.filter((s) => {
    if (filterStatus !== "all" && s.status !== filterStatus) return false;
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      return s.vulnerability_type?.toLowerCase().includes(q) || s.vulnerable_file?.toLowerCase().includes(q) || s.commit_sha.toLowerCase().includes(q);
    }
    return true;
  });

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: 16 }}>
      <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 800, fontSize: 24 }}>AE<span style={{ color: "var(--green)" }}>G</span>IS</div>
      <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)", letterSpacing: "0.15em", animation: "pulse 2s infinite" }}>// LOADING MISSION CONTROL...</span>
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", background: "var(--background)" }}>
      <NotificationPermissionBanner />

      {/* ── Header ── */}
      <header className="aegis-glass-nav" style={{ position: "sticky", top: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 800, fontSize: 18, letterSpacing: "0.06em" }}>
            AE<span style={{ color: "var(--green)" }}>G</span>IS
          </div>
          {activeCount > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 10px", border: "1px solid var(--green-dim)", background: "var(--green-dim)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", animation: "pulse 2s infinite", display: "inline-block" }} />
              <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--green)", letterSpacing: "0.1em", textTransform: "uppercase" }}>{activeCount} active</span>
            </div>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {avatarUrl && <img src={avatarUrl} alt={username} style={{ width: 28, height: 28, borderRadius: "50%", border: "1px solid var(--border)" }} />}
          <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)" }}>{username}</span>
          <ThemeToggle />
          <NotificationToggle />
          <Link href="/analytics">
            <button style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, padding: "6px 14px", border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", cursor: "pointer", letterSpacing: "0.08em", textTransform: "uppercase" }}>Analytics</button>
          </Link>
          <button onClick={async () => { await api.logout(); localStorage.removeItem("aegis_username"); localStorage.removeItem("aegis_avatar"); router.push("/"); }}
            style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, padding: "6px 14px", border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", cursor: "pointer", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Sign Out
          </button>
        </div>
      </header>

      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 32px" }}>

        {/* ── Stats Row ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, background: "var(--border)", border: "1px solid var(--border)", marginBottom: 24 }}>
          <StatCell value={stats?.total_repos ?? repos.length}  label="Repos Monitored"      bg="⬡" color="var(--blue)" />
          <StatCell value={stats?.active_scans ?? activeCount}  label="Active Scans"         bg="⚡" color={activeCount > 0 ? "var(--amber)" : "var(--muted)"} />
          <StatCell value={stats?.vulns_fixed ?? 0}             label="Vulnerabilities Fixed" bg="✓" color="var(--agent-verifier)" />
          <StatCell value={stats?.total_scans ?? scans.length}  label="Total Scans"           bg="#" color="var(--muted)" />
        </div>

        {/* ── Two-Column Layout ── */}
        <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 1, background: "var(--border)", border: "1px solid var(--border)", minHeight: 500 }}>

          {/* Left: Repos */}
          <div style={{ background: "var(--surface)", padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
              <div>
                <h2 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16, marginBottom: 2 }}>Monitored Repos</h2>
                <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--muted)", letterSpacing: "0.1em" }}>
                  {repos.length} {repos.length === 1 ? "repository" : "repositories"} connected
                </span>
              </div>
              <AddRepoModal userId={userId} onSuccess={fetchData} forceOpen={openAddRepo} onForceOpenHandled={() => setOpenAddRepo(false)} />
            </div>
            <ErrorBoundary fallbackTitle="Repos list failed to render">
              {repos.length === 0 ? (
                <div onClick={() => setOpenAddRepo(true)} style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, border: "1px dashed var(--border)", padding: 40, cursor: "pointer", transition: "border-color 0.2s" }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--green)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}>
                  <div style={{ width: 40, height: 40, border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, color: "var(--muted)" }}>+</div>
                  <div style={{ textAlign: "center" }}>
                    <p style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 600, fontSize: 14, marginBottom: 4 }}>No repos yet</p>
                    <p style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)" }}>Click "Monitor Repo" to get started</p>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {repos.map((repo) => (
                    <RepoCard key={repo.id} repo={repo} onDelete={async (id) => { await api.deleteRepo(id); await fetchData(); }} onTriggerScan={async (id) => { try { await api.triggerScan(id); setTimeout(fetchData, 2000); } catch (e) { console.error(e); } }} />
                  ))}
                </div>
              )}
            </ErrorBoundary>
          </div>

          {/* Right: Live Scan Feed */}
          <div style={{ background: "var(--surface)", padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                  <h2 style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 700, fontSize: 16 }}>Live Activity</h2>
                  {activeCount > 0 && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", animation: "pulse 2s infinite", display: "inline-block" }} />}
                </div>
                <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--muted)", letterSpacing: "0.1em" }}>Real-time vulnerability scan results</span>
              </div>
            </div>

            {/* Filter bar */}
            {scans.length > 0 && (
              <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
                <input type="text" placeholder="Search vulnerability, file, commit..." value={searchText} onChange={(e) => setSearchText(e.target.value)}
                  style={{ flex: 1, minWidth: 200, padding: "6px 10px", border: "1px solid var(--border)", background: "var(--card)", color: "var(--foreground)", fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, outline: "none" }} />
                <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ padding: "6px 10px" }}>
                  <option value="all">All Statuses</option>
                  <option value="fixed">Fixed</option>
                  <option value="failed">Failed</option>
                  <option value="scanning">Scanning</option>
                  <option value="exploiting">Exploiting</option>
                  <option value="patching">Patching</option>
                  <option value="clean">Clean</option>
                </select>
                {(filterStatus !== "all" || searchText.trim()) && (
                  <button onClick={() => { setFilterStatus("all"); setSearchText(""); }}
                    style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, padding: "6px 12px", border: "1px solid var(--border)", background: "transparent", color: "var(--muted)", cursor: "pointer", letterSpacing: "0.08em" }}>
                    Clear ✕
                  </button>
                )}
                <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 10, color: "var(--muted)", marginLeft: "auto" }}>{filteredScans.length} scans</span>
              </div>
            )}

            <ErrorBoundary fallbackTitle="Scan feed failed to render">
              {filteredScans.length === 0 ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, border: "1px dashed var(--border)", padding: 60 }}>
                  <span style={{ fontFamily: "var(--font-share-tech-mono, monospace)", fontSize: 11, color: "var(--muted)" }}>
                    {scans.length === 0 ? "// No scans yet — push code or trigger manually" : "// No matching scans"}
                  </span>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {filteredScans.map((scan) => <ScanFeedCard key={scan.id} scan={scan} />)}
                </div>
              )}
            </ErrorBoundary>
          </div>
        </div>
      </main>
    </div>
  );
}
