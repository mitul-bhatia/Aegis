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
} from "lucide-react";
import { api } from "@/lib/api";

type ProgressState = "idle" | "validating" | "webhook" | "indexing" | "complete" | "error";

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
  const [url, setUrl] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (forceOpen) {
      setOpen(true);
      onForceOpenHandled?.();
    }
  }, [forceOpen, onForceOpenHandled]);
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
      await new Promise((resolve) => setTimeout(resolve, 400));

      // Step 2: Installing webhook + saving repo
      setState("webhook");
      const result = await api.addRepo(userId, url);
      setRepoId(result.id);

      // Step 3: Indexing — show progress while background RAG indexing runs.
      // The polling useEffect above will auto-transition to "complete" once indexed.
      setState("indexing");

      // Safety timeout: if indexing takes >30s, close the modal anyway.
      // The indexing continues in the background and the dashboard shows "Setting Up".
      setTimeout(() => {
        setState((prev) => {
          if (prev === "indexing") {
            setTimeout(() => {
              setOpen(false);
              onSuccess();
              setState("idle");
              setUrl("");
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
      if (state === "validating" || state === "webhook" || state === "indexing") {
        return; // Prevent closing while processing
      }
      setOpen(false);
      setState("idle");
      setUrl("");
      setError("");
      setRepoId(null);
    } else {
      setOpen(true);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger>
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
