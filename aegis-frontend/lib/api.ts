const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// All API calls go through /api/v1/ for versioning
// In the browser, use a relative path so requests proxy through Next.js (avoids CORS).
// On the server (SSR), use the full backend URL.
const API_V1 =
  typeof window !== "undefined"
    ? "/api/v1"
    : `${API_BASE}/api/v1`;

// All fetch calls include credentials: "include" so the browser sends
// the httpOnly session cookie automatically with every request.
const OPTS: RequestInit = { credentials: "include" };

export const api = {
  // ── Auth ──────────────────────────────────────────────

  /** Exchange GitHub OAuth code for a session. Backend sets httpOnly cookie. */
  async exchangeGitHubCode(code: string) {
    const redirectUri = `${window.location.origin}/auth/callback`;
    const res = await fetch(`${API_V1}/auth/github`, {
      ...OPTS,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "OAuth failed");
    }
    return res.json() as Promise<UserInfo>;
  },

  /**
   * Read the session cookie and return the current user.
   * Call this on every page load to check if the user is logged in.
   * Returns null if not authenticated (401).
   */
  async getMe(): Promise<UserInfo | null> {
    const res = await fetch(`${API_V1}/auth/me`, OPTS);
    if (res.status === 401) return null;
    if (!res.ok) return null;
    return res.json() as Promise<UserInfo>;
  },

  /** Clear the session cookie on the backend. */
  async logout() {
    await fetch(`${API_V1}/auth/logout`, { ...OPTS, method: "POST" });
  },

  /** Get user by ID (kept for backwards compat). */
  async getUser(userId: number) {
    const res = await fetch(`${API_V1}/auth/user/${userId}`, OPTS);
    if (!res.ok) throw new Error("User not found");
    return res.json() as Promise<UserInfo>;
  },

  // ── Repos ─────────────────────────────────────────────

  async addRepo(userId: number, repoUrl: string) {
    const res = await fetch(`${API_V1}/repos`, {
      ...OPTS,
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

  async listRepos(userId: number, page = 1, perPage = 20): Promise<PaginatedResponse<RepoInfo>> {
    const params = new URLSearchParams({ user_id: String(userId), page: String(page), per_page: String(perPage) });
    const res = await fetch(`${API_V1}/repos?${params}`, OPTS);
    return res.json();
  },

  async getRepo(repoId: number) {
    const res = await fetch(`${API_V1}/repos/${repoId}`, OPTS);
    if (!res.ok) throw new Error("Repo not found");
    return res.json();
  },

  async deleteRepo(repoId: number) {
    const res = await fetch(`${API_V1}/repos/${repoId}`, {
      ...OPTS,
      method: "DELETE",
    });
    return res.json();
  },

  // ── Scans ─────────────────────────────────────────────

  async listScans(repoId?: number, page = 1, perPage = 20): Promise<PaginatedResponse<ScanInfo>> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (repoId) params.set("repo_id", String(repoId));
    const res = await fetch(`${API_V1}/scans?${params}`, OPTS);
    return res.json();
  },

  async getScan(scanId: number) {
    const res = await fetch(`${API_V1}/scans/${scanId}`, OPTS);
    if (!res.ok) throw new Error("Scan not found");
    return res.json();
  },

  async approveScan(scanId: number) {
    const res = await fetch(`${API_V1}/scans/${scanId}/approve`, {
      ...OPTS,
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to approve scan");
    }
    return res.json();
  },

  async rejectScan(scanId: number, reason: string = "") {
    const res = await fetch(`${API_V1}/scans/${scanId}/reject?reason=${encodeURIComponent(reason)}`, {
      ...OPTS,
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to reject scan");
    }
    return res.json();
  },

  async triggerScan(repoId: number): Promise<TriggerResult> {
    // Use the last known commit so we don't need a blocking GitHub API call
    const result = await api.listScans(repoId).catch(() => ({ data: [] as ScanInfo[], pagination: null }));
    const scans = result.data;

    const lastCommit = scans[0]?.commit_sha ?? "HEAD";
    const lastBranch = scans[0]?.branch ?? "main";

    const res = await fetch(
      `${API_V1}/scans/trigger-direct?repo_id=${repoId}&commit_sha=${lastCommit}&branch=${lastBranch}`,
      { ...OPTS, method: "POST" }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Failed to trigger scan");
    }
    return res.json();
  },

  // ── Stats ─────────────────────────────────────────────

  async getStats(userId: number): Promise<StatsInfo> {
    const res = await fetch(`${API_V1}/stats?user_id=${userId}`, OPTS);
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  // ── Intelligence ──────────────────────────────────────

  async getRepoIntelligence(repoId: number): Promise<RepoIntelligence> {
    const res = await fetch(`${API_V1}/intelligence/repo/${repoId}`, OPTS);
    if (!res.ok) throw new Error("Failed to fetch repo intelligence");
    return res.json();
  },

  async getGlobalThreat(): Promise<GlobalThreat> {
    const res = await fetch(`${API_V1}/intelligence/global`, OPTS);
    if (!res.ok) throw new Error("Failed to fetch global threat");
    return res.json();
  },

  async getAnalytics(userId: number, days = 30): Promise<AnalyticsData> {
    const res = await fetch(`${API_V1}/intelligence/analytics?user_id=${userId}&days=${days}`, OPTS);
    if (!res.ok) throw new Error("Failed to fetch analytics");
    return res.json() as Promise<AnalyticsData>;
  },

  async getScorecard(repoId: number): Promise<ScorecardData> {
    const res = await fetch(`${API_V1}/intelligence/scorecard/${repoId}`, OPTS);
    if (!res.ok) throw new Error("Failed to fetch scorecard");
    return res.json() as Promise<ScorecardData>;
  },

  // ── SSE ───────────────────────────────────────────────

  /**
   * Open a Server-Sent Events connection for live scan updates.
   * EventSource doesn't support custom headers, but it does send cookies
   * automatically — so the session cookie works here too.
   */
  connectLiveFeed(onMessage: (data: ScanInfo) => void): { close: () => void } {
    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      // withCredentials=true sends the session cookie with the SSE request
      es = new EventSource(`${API_V1}/scans/live`, { withCredentials: true });

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ScanInfo;
          onMessage(data);
        } catch (err) {
          console.error("SSE parse error:", err);
        }
      };

      es.onerror = () => {
        es?.close();
        // Reconnect after 3 seconds on error
        retryTimeout = setTimeout(connect, 3000);
      };
    }

    connect();

    return {
      close: () => {
        clearTimeout(retryTimeout);
        es?.close();
      },
    };
  },
};

// ── Types ──────────────────────────────────────────────────

/** Generic paginated response wrapper returned by list endpoints. */
export type PaginatedResponse<T> = {
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
};

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
  original_code?: string | null;
  exploit_script?: string | null;
  findings_json?: string | null;
  current_agent?: AgentKey | null;
  agent_message?: string | null;
  patch_attempts?: number;
  is_regression?: boolean;
};

export type ScanStatus =
  | "queued"
  | "scanning"
  | "exploiting"
  | "exploit_confirmed"
  | "patching"
  | "verifying"
  | "awaiting_approval"
  | "fixed"
  | "false_positive"
  | "clean"
  | "failed"
  | "regression";

export type AgentKey = "finder" | "exploiter" | "engineer" | "verifier" | "safety_validator" | "approval_gate";

export const ACTIVE_STATUSES: ScanStatus[] = [
  "queued",
  "scanning",
  "exploiting",
  "exploit_confirmed",
  "patching",
  "verifying",
  "awaiting_approval",
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

export type AnalyticsData = {
  vuln_trend: { date: string; found: number; fixed: number }[];
  top_vulns: { type: string; count: number }[];
  severity_dist: Record<string, number>;
  mttr_hours: number;
  fix_rate: number;
  total_scans: number;
  total_vulns_found: number;
  total_fixed: number;
  regressions: number;
  period_days: number;
};

export type ScorecardDimension = {
  score: number;
  label: string;
  weight: number;
};

export type ScorecardData = {
  repo_id: number;
  repo_name: string;
  grade: string;
  score: number | null;
  dimensions: Record<string, ScorecardDimension>;
  open_vulns: number;
  mttr_hours: number;
  fix_rate: number;
  total_scans: number;
  message?: string;
};

export function parseFindingsJson(raw: string | null | undefined): FindingInfo[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as FindingInfo[]) : [];
  } catch {
    return [];
  }
}
