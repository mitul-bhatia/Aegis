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

  // ── SSE ───────────────────────────────────────────────
  connectLiveFeed(onMessage: (data: unknown) => void): EventSource {
    const es = new EventSource(`${API_BASE}/api/scans/live`);
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        // keepalive or malformed, ignore
      }
    };
    return es;
  },
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
};

export type ScanInfo = {
  id: number;
  repo_id: number;
  commit_sha: string;
  branch: string;
  status: string;
  vulnerability_type: string | null;
  severity: string | null;
  pr_url: string | null;
  created_at: string;
  vulnerable_file?: string | null;
  exploit_output?: string | null;
  patch_diff?: string | null;
  error_message?: string | null;
  completed_at?: string | null;
};
