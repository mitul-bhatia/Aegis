"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type ScanInfo } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Shield,
  ArrowLeft,
  ExternalLink,
  Bug,
  Wrench,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  GitCommit,
  GitBranch,
  FileCode2,
  AlertTriangle,
} from "lucide-react";

function SeverityBadge({ severity }: { severity: string | null }) {
  const colors: Record<string, string> = {
    ERROR: "bg-red-500/15 text-red-400 border-red-500/30",
    WARNING: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    INFO: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  };
  const s = (severity || "INFO").toUpperCase();
  return (
    <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold ${colors[s] || colors.INFO}`}>
      {s}
    </span>
  );
}

function StatusTimeline({ status }: { status: string }) {
  const steps = [
    { key: "scanning", label: "Scanning", icon: Shield },
    { key: "exploiting", label: "Exploiting", icon: Bug },
    { key: "exploit_confirmed", label: "Exploit Confirmed", icon: AlertTriangle },
    { key: "patching", label: "Patching", icon: Wrench },
    { key: "verifying", label: "Verifying", icon: CheckCircle2 },
    { key: "fixed", label: "Fixed", icon: CheckCircle2 },
  ];

  const order = steps.map((s) => s.key);
  const currentIdx = order.indexOf(status);

  // Handle terminal states
  const isFailed = status === "failed";
  const isFalsePositive = status === "false_positive";
  const isClean = status === "clean";

  if (isClean || isFalsePositive) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border/50 bg-card p-4">
        <CheckCircle2 className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium">
          {isClean ? "No vulnerabilities found" : "False positive — exploit failed in sandbox"}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {steps.map((step, idx) => {
        const Icon = step.icon;
        const isDone = currentIdx > idx || status === "fixed";
        const isCurrent = currentIdx === idx && !isFailed;
        const isActive = isDone || isCurrent;

        return (
          <div key={step.key} className="flex items-center gap-2">
            <div className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium border transition-all ${
              isCurrent ? "border-primary bg-primary/10 text-primary status-pulse" :
              isDone ? "border-primary/30 bg-primary/5 text-primary" :
              "border-border/50 bg-secondary/30 text-muted-foreground"
            }`}>
              <Icon className={`h-3 w-3 ${isCurrent ? "animate-pulse" : ""}`} />
              {step.label}
            </div>
            {idx < steps.length - 1 && (
              <div className={`h-px w-4 ${isActive ? "bg-primary/40" : "bg-border/40"}`} />
            )}
          </div>
        );
      })}
      {isFailed && (
        <div className="flex items-center gap-1.5 rounded-full border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs font-medium text-destructive">
          <XCircle className="h-3 w-3" /> Failed
        </div>
      )}
    </div>
  );
}

function CodeBlock({ title, content, language = "text" }: {
  title: string;
  content: string;
  language?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const lines = content.split("\n");
  const preview = lines.slice(0, 8).join("\n");
  const needsExpand = lines.length > 8;

  return (
    <div className="rounded-lg border border-border/50 overflow-hidden">
      <div className="flex items-center justify-between bg-secondary/50 px-4 py-2.5">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          {title}
        </span>
        {needsExpand && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-primary hover:underline"
          >
            {expanded ? "Collapse" : `Show all ${lines.length} lines`}
          </button>
        )}
      </div>
      <pre className="overflow-x-auto p-4 text-xs leading-relaxed text-foreground/90 bg-background/50 font-mono">
        <code>{expanded ? content : preview}{needsExpand && !expanded ? "\n..." : ""}</code>
      </pre>
    </div>
  );
}

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = Number(params.id);
  const [scan, setScan] = useState<ScanInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchScan() {
      try {
        const data = await api.getScan(scanId);
        setScan(data);
      } catch {
        setError("Scan not found");
      } finally {
        setLoading(false);
      }
    }

    fetchScan();

    // Poll if scan is still in progress
    const interval = setInterval(async () => {
      const data = await api.getScan(scanId).catch(() => null);
      if (data) {
        setScan(data);
        const terminal = ["fixed", "failed", "false_positive", "clean"];
        if (terminal.includes(data.status)) clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [scanId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-destructive">{error || "Scan not found"}</p>
          <Link href="/dashboard" className="mt-4 text-sm text-primary underline">
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  const isTerminal = ["fixed", "failed", "false_positive", "clean"].includes(scan.status);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-4xl items-center gap-4 px-6 py-3">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm" className="gap-1.5">
              <ArrowLeft className="h-4 w-4" /> Dashboard
            </Button>
          </Link>
          <Separator orientation="vertical" className="h-5" />
          <Shield className="h-5 w-5 text-primary" />
          <span className="font-semibold">Scan #{scan.id}</span>
          {!isTerminal && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8 space-y-6">
        {/* Overview */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-base">Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Commit</p>
                <div className="flex items-center gap-1.5">
                  <GitCommit className="h-3.5 w-3.5 text-muted-foreground" />
                  <code className="text-sm font-mono">{scan.commit_sha.slice(0, 8)}</code>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Branch</p>
                <div className="flex items-center gap-1.5">
                  <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
                  <code className="text-sm font-mono text-primary">{scan.branch}</code>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Severity</p>
                <SeverityBadge severity={scan.severity} />
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Started</p>
                <div className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-sm">{new Date(scan.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>

            {scan.vulnerability_type && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Vulnerability</p>
                <div className="flex items-center gap-2">
                  <Bug className="h-4 w-4 text-destructive" />
                  <span className="font-semibold">{scan.vulnerability_type}</span>
                  {scan.vulnerable_file && (
                    <>
                      <span className="text-muted-foreground text-sm">in</span>
                      <div className="flex items-center gap-1">
                        <FileCode2 className="h-3.5 w-3.5 text-muted-foreground" />
                        <code className="text-sm text-primary">{scan.vulnerable_file}</code>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Status timeline */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="text-base">Pipeline Status</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusTimeline status={scan.status} />
          </CardContent>
        </Card>

        {/* Exploit Output */}
        {scan.exploit_output && (
          <Card className="border-destructive/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-destructive">
                <Bug className="h-4 w-4" /> Exploit Proof
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CodeBlock
                title="Sandbox Output"
                content={scan.exploit_output}
              />
            </CardContent>
          </Card>
        )}

        {/* Patch Diff */}
        {scan.patch_diff && (
          <Card className="border-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-primary">
                <Wrench className="h-4 w-4" /> Security Patch
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CodeBlock
                title="Patched Code"
                content={scan.patch_diff}
                language="python"
              />
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {scan.error_message && (
          <Card className="border-destructive/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-destructive">
                <XCircle className="h-4 w-4" /> Error
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs text-destructive/80 whitespace-pre-wrap font-mono">
                {scan.error_message}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* PR Link */}
        {scan.pr_url && (
          <Card className="border-primary/20 bg-primary/5 aegis-glow">
            <CardContent className="flex items-center justify-between p-5">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-6 w-6 text-primary" />
                <div>
                  <p className="font-semibold">Vulnerability fixed!</p>
                  <p className="text-sm text-muted-foreground">
                    A PR with the security patch is ready for your review.
                  </p>
                </div>
              </div>
              <Button
                className="aegis-glow"
                render={
                  <a href={scan.pr_url} target="_blank" rel="noopener noreferrer">
                    Review PR <ExternalLink className="ml-2 h-4 w-4" />
                  </a>
                }
              />
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
