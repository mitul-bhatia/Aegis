"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type RepoInfo, type ScanInfo } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Shield,
  Plus,
  GitBranch,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Trash2,
  Activity,
  FolderGit2,
  Search,
  LogOut,
} from "lucide-react";

import { VulnCard } from "@/components/VulnCard";
import { AddRepoModal } from "@/components/AddRepoModal";
import { SchedulerControl } from "@/components/SchedulerControl";

// ── Status Badge Component ───────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; icon: React.ElementType }> = {
    queued: { label: "Queued", variant: "secondary", icon: Loader2 },
    scanning: { label: "Scanning", variant: "outline", icon: Search },
    exploiting: { label: "Exploiting", variant: "outline", icon: AlertTriangle },
    exploit_confirmed: { label: "Exploit Found", variant: "destructive", icon: AlertTriangle },
    patching: { label: "Patching", variant: "outline", icon: Activity },
    verifying: { label: "Verifying", variant: "outline", icon: CheckCircle2 },
    fixed: { label: "Fixed", variant: "default", icon: CheckCircle2 },
    false_positive: { label: "False Positive", variant: "secondary", icon: XCircle },
    clean: { label: "Clean", variant: "default", icon: CheckCircle2 },
    failed: { label: "Failed", variant: "destructive", icon: XCircle },
    setting_up: { label: "Setting up", variant: "outline", icon: Loader2 },
    monitoring: { label: "Monitoring", variant: "default", icon: Shield },
    error: { label: "Error", variant: "destructive", icon: XCircle },
  };

  const c = config[status] || { label: status, variant: "secondary" as const, icon: Activity };
  const Icon = c.icon;

  return (
    <Badge variant={c.variant} className="gap-1.5">
      <Icon className={`h-3 w-3 ${status === "scanning" || status === "queued" || status === "setting_up" ? "animate-spin" : ""}`} />
      {c.label}
    </Badge>
  );
}

// ── Repo Card Component ──────────────────────────────────
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

  async function handleTriggerScan() {
    setTriggering(true);
    try {
      await onTriggerScan(repo.id);
    } finally {
      setTriggering(false);
    }
  }

  return (
    <Card className="aegis-card-hover border-border/50">
      <CardContent className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <FolderGit2 className="h-5 w-5 text-muted-foreground" />
          <div>
              <Link href={`/repos/${repo.id}`}>
                <p className="font-semibold text-sm underline text-primary">{repo.full_name}</p>
              </Link>
            <p className="text-xs text-muted-foreground">
              Added {new Date(repo.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={repo.status} />
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5"
            onClick={handleTriggerScan}
            disabled={triggering}
          >
            {triggering ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Activity className="h-3 w-3" />
            )}
            Scan
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={() => onDelete(repo.id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Scan Card Component ──────────────────────────────────
function ScanCard({ scan }: { scan: ScanInfo }) {
  const router = useRouter();

  return (
    <Card
      className="aegis-card-hover border-border/50 cursor-pointer"
      role="link"
      tabIndex={0}
      onClick={() => router.push(`/scans/${scan.id}`)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          router.push(`/scans/${scan.id}`);
        }
      }}
    >
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-muted-foreground" />
                <code className="text-xs text-muted-foreground">
                  {scan.commit_sha.slice(0, 8)}
                </code>
                <span className="text-xs text-muted-foreground">on</span>
                <code className="text-xs text-primary">{scan.branch}</code>
              </div>
              {scan.vulnerability_type && (
                <p className="text-sm font-medium">
                  {scan.vulnerability_type}
                  {scan.vulnerable_file && (
                    <span className="ml-2 text-muted-foreground font-normal">
                      in {scan.vulnerable_file}
                    </span>
                  )}
                </p>
              )}
              {scan.exploit_output && (
                <pre className="mt-2 max-h-24 overflow-auto rounded bg-secondary/50 p-2 text-xs text-muted-foreground">
                  {scan.exploit_output.slice(0, 300)}
                </pre>
              )}
            </div>
            <div className="flex flex-col items-end gap-2">
              <StatusBadge status={scan.status} />
              {scan.pr_url && (
                <a
                  href={scan.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  View PR <ExternalLink className="h-3 w-3" />
                </a>
              )}
              <span className="text-xs text-muted-foreground">
                {new Date(scan.created_at).toLocaleTimeString()}
              </span>
            </div>
          </div>
        </CardContent>
    </Card>
  );
}

// ── Main Dashboard ───────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [scans, setScans] = useState<ScanInfo[]>([]);
  const [username, setUsername] = useState("");
  const [userId, setUserId] = useState(0);
  const [sessionReady, setSessionReady] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUserId(Number(localStorage.getItem("aegis_user_id")));
    setUsername(localStorage.getItem("aegis_username") || "");
    setSessionReady(true);
  }, []);

  const fetchData = useCallback(async () => {
    if (!userId) return;
    try {
      const [repoData, scanData] = await Promise.all([
        api.listRepos(userId),
        api.listScans(),
      ]);
      setRepos(repoData);
      setScans(scanData);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    }
  }, [userId]);

  useEffect(() => {
    if (!sessionReady) return;
    if (!userId) {
      router.push("/");
      return;
    }
    fetchData().finally(() => setLoading(false));

    // Connect to live feed with real-time scan updates
    const es = api.connectLiveFeed((scanData) => {
      console.log("SSE received scan update:", scanData.id, scanData.status);
      // Update scans in real-time without full re-fetch
      setScans((prevScans) => {
        const existingIndex = prevScans.findIndex((s) => s.id === scanData.id);
        if (existingIndex >= 0) {
          // Update existing scan
          const updated = [...prevScans];
          updated[existingIndex] = scanData;
          console.log("Updated existing scan", scanData.id);
          return updated;
        } else {
          // Add new scan at the beginning
          console.log("Added new scan", scanData.id);
          return [scanData, ...prevScans];
        }
      });
    });

    // Poll every 5s as fallback (more frequent for better UX)
    const interval = setInterval(fetchData, 5000);

    return () => {
      es.close();
      clearInterval(interval);
    };
  }, [sessionReady, userId, router, fetchData]);

  async function handleAddRepo(url: string) {
    await api.addRepo(userId, url);
    await fetchData();
  }

  async function handleDeleteRepo(repoId: number) {
    await api.deleteRepo(repoId);
    await fetchData();
  }

  async function handleTriggerScan(repoId: number) {
    try {
      const response = await fetch(`http://localhost:8000/api/scans/trigger?repo_id=${repoId}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to trigger scan");
      }
      const data = await response.json();
      console.log("Scan triggered:", data);
      // Refresh data to show new scan
      setTimeout(() => fetchData(), 2000);
    } catch (error) {
      console.error("Error triggering scan:", error);
    }
  }

  function handleLogout() {
    localStorage.removeItem("aegis_user_id");
    localStorage.removeItem("aegis_username");
    localStorage.removeItem("aegis_avatar");
    router.push("/");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold">Aegis</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{username}</span>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-1.5">
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        {/* Repos section */}
        <div className="mb-10">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">Monitored Repositories</h2>
              <p className="text-sm text-muted-foreground">
                {repos.length} {repos.length === 1 ? "repo" : "repos"} connected
              </p>
            </div>
            <AddRepoModal userId={userId} onSuccess={fetchData} />
          </div>

          {repos.length === 0 ? (
            <Card className="border-dashed border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FolderGit2 className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-muted-foreground">No repos monitored yet</p>
                <p className="text-sm text-muted-foreground/70">
                  Click &quot;Monitor Repo&quot; to get started
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {repos.map((repo) => (
                <RepoCard key={repo.id} repo={repo} onDelete={handleDeleteRepo} onTriggerScan={handleTriggerScan} />
              ))}
            </div>
          )}
        </div>

        {/* Scheduler Control */}
        <div className="mb-6">
          <SchedulerControl />
        </div>

        {/* Scans feed */}
        <div>
          <div className="mb-4">
            <h2 className="text-xl font-bold">Scan Feed</h2>
            <p className="text-sm text-muted-foreground">
              Live vulnerability scan results
            </p>
          </div>

          {scans.length === 0 ? (
            <Card className="border-dashed border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Activity className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-muted-foreground">No scans yet</p>
                <p className="text-sm text-muted-foreground/70">
                  Scans appear here when you push code to a monitored repo
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {scans.map((scan) => (
                <VulnCard key={scan.id} scan={scan} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
