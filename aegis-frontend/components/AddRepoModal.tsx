"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Loader2, CheckCircle2, RefreshCw } from "lucide-react";
import { api, UserInfo } from "@/lib/api";

type ProgressState =
  | "idle"
  | "fetching"
  | "validating"
  | "webhook"
  | "indexing"
  | "complete"
  | "error";

export function AddRepoModal({
  userId,
  onSuccess,
  forceOpen,
  onForceOpenHandled,
}: {
  userId: number;
  onSuccess: () => void;
  forceOpen?: boolean;
  onForceOpenHandled?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<ProgressState>("idle");
  const [error, setError] = useState("");
  const [repoId, setRepoId] = useState<number | null>(null);
  
  const [user, setUser] = useState<UserInfo | null>(null);
  const [availableRepos, setAvailableRepos] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    if (forceOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setOpen(true);
      onForceOpenHandled?.();
    }
  }, [forceOpen, onForceOpenHandled]);
  
  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open, userId]);

  async function loadData() {
    setState("fetching");
    try {
      const u = await api.getMe();
      setUser(u);
      
      if (u?.github_installation_id) {
        const repos = await api.getAvailableRepos(userId);
        setAvailableRepos(repos.data || []);
      }
      setState("idle");
    } catch (err: unknown) {
      setError("Failed to load user or repositories");
      setState("error");
    }
  }

  // Poll repo status when indexing
  useEffect(() => {
    if (state !== "indexing" || !repoId) return;

    const interval = setInterval(async () => {
      try {
        const repo = await api.getRepo(repoId);
        if (repo.is_indexed) {
          setState("complete");
          clearInterval(interval);
          setTimeout(() => {
            setOpen(false);
            onSuccess();
            setState("idle");
            setRepoId(null);
          }, 1500);
        }
      } catch (err) {
        console.error("Failed to check repo status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [state, repoId, onSuccess]);

  async function handleMonitorRepo(repoUrl: string) {
    setError("");
    try {
      setState("validating");
      await new Promise((resolve) => setTimeout(resolve, 400));

      setState("webhook");
      const result = await api.addRepo(userId, repoUrl);
      setRepoId(result.id);

      setState("indexing");

      setTimeout(() => {
        setState((prev) => {
          if (prev === "indexing") {
            setTimeout(() => {
              setOpen(false);
              onSuccess();
              setState("idle");
              setRepoId(null);
            }, 500);
            return "complete";
          }
          return prev;
        });
      }, 30000);
    } catch (err: unknown) {
      setState("error");
      setError(err instanceof Error ? err.message : "Failed to add repo");
    }
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      if (
        state === "validating" ||
        state === "webhook" ||
        state === "indexing"
      ) {
        return; // Prevent closing while processing
      }
      setOpen(false);
      setState("idle");
      setError("");
      setRepoId(null);
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setOpen(true);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button className="gap-2 aegis-glow">
          <Plus className="h-4 w-4" />
          Monitor Repo
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add a Repository</DialogTitle>
        </DialogHeader>

        {state === "fetching" ? (
          <div className="flex justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : state === "idle" || state === "error" ? (
          <div className="space-y-4">
            {error && (
              <p className="text-sm text-destructive mb-4 text-center">{error}</p>
            )}
            
            {!user?.github_installation_id ? (
              // User has not installed the GitHub App
              <div className="rounded-lg bg-slate-800 p-4 border border-slate-700 text-center">
                <p className="text-sm text-slate-300 mb-4">
                  To monitor a repository, you must install the Aegis GitHub App.
                  This gives Aegis secure access to your code to build the RAG
                  index and scan future commits automatically.
                </p>
                <a
                  href={`https://github.com/apps/${process.env.NEXT_PUBLIC_GITHUB_APP_NAME || "aegis-defensibility-system"}/installations/new`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex w-full items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  📦 Install GitHub App
                </a>
              </div>
            ) : (
              // User HAS installed the GitHub App, show available repos
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <p className="text-sm text-muted-foreground">Select a repository to start monitoring:</p>
                  <Button variant="ghost" size="icon" onClick={loadData}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
                
                {availableRepos.length === 0 ? (
                  <div className="text-center p-4 border rounded-md">
                    <p className="text-sm text-muted-foreground mb-4">No repositories found. Ensure you granted access during installation.</p>
                    <a
                      href={`https://github.com/apps/${process.env.NEXT_PUBLIC_GITHUB_APP_NAME || "aegis-defensibility-system"}/installations/new`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline"
                    >
                      Manage GitHub App Access
                    </a>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {availableRepos.map((repo) => (
                      <div key={repo.id} className="flex items-center justify-between p-3 border rounded-md">
                        <div>
                          <p className="text-sm font-medium">{repo.full_name}</p>
                          <p className="text-xs text-muted-foreground">{repo.private ? "Private" : "Public"}</p>
                        </div>
                        {repo.is_monitored ? (
                          <Button disabled variant="outline" size="sm">Monitored</Button>
                        ) : (
                          <Button size="sm" onClick={() => handleMonitorRepo(repo.full_name)}>Monitor</Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-center pt-2">
                    <a
                      href={`https://github.com/apps/${process.env.NEXT_PUBLIC_GITHUB_APP_NAME || "aegis-defensibility-system"}/installations/new`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      Manage GitHub App Access
                    </a>
                </div>
              </div>
            )}

            {!user?.github_installation_id && (
              <>
                <div className="relative my-4 text-center text-xs text-muted-foreground before:absolute before:inset-0 before:top-1/2 before:border-t before:border-border">
                  <span className="relative bg-background px-2">OR TRY IT OUT</span>
                </div>

                <button
                  type="button"
                  onClick={async () => {
                    try {
                      setState("validating");
                      await api.seedDemoRepo(userId);
                      setState("complete");
                      setTimeout(() => {
                        setOpen(false);
                        onSuccess();
                        setState("idle");
                      }, 1000);
                    } catch (err: unknown) {
                      setState("error");
                      if (err instanceof Error) {
                        setError(err.message || "Failed to seed demo repo");
                      } else {
                        setError("Failed to seed demo repo");
                      }
                    }
                  }}
                  className="inline-flex w-full items-center justify-center rounded-md border border-green-500/30 bg-green-500/10 px-4 py-2 text-sm font-medium text-green-400 hover:bg-green-500/20"
                >
                  ⚡ Load Showcase Repo
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-6 py-4">
            {/* Progress steps */}
            <div className="space-y-4">
              {/* Step 1: Validating */}
              <div className="flex items-center gap-3">
                {state === "validating" ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                )}
                <div>
                  <p className="text-sm font-medium">Validating repository</p>
                  <p className="text-xs text-muted-foreground">
                    Checking GitHub access and permissions
                  </p>
                </div>
              </div>

              {/* Step 2: Installing webhook */}
              <div className="flex items-center gap-3">
                {state === "validating" ? (
                  <div className="h-5 w-5 rounded-full border-2 border-muted" />
                ) : state === "webhook" ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                )}
                <div>
                  <p className="text-sm font-medium">Installing webhook</p>
                  <p className="text-xs text-muted-foreground">
                    Setting up automatic vulnerability scanning
                  </p>
                </div>
              </div>

              {/* Step 3: Indexing codebase */}
              <div className="flex items-center gap-3">
                {state === "validating" || state === "webhook" ? (
                  <div className="h-5 w-5 rounded-full border-2 border-muted" />
                ) : state === "indexing" ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                )}
                <div>
                  <p className="text-sm font-medium">Indexing codebase</p>
                  <p className="text-xs text-muted-foreground">
                    Building semantic code index for AI agents
                  </p>
                </div>
              </div>
            </div>

            {/* Complete message */}
            {state === "complete" && (
              <div className="rounded-lg bg-green-500/10 p-4 text-center border border-green-500/20">
                <CheckCircle2 className="mx-auto h-8 w-8 text-green-500 mb-2" />
                <p className="text-sm font-medium text-green-600">
                  Repository ready for monitoring!
                </p>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
