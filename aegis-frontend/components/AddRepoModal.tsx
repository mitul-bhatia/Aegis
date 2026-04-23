"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Plus,
  Loader2,
  CheckCircle2,
  GitBranch,
  Webhook,
  Database,
} from "lucide-react";
import { api } from "@/lib/api";

type ProgressState = "idle" | "validating" | "webhook" | "indexing" | "complete" | "error";

export function AddRepoModal({
  userId,
  onSuccess,
}: {
  userId: number;
  onSuccess: () => void;
}) {
  const [url, setUrl] = useState("");
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<ProgressState>("idle");
  const [error, setError] = useState("");
  const [repoId, setRepoId] = useState<number | null>(null);

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
            // Reset state
            setState("idle");
            setUrl("");
            setRepoId(null);
          }, 1500);
        }
      } catch (err) {
        console.error("Failed to check repo status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [state, repoId, onSuccess]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    try {
      // Step 1: Validating
      setState("validating");
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Step 2: Installing webhook
      setState("webhook");
      const result = await api.addRepo(userId, url);
      setRepoId(result.id);

      // Step 3: Indexing (will poll until complete)
      setState("indexing");
    } catch (err: unknown) {
      setState("error");
      setError(err instanceof Error ? err.message : "Failed to add repo");
    }
  }

  function handleClose() {
    if (state === "validating" || state === "webhook" || state === "indexing") {
      // Don't allow closing during progress
      return;
    }
    setOpen(false);
    setState("idle");
    setUrl("");
    setError("");
    setRepoId(null);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button className="gap-2 aegis-glow">
          <Plus className="h-4 w-4" />
          Monitor Repo
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a Repository</DialogTitle>
        </DialogHeader>

        {state === "idle" || state === "error" ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Input
                placeholder="github.com/owner/repo"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={state !== "idle"}
                className="font-mono text-sm"
              />
              <p className="mt-2 text-xs text-muted-foreground">
                Paste any GitHub repo URL. Aegis will install a webhook and start monitoring.
              </p>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={!url}>
              Start Monitoring
            </Button>
          </form>
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
