const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "https://aegis-backend-kiw7.onrender.com";
// All API calls go through /api/v1/ for versioning
// In the browser, use relative path /api/v1 (proxied by Next.js rewrites) or absolute URL as fallback.
const API_V1 =
  typeof window !== "undefined"
    ? "/api/v1"
    : `${API_BASE}/api/v1`;

/**
 * Build request options with credentials and fallback Authorization headers from localStorage.
 * Guarantees auth works even if modern browsers block 3rd-party cross-site cookies.
 */
function getOpts(customOpts: RequestInit = {}): RequestInit {
  const headers: Record<string, string> = {
    ...(customOpts.headers as Record<string, string> || {}),
  };

  if (typeof window !== "undefined") {
    const userId = localStorage.getItem("aegis_user_id");
    if (userId) {
      headers["Authorization"] = `Bearer ${userId}`;
      headers["X-Aegis-User-Id"] = userId;
    }
  }

  return {
    credentials: "include",
    ...customOpts,
    headers,
  };
}

export const api = {
  // ── Auth ──────────────────────────────────────────────

  /** Exchange GitHub OAuth code for a session. Backend sets httpOnly cookie. */
  async exchangeGitHubCode(code: string) {
    const redirectUri = `${window.location.origin}/auth/callback`;
    
    // Render free instances spin down after inactivity. Vercel will return 504 Gateway Timeout
    // if Render takes >10s to wake up. We'll retry up to 5 times (50 seconds total).
    let retries = 5;
    let res;
    
    while (retries > 0) {
      res = await fetch(`${API_V1}/auth/github`, getOpts({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, redirect_uri: redirectUri }),
      }));
      
      if (res.ok) break; // Success
      
      // If it's a 502 Bad Gateway or 504 Gateway Timeout (Render waking up)
      if (res.status === 502 || res.status === 504) {
        retries--;
        if (retries === 0) throw new Error("Backend took too long to wake up. Please try again.");
        console.log(`Backend is waking up... retrying in 10s. (${retries} retries left)`);
        await new Promise(r => setTimeout(r, 10000));
        continue;
      }
      
      // For any other error (400, 401, etc.), try to parse the error message
      const text = await res.text().catch(() => "");
      try {
        const err = JSON.parse(text);
        throw new Error(err.detail || "OAuth failed");
      } catch (e) {
        // If it's HTML/text and not JSON, it's likely a 500 error
        throw new Error(text.slice(0, 100) || "OAuth failed");
      }
    }
    
    if (!res) throw new Error("OAuth failed");

    const user = await res.json() as UserInfo;
    if (typeof window !== "undefined" && user?.id) {
      localStorage.setItem("aegis_user_id", String(user.id));
      localStorage.setItem("aegis_username", user.github_username);
      localStorage.setItem("aegis_avatar", user.github_avatar_url);
    }
    return user;
  },

  /** Demo Mode login when OAuth Client ID is not configured. */
  async loginDemo() {
    const res = await fetch(`${API_V1}/auth/demo`, getOpts({ method: "POST" })).catch(() => null);
    if (res && res.ok) {
      const user = await res.json() as UserInfo;
      if (typeof window !== "undefined" && user?.id) {
        localStorage.setItem("aegis_user_id", String(user.id));
        localStorage.setItem("aegis_username", user.github_username);
        localStorage.setItem("aegis_avatar", user.github_avatar_url);
      }
      return user;
    }
    const fallbackUser: UserInfo = {
      id: 1,
      github_id: 999999,
      github_username: "demo-user",
      github_avatar_url: "https://avatars.githubusercontent.com/u/999999?v=4",
    };
    if (typeof window !== "undefined") {
      localStorage.setItem("aegis_user_id", "1");
      localStorage.setItem("aegis_username", "demo-user");
      localStorage.setItem("aegis_avatar", fallbackUser.github_avatar_url);
    }
    return fallbackUser;
  },

  /**
   * Read the session cookie / headers and return the current user.
   * Call this on every page load to check if the user is logged in.
   * Returns null if not authenticated (401).
   */
  async getMe(): Promise<UserInfo | null> {
    try {
      const res = await fetch(`${API_V1}/auth/me`, getOpts());
      if (res.ok) {
        const user = await res.json() as UserInfo;
        if (typeof window !== "undefined" && user?.id) {
          localStorage.setItem("aegis_user_id", String(user.id));
          localStorage.setItem("aegis_username", user.github_username);
          localStorage.setItem("aegis_avatar", user.github_avatar_url);
        }
        return user;
      }
    } catch (e) {
      console.warn("getMe failed:", e);
    }

    // Unauthenticated — clear any stale cached session from localStorage
    if (typeof window !== "undefined") {
      localStorage.removeItem("aegis_user_id");
      localStorage.removeItem("aegis_username");
      localStorage.removeItem("aegis_avatar");
    }
    return null;
  },

  /** Clear the session cookie and localStorage. */
  async logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("aegis_user_id");
      localStorage.removeItem("aegis_username");
      localStorage.removeItem("aegis_avatar");
      sessionStorage.clear();
    }
    await fetch(`${API_V1}/auth/logout`, getOpts({ method: "POST" })).catch(() => null);
  },


  /** Get user by ID (kept for backwards compat). */
  async getUser(userId: number) {
    const res = await fetch(`${API_V1}/auth/user/${userId}`, getOpts());
    if (!res.ok) throw new Error("User not found");
    return res.json() as Promise<UserInfo>;
  },

  // ── Repos ─────────────────────────────────────────────

  async addRepo(userId: number, repoUrl: string) {
    const res = await fetch(`${API_V1}/repos`, getOpts({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, repo_url: repoUrl }),
    }));
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to add repo");
    }
    return res.json();
  },

  async seedDemoRepo(userId: number) {
    const res = await fetch(`${API_V1}/repos/seed-demo`, getOpts({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    }));
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to seed demo repo");
    }
    return res.json();
  },


  async listRepos(userId: number, page = 1, perPage = 20): Promise<PaginatedResponse<RepoInfo>> {
    const params = new URLSearchParams({ user_id: String(userId), page: String(page), per_page: String(perPage) });
    const res = await fetch(`${API_V1}/repos?${params}`, getOpts());
    return res.json();
  },

  async getRepo(repoId: number) {
    const res = await fetch(`${API_V1}/repos/${repoId}`, getOpts());
    if (!res.ok) throw new Error("Repo not found");
    return res.json();
  },

  async deleteRepo(repoId: number) {
    const res = await fetch(`${API_V1}/repos/${repoId}`, getOpts({
      method: "DELETE",
    }));
    return res.json();
  },

  // ── Scans ─────────────────────────────────────────────

  async listScans(repoId?: number, page = 1, perPage = 20): Promise<PaginatedResponse<ScanInfo>> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (repoId) params.set("repo_id", String(repoId));
    const res = await fetch(`${API_V1}/scans?${params}`, getOpts());
    return res.json();
  },

  async getScan(scanId: number) {
    const res = await fetch(`${API_V1}/scans/${scanId}`, getOpts());
    if (!res.ok) throw new Error("Scan not found");
    return res.json();
  },

  async approveScan(scanId: number) {
    const res = await fetch(`${API_V1}/scans/${scanId}/approve`, getOpts({
      method: "POST",
    }));
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to approve scan");
    }
    return res.json();
  },

  async rejectScan(scanId: number, reason: string = "") {
    const res = await fetch(`${API_V1}/scans/${scanId}/reject?reason=${encodeURIComponent(reason)}`, getOpts({
      method: "POST",
    }));
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
      getOpts({ method: "POST" })
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Failed to trigger scan");
    }
    return res.json();
  },

  // ── Stats ─────────────────────────────────────────────

  async getStats(userId: number): Promise<StatsInfo> {
    const res = await fetch(`${API_V1}/stats?user_id=${userId}`, getOpts());
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  // ── Intelligence ──────────────────────────────────────

  async getRepoIntelligence(repoId: number): Promise<RepoIntelligence> {
    const res = await fetch(`${API_V1}/intelligence/repo/${repoId}`, getOpts());
    if (!res.ok) throw new Error("Failed to fetch repo intelligence");
    return res.json();
  },

  async getGlobalThreat(): Promise<GlobalThreat> {
    const res = await fetch(`${API_V1}/intelligence/global`, getOpts());
    if (!res.ok) throw new Error("Failed to fetch global threat");
    return res.json();
  },

  async getAnalytics(userId: number, days = 30): Promise<AnalyticsData> {
    const res = await fetch(`${API_V1}/intelligence/analytics?user_id=${userId}&days=${days}`, getOpts());
    if (!res.ok) throw new Error("Failed to fetch analytics");
    return res.json() as Promise<AnalyticsData>;
  },

  async getScorecard(repoId: number): Promise<ScorecardData> {
    const res = await fetch(`${API_V1}/intelligence/scorecard/${repoId}`, getOpts());
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
