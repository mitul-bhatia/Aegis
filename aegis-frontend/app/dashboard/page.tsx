"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  type RepoInfo,
  type ScanInfo,
  type ScanStatus,
  type StatsInfo,
  isActiveScan,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/StatCard";
import { AgentAvatar } from "@/components/AgentAvatar";
import { LiveTimer } from "@/components/LiveTimer";
import { AddRepoModal } from "@/components/AddRepoModal";
import {
  Shield,
  GitBranch,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Trash2,
  Activity,
  FolderGit2,
  Zap,
  Clock,
  LogOut,
  Plus,
} from "lucide-react";

// ── Status Badge ─────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    queued:            { label: "Queued",         cls: "bg-white/5 text-muted-foreground border-white/10" },
    scanning:          { label: "Scanning",        cls: "bg-violet-500/15 text-violet-400 border-violet-500/30" },
    exploiting:        { label: "Exploiting",      cls: "bg-red-500/15 text-red-400 border-red-500/30" },
    exploit_confirmed: { label: "Exploit Found",   cls: "bg-red-500/20 text-red-300 border-red-500/40 font-bold" },
    patching:          { label: "Patching",        cls: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
    verifying:         { label: "Verifying",       cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
    fixed:             { label: "Fixed ✓",        cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
    false_positive:    { label: "False Positive",  cls: "bg-amber-500/10 text-amber-500 border-amber-500/20" },
    clean:             { label: "Clean ✓",        cls: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" },
    failed:            { label: "Failed",          cls: "bg-red-500/10 text-red-400 border-red-500/20" },
    setting_up:        { label: "Setting Up",      cls: "bg-white/5 text-muted-foreground border-white/10" },
    monitoring:        { label: "Monitoring",      cls: "bg-primary/10 text-primary border-primary/20" },
    error:             { label: "Error",           cls: "bg-red-500/10 text-red-400 border-red-500/20" },
  };
  const c = map[status] ?? { label: status, cls: "bg-white/5 text-muted-foreground border-white/10" };
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${c.cls}`}>
      {c.label}
    </span>
  );
}

// ── Repo Card ─────────────────────────────────────────────
function RepoCard({
  repo,
  onDelete,
  onTriggerScan,
}: {
  repo: RepoInfo;
  onDelete: (id: number) => void;
  onTriggerScan: (id: number) => void;
}) {
  const [triggering, setTriggering] = useState(false);

  const borderColor =
    repo.status === "monitoring" ? "border-l-emerald-500/60"
    : repo.status === "setting_up" ? "border-l-amber-500/60"
    : repo.status === "error" ? "border-l-red-500/60"
    : "border-l-white/10";

  async function handleTrigger() {
    setTriggering(true);
    try { await onTriggerScan(repo.id); }
    finally { setTimeout(() => setTriggering(false), 2000); }
  }

  return (
    <div className={`aegis-glass aegis-card-hover rounded-xl border-l-4 ${borderColor} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <FolderGit2 className="h-4 w-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <Link href={`/repos/${repo.id}`}>
              <p className="font-semibold text-sm text-foreground truncate hover:text-primary transition-colors">
                {repo.full_name}
              </p>
            </Link>
            <p className="text-xs text-muted-foreground">
              Added {new Date(repo.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={repo.status} />
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1.5 text-xs border-white/10 hover:border-primary/50 hover:text-primary"
            onClick={handleTrigger}
            disabled={triggering}
          >
            {triggering ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Activity className="h-3 w-3" />
            )}
            {triggering ? "Starting..." : "Scan"}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-red-400"
            onClick={() => onDelete(repo.id)}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Scan Feed Card ────────────────────────────────────────
function ScanFeedCard({ scan }: { scan: ScanInfo }) {
  const router = useRouter();
  const active = isActiveScan(scan.status as ScanStatus);
  const agent = scan.current_agent as "finder" | "exploiter" | "engineer" | "verifier" | null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/scans/${scan.id}`)}
      onKeyDown={(e) => { if (e.key === "Enter") router.push(`/scans/${scan.id}`); }}
      className={`group relative rounded-xl border p-4 cursor-pointer transition-all duration-300 ${
        active
          ? "aegis-active-scan bg-card/80"
          : "border-border/40 bg-card/40 hover:border-border/70 hover:bg-card/60"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Agent avatar or status icon */}
        <div className="shrink-0 mt-0.5">
          {active && agent ? (
            <AgentAvatar agent={agent} size="sm" showRing={true} />
          ) : scan.status === "fixed" || scan.status === "clean" ? (
            <div className="h-7 w-7 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            </div>
          ) : scan.status === "failed" ? (
            <div className="h-7 w-7 rounded-full bg-red-500/15 border border-red-500/30 flex items-center justify-center">
              <XCircle className="h-3.5 w-3.5 text-red-400" />
            </div>
          ) : scan.status === "false_positive" ? (
            <div className="h-7 w-7 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            </div>
          ) : (
            <div className="h-7 w-7 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
              <Activity className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-1">
          {/* Commit + branch */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <code className="text-xs text-muted-foreground font-mono">{scan.commit_sha.slice(0, 8)}</code>
            <span className="text-xs text-muted-foreground">on</span>
            <code className="text-xs text-primary font-mono">{scan.branch}</code>
          </div>

          {/* Agent message or vulnerability */}
          {active && scan.agent_message ? (
            <p className="text-xs text-foreground/80 leading-relaxed">{scan.agent_message}</p>
          ) : scan.vulnerability_type ? (
            <p className="text-xs font-medium text-foreground">
              {scan.vulnerability_type}
              {scan.vulnerable_file && (
                <span className="ml-1.5 text-muted-foreground font-normal">
                  in <code className="text-primary">{scan.vulnerable_file}</code>
                </span>
              )}
            </p>
          ) : null}
        </div>

        {/* Right side */}
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <StatusBadge status={scan.status} />
          {active ? (
            <LiveTimer startTime={scan.created_at} isActive={true} />
          ) : (
            <span className="text-xs text-muted-foreground">
              {new Date(scan.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
          {scan.pr_url && (
            <a
              href={scan.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 text-xs text-emerald-400 hover:underline"
            >
              View PR <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────
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

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUserId(Number(localStorage.getItem("aegis_user_id")));
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUsername(localStorage.getItem("aegis_username") || "");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAvatarUrl(localStorage.getItem("aegis_avatar") || "");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessionReady(true);
  }, []);

  const fetchData = useCallback(async () => {
    if (!userId) return;
    try {
      const [repoData, scanData, statsData] = await Promise.all([
        api.listRepos(userId),
        api.listScans(),
        api.getStats(userId).catch(() => null),
      ]);
      setRepos(repoData);
      setScans(scanData);
      if (statsData) setStats(statsData);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    }
  }, [userId]);

  useEffect(() => {
    if (!sessionReady) return;
    if (!userId) { router.push("/"); return; }

    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData().finally(() => setLoading(false));

    // SSE live feed — merge updates to preserve full scan data
    const es = api.connectLiveFeed((scanData) => {
      setScans((prev) => {
        const idx = prev.findIndex((s) => s.id === scanData.id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = { ...updated[idx], ...scanData };
          return updated;
        }
        return [scanData, ...prev];
      });
    });

    // Refresh stats every 10s
    const interval = setInterval(fetchData, 10000);

    return () => { es.close(); clearInterval(interval); };
  }, [sessionReady, userId, router, fetchData]);

  async function handleDeleteRepo(repoId: number) {
    await api.deleteRepo(repoId);
    await fetchData();
  }

  async function handleTriggerScan(repoId: number) {
    try {
      await api.triggerScan(repoId);
      setTimeout(() => fetchData(), 2000);
    } catch (err) {
      console.error("Error triggering scan:", err);
    }
  }

  function handleLogout() {
    localStorage.removeItem("aegis_user_id");
    localStorage.removeItem("aegis_username");
    localStorage.removeItem("aegis_avatar");
    router.push("/");
  }

  // Sort: active scans first
  const sortedScans = [...scans].sort((a, b) => {
    const aActive = isActiveScan(a.status as ScanStatus) ? 1 : 0;
    const bActive = isActiveScan(b.status as ScanStatus) ? 1 : 0;
    return bActive - aActive;
  });

  const activeCount = scans.filter((s) => isActiveScan(s.status as ScanStatus)).length;

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

  return (
    <div className="min-h-screen">
      {/* ── Header ── */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2.5">
            <Shield className="h-6 w-6 text-primary" strokeWidth={1.8} />
            <span className="text-lg font-bold tracking-tight">Aegis</span>
            {activeCount > 0 && (
              <span className="flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-xs text-primary">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
                </span>
                {activeCount} active
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {avatarUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={avatarUrl} alt={username} className="h-7 w-7 rounded-full border border-border/50" />
            )}
            <span className="text-sm text-muted-foreground">{username}</span>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-1.5 text-muted-foreground">
              <LogOut className="h-4 w-4" /> Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">

        {/* ── Stats Row ── */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            icon={GitBranch}
            label="Repos Monitored"
            value={stats?.total_repos ?? repos.length}
            accentClass="text-primary"
          />
          <StatCard
            icon={Zap}
            label="Active Scans"
            value={stats?.active_scans ?? activeCount}
            subLabel={stats?.active_scans ? "in progress" : "all idle"}
            accentClass="text-amber-400"
            isActive={(stats?.active_scans ?? activeCount) > 0}
          />
          <StatCard
            icon={Shield}
            label="Vulnerabilities Fixed"
            value={stats?.vulns_fixed ?? 0}
            accentClass="text-emerald-400"
          />
          <StatCard
            icon={Clock}
            label="Last Scan"
            value={
              stats?.last_scan_at
                ? (() => {
                    // eslint-disable-next-line react-hooks/purity
                    const diff = Date.now() - new Date(stats.last_scan_at).getTime();
                    const mins = Math.floor(diff / 60000);
                    if (mins < 1) return "Just now";
                    if (mins < 60) return `${mins}m ago`;
                    return `${Math.floor(mins / 60)}h ago`;
                  })()
                : "Never"
            }
            accentClass="text-muted-foreground"
          />
        </div>

        {/* ── Two-column grid ── */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">

          {/* ── Left: Repos ── */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold">Monitored Repos</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {repos.length} {repos.length === 1 ? "repository" : "repositories"} connected
                </p>
              </div>
              <AddRepoModal userId={userId} onSuccess={fetchData} forceOpen={openAddRepo} onForceOpenHandled={() => setOpenAddRepo(false)} />
            </div>

            {repos.length === 0 ? (
              <div
                className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/50 py-12 cursor-pointer hover:border-primary/30 hover:bg-primary/5 transition-colors"
                onClick={() => setOpenAddRepo(true)}
              >
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Plus className="h-5 w-5 text-primary" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium">No repos yet</p>
                  <p className="text-xs text-muted-foreground">Click &quot;Monitor Repo&quot; to get started</p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {repos.map((repo) => (
                  <RepoCard
                    key={repo.id}
                    repo={repo}
                    onDelete={handleDeleteRepo}
                    onTriggerScan={handleTriggerScan}
                  />
                ))}
              </div>
            )}
          </div>

          {/* ── Right: Live Scan Feed ── */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-bold">Live Activity</h2>
                  {activeCount > 0 && (
                    <span className="flex h-2 w-2">
                      <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-primary opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Real-time vulnerability scan results
                </p>
              </div>
            </div>

            {sortedScans.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/50 py-16">
                <Activity className="h-8 w-8 text-muted-foreground/30" />
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">No scans yet</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">
                    Push code to a monitored repo or click &quot;Scan&quot; to trigger one
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {sortedScans.map((scan) => (
                  <ScanFeedCard key={scan.id} scan={scan} />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
