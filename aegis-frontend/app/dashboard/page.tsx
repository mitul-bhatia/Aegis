"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, RepoInfo, ScanInfo, StatsInfo, ACTIVE_STATUSES } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { VulnCard } from "@/components/VulnCard";
import { StatCard } from "@/components/StatCard";
import { AddRepoModal } from "@/components/AddRepoModal";

export default function Dashboard() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [scans, setScans] = useState<ScanInfo[]>([]);
  const [stats, setStats] = useState<StatsInfo | null>(null);

  const [loading, setLoading] = useState(true);
  const [showAddRepo, setShowAddRepo] = useState(false);

  useEffect(() => {
    if (!user) {
      router.push("/");
      return;
    }

    let sse: { close: () => void } | null = null;
    let isSubscribed = true;

    async function loadData() {
      try {
        const [reposData, scansData, statsData] = await Promise.all([
          api.listRepos(user!.id),
          api.listScans(),
          api.getStats(user!.id)
        ]);

        if (!isSubscribed) return;

        setRepos(reposData);
        setScans(scansData);
        setStats(statsData);
        setLoading(false);

        // Connect live feed
        sse = api.connectLiveFeed((update) => {
          setScans((prev) => {
            const idx = prev.findIndex((s) => s.id === update.id);
            if (idx === -1) {
              return [update, ...prev].slice(0, 50); // keep last 50
            }
            const next = [...prev];
            next[idx] = { ...next[idx], ...update };
            return next;
          });

          // Refresh stats slightly delayed to ensure DB consistency
          setTimeout(() => {
            api.getStats(user!.id).then(setStats).catch(console.error);
          }, 1000);
        });

      } catch (err) {
        console.error("Dashboard load error", err);
      }
    }

    loadData();

    return () => {
      isSubscribed = false;
      if (sse) sse.close();
    };
  }, [user, router]);

  const handleTriggerScan = async (repoId: number) => {
    try {
      await api.triggerScan(repoId);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRepoAdded = () => {
    setShowAddRepo(false);
    if (user) {
      api.listRepos(user.id).then(setRepos);
    }
  };

  const handleRemoveRepo = async (repoId: number) => {
    if (!confirm("Are you sure you want to stop monitoring this repository?")) return;
    try {
      await api.deleteRepo(repoId);
      setRepos(repos.filter(r => r.id !== repoId));
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (!user || loading) return <div className="p-8 text-slate-400 font-mono">Loading...</div>;

  // Split active and recent scans
  const activeScans = scans.filter(s => ACTIVE_STATUSES.includes(s.status));
  const recentScans = scans.filter(s => !ACTIVE_STATUSES.includes(s.status)).slice(0, 10);

  return (
    <div className="min-h-screen bg-[#050810] text-slate-200">
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-[#0a0e17] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-slate-800 flex items-center justify-center font-bold font-mono border border-slate-700">
            A
          </div>
          <span className="font-bold font-mono tracking-tight text-white">Aegis Dashboard</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-400 font-mono">{user.github_username}</span>
          <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-300 font-mono">
            Logout
          </button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard icon="📁" value={stats?.total_repos || 0} label="Monitored Repos" />
          <StatCard icon="⚡" value={stats?.active_scans || 0} label="Active Pipeline Runs" color="#dc2626" pulse={!!(stats && stats.active_scans > 0)} />
          <StatCard icon="🛡️" value={stats?.vulns_fixed || 0} label="Vulnerabilities Patched" color="#059669" />
          <StatCard icon="🔍" value={stats?.total_scans || 0} label="Total Scans" color="#3b82f6" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* Left Column: Repos (40%) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-bold font-mono text-white">Repositories</h2>
              <button onClick={() => setShowAddRepo(true)}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono px-3 py-1.5 rounded transition-colors border border-slate-700">
                + Add Repo
              </button>
            </div>

            {repos.length === 0 ? (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center">
                <p className="text-slate-500 font-mono text-sm mb-4">No repositories monitored.</p>
                <button onClick={() => setShowAddRepo(true)} className="text-violet-400 hover:text-violet-300 font-mono text-sm">
                  Add your first repository →
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {repos.map(repo => (
                  <div key={repo.id} className="bg-slate-900/40 border border-slate-800 rounded-lg p-4 flex items-center justify-between hover:border-slate-700 transition-colors">
                    <div>
                      <h3 className="font-mono font-bold text-sm text-slate-200">{repo.full_name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <div className={`w-2 h-2 rounded-full ${repo.status === "monitoring" ? "bg-emerald-500" : "bg-amber-500"}`} />
                        <span className="text-xs text-slate-500 font-mono capitalize">{repo.status.replace("_", " ")}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => handleTriggerScan(repo.id)} className="text-xs text-slate-400 hover:text-white font-mono px-2 py-1 bg-slate-800 rounded">
                        Scan Now
                      </button>
                      <button onClick={() => handleRemoveRepo(repo.id)} className="text-slate-500 hover:text-red-400 px-2 py-1">
                        ×
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Live Feed (60%) */}
          <div className="lg:col-span-7 space-y-6">

            {/* Active Scans */}
            <div>
              <h2 className="text-lg font-bold font-mono text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                Active Swarm Activity
              </h2>
              {activeScans.length === 0 ? (
                <div className="bg-slate-900/30 border border-slate-800 border-dashed rounded-xl p-6 text-center">
                  <p className="text-slate-500 font-mono text-sm">All clear. No active threats detected.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {activeScans.map(scan => <VulnCard key={scan.id} scan={scan} />)}
                </div>
              )}
            </div>

            {/* Recent History */}
            {recentScans.length > 0 && (
              <div className="pt-4">
                <h2 className="text-sm font-bold font-mono text-slate-500 mb-4 uppercase tracking-wider">
                  Recent History
                </h2>
                <div className="space-y-3">
                  {recentScans.map(scan => <VulnCard key={scan.id} scan={scan} />)}
                </div>
              </div>
            )}

          </div>
        </div>
      </main>

      {showAddRepo && (
        <AddRepoModal
          userId={user.id}
          onClose={() => setShowAddRepo(false)}
          onSuccess={handleRepoAdded}
        />
      )}
    </div>
  );
}
