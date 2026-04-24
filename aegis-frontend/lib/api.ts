const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  // ── Auth ──────────────────────────────────────────────
  async exchangeGitHubCode(code: string) {
    const res = await fetch(`${API_BASE}/api/auth/github`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) throw new Error("OAuth failed");
    return res.json();
  },

  async getUser(userId: number) {
    const res = await fetch(`${API_BASE}/api/auth/user/${userId}`);
    if (!res.ok) throw new Error("User not found");
    return res.json();
  },

  // ── Repos ─────────────────────────────────────────────
  async addRepo(userId: number, repoUrl: string) {
    const res = await fetch(`${API_BASE}/api/repos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, repo_url: repoUrl }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to add repo");
    }
    return res.json();
  },

  async listRepos(userId: number) {
    const res = await fetch(`${API_BASE}/api/repos?user_id=${userId}`);
    return res.json();
  },

  async getRepo(repoId: number) {
    const res = await fetch(`${API_BASE}/api/repos/${repoId}`);
    if (!res.ok) throw new Error("Repo not found");
    return res.json();
  },

  async deleteRepo(repoId: number) {
    const res = await fetch(`${API_BASE}/api/repos/${repoId}`, {
      method: "DELETE",
    });
    return res.json();
  },

  // ── Scans ─────────────────────────────────────────────
  async listScans(repoId?: number) {
    const url = repoId
      ? `${API_BASE}/api/scans?repo_id=${repoId}`
      : `${API_BASE}/api/scans`;
    const res = await fetch(url);
    return res.json();
  },

  async getScan(scanId: number) {
    const res = await fetch(`${API_BASE}/api/scans/${scanId}`);
    if (!res.ok) throw new Error("Scan not found");
    return res.json();
  },

  async triggerScan(repoId: number): Promise<TriggerResult> {
    // Use trigger-direct with the last known commit from the repo's scan history
    // This avoids blocking GitHub API calls
    const scans: ScanInfo[] = await fetch(`${API_BASE}/api/scans?repo_id=${repoId}`)
      .then(r => r.json()).catch(() => []);
    const lastCommit = scans[0]?.commit_sha ?? "HEAD";
    const lastBranch = scans[0]?.branch ?? "main";

    const res = await fetch(
      `${API_BASE}/api/scans/trigger-direct?repo_id=${repoId}&commit_sha=${lastCommit}&branch=${lastBranch}`,
      { method: "POST" }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Failed to trigger scan");
    }
    return res.json();
  },

  // ── Stats ─────────────────────────────────────────────
  async getStats(userId: number): Promise<StatsInfo> {
    const res = await fetch(`${API_BASE}/api/stats?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  // ── Intelligence ──────────────────────────────────────
  async getRepoIntelligence(repoId: number): Promise<RepoIntelligence> {
    const res = await fetch(`${API_BASE}/api/intelligence/repo/${repoId}`);
    if (!res.ok) throw new Error("Failed to fetch repo intelligence");
    return res.json();
  },

  async getGlobalThreat(): Promise<GlobalThreat> {
    const res = await fetch(`${API_BASE}/api/intelligence/global`);
    if (!res.ok) throw new Error("Failed to fetch global threat");
    return res.json();
  },

  async getSchedulerInsights(): Promise<SchedulerInsights> {
    const res = await fetch(`${API_BASE}/api/intelligence/scheduler/insights`);
    if (!res.ok) throw new Error("Failed to fetch scheduler insights");
    return res.json();
  },

  // ── SSE ───────────────────────────────────────────────
  connectLiveFeed(onMessage: (data: ScanInfo) => void): { close: () => void } {
    let es: EventSource | null = null;
    let retryTimeout: NodeJS.Timeout;

    function connect() {
      es = new EventSource(`${API_BASE}/api/scans/live`);
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ScanInfo;
          onMessage(data);
        } catch (err) {
          console.error("SSE parse error:", err);
        }
      };
      es.onerror = (err) => {
        console.error("SSE connection error, reconnecting in 3s...", err);
        if (es) {
          es.close();
        }
        retryTimeout = setTimeout(connect, 3000);
      };
    }
    
    connect();

    return {
      close: () => {
        clearTimeout(retryTimeout);
        if (es) {
          es.close();
        }
      }
    };
  },
};

// ── Types ──────────────────────────────────────────────────

export type UserInfo = {
  id: number;
  github_id: number;
  github_username: string;
  github_avatar_url: string;
};

export type RepoInfo = {
  id: number;
  full_name: string;
  webhook_id: number | null;
  is_indexed: boolean;
  status: string;
  created_at: string;
  html_url?: string;
};

export type ScanInfo = {
  id: number;
  repo_id: number;
  commit_sha: string;
  branch: string;
  status: ScanStatus;
  vulnerability_type: string | null;
  severity: string | null;
  pr_url: string | null;
  created_at: string;
  completed_at?: string | null;
  vulnerable_file?: string | null;
  exploit_output?: string | null;
  patch_diff?: string | null;
  error_message?: string | null;
  // Agent-identity fields (new)
  original_code?: string | null;
  exploit_script?: string | null;
  findings_json?: string | null;
  current_agent?: AgentKey | null;
  agent_message?: string | null;
  patch_attempts?: number;
};

export type ScanStatus =
  | "queued"
  | "scanning"
  | "exploiting"
  | "exploit_confirmed"
  | "patching"
  | "verifying"
  | "fixed"
  | "false_positive"
  | "clean"
  | "failed";

export type AgentKey = "finder" | "exploiter" | "engineer" | "verifier";

export const ACTIVE_STATUSES: ScanStatus[] = [
  "queued",
  "scanning",
  "exploiting",
  "exploit_confirmed",
  "patching",
  "verifying",
];

export const TERMINAL_STATUSES: ScanStatus[] = [
  "fixed",
  "false_positive",
  "clean",
  "failed",
];

export function isActiveScan(status: ScanStatus): boolean {
  return ACTIVE_STATUSES.includes(status);
}

export type StatsInfo = {
  total_repos: number;
  active_scans: number;
  vulns_fixed: number;
  total_scans: number;
  false_positives: number;
  last_scan_at: string | null;
};

export type TriggerResult = {
  message: string;
  repo: string;
  commit: string;
  files: string[];
};

// ── Intelligence Types ─────────────────────────────────────

export type FindingInfo = {
  file: string;
  line_start: number;
  vuln_type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  relevant_code: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
};

export type RepoIntelligence = {
  repo_id: number;
  repo_name: string;
  threat_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  critical_threats: number;
  high_threats: number;
  medium_threats: number;
  predicted_risk: number;
  vulnerability_density: number;
  activity_score: number;
  business_impact: number;
  adaptive_interval_hours: number;
  last_scan: string | null;
  next_scan_in_minutes: number | null;
};

export type GlobalThreat = {
  level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  emergency_repos: string[];
  total_threats: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
};

export type MLPrediction = {
  repo_id: number;
  repo_name: string;
  risk_score: number;
  confidence: number;
  factors: string[];
};

export type MLPredictions = {
  high_risk_repos: MLPrediction[];
  accuracy: number;
  total_predictions: number;
  false_positives: number;
  false_negatives: number;
};

export type SchedulerInsights = {
  total_scans: number;
  repo_patterns: number;
  avg_scan_duration: number;
  threat_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  scans_today: number;
  vulnerabilities_found_today: number;
  vulnerabilities_fixed_today: number;
};

/** Parse findings_json string from a scan into typed array */
export function parseFindingsJson(raw: string | null | undefined): FindingInfo[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as FindingInfo[]) : [];
  } catch {
    return [];
  }
}
