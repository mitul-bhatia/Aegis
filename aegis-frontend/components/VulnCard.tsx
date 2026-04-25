"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  GitBranch,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  Code,
  FileCode,
  Loader2,
  XCircle,
  Activity,
  Search,
  Shield,
} from "lucide-react";
import type { ScanInfo } from "@/lib/api";

// ── Status Badge Component ───────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    {
      label: string;
      variant: "default" | "secondary" | "destructive" | "outline";
      icon: React.ElementType;
      className?: string;
    }
  > = {
    queued: {
      label: "Queued",
      variant: "secondary",
      icon: Loader2,
      className: "animate-pulse",
    },
    scanning: {
      label: "Scanning",
      variant: "outline",
      icon: Search,
      className: "animate-pulse",
    },
    exploiting: {
      label: "Exploiting",
      variant: "outline",
      icon: Activity,
      className: "animate-pulse",
    },
    exploit_confirmed: {
      label: "Exploit Found",
      variant: "destructive",
      icon: AlertTriangle,
    },
    patching: {
      label: "Patching",
      variant: "outline",
      icon: Code,
      className: "animate-pulse",
    },
    verifying: {
      label: "Verifying",
      variant: "outline",
      icon: Shield,
      className: "animate-pulse",
    },
    fixed: {
      label: "Fixed",
      variant: "default",
      icon: CheckCircle2,
      className: "bg-green-500/10 text-green-600 border-green-500/20",
    },
    false_positive: {
      label: "False Positive",
      variant: "secondary",
      icon: XCircle,
    },
    clean: {
      label: "Clean",
      variant: "default",
      icon: CheckCircle2,
      className: "bg-green-500/10 text-green-600 border-green-500/20",
    },
    failed: {
      label: "Failed",
      variant: "destructive",
      icon: XCircle,
    },
  };

  const c = config[status] || {
    label: status,
    variant: "secondary" as const,
    icon: Activity,
  };
  const Icon = c.icon;

  return (
    <Badge variant={c.variant} className={`gap-1.5 ${c.className || ""}`}>
      <Icon
        className={`h-3 w-3 ${
          status === "scanning" ||
          status === "queued" ||
          status === "exploiting" ||
          status === "patching" ||
          status === "verifying"
            ? "animate-spin"
            : ""
        }`}
      />
      {c.label}
    </Badge>
  );
}

// ── Severity Badge ───────────────────────────────────────
function SeverityBadge({ severity }: { severity: string | null }) {
  if (!severity) return null;

  const config: Record<
    string,
    { variant: "default" | "secondary" | "destructive" | "outline" }
  > = {
    CRITICAL: { variant: "destructive" },
    HIGH: { variant: "destructive" },
    ERROR: { variant: "destructive" },
    MEDIUM: { variant: "outline" },
    WARNING: { variant: "outline" },
    LOW: { variant: "secondary" },
  };

  const c = config[severity.toUpperCase()] || { variant: "secondary" as const };

  return (
    <Badge variant={c.variant} className="text-xs">
      {severity}
    </Badge>
  );
}

// ── Collapsible Section ──────────────────────────────────
function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = false,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-t border-border/50 pt-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between text-sm font-medium hover:text-primary transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </div>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {isOpen && <div className="mt-3">{children}</div>}
    </div>
  );
}

// ── Main VulnCard Component ──────────────────────────────
export function VulnCard({ scan }: { scan: ScanInfo }) {
  const router = useRouter();

  return (
    <Card className="aegis-card-hover border-border/50">
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            {/* Commit info */}
            <div className="flex items-center gap-2 flex-wrap">
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              <code className="text-xs text-muted-foreground">
                {scan.commit_sha.slice(0, 8)}
              </code>
              <span className="text-xs text-muted-foreground">on</span>
              <code className="text-xs text-primary">{scan.branch}</code>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">
                {new Date(scan.created_at).toLocaleString()}
              </span>
            </div>

            {/* Vulnerability info */}
            {scan.vulnerability_type && (
              <div className="flex items-center gap-2 flex-wrap">
                <AlertTriangle className="h-4 w-4 text-destructive" />
                <span className="text-sm font-semibold">
                  {scan.vulnerability_type}
                </span>
                {scan.severity && <SeverityBadge severity={scan.severity} />}
                {scan.vulnerable_file && (
                  <span className="text-xs text-muted-foreground">
                    in <code className="text-primary">{scan.vulnerable_file}</code>
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Status badge */}
          <div className="flex flex-col items-end gap-2">
            <StatusBadge status={scan.status} />
            {scan.pr_url && (
              <a
                href={scan.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 h-7 text-xs"
                >
                  View PR <ExternalLink className="h-3 w-3" />
                </Button>
              </a>
            )}
          </div>
        </div>

        {/* Collapsible sections */}
        {scan.exploit_output && (
          <CollapsibleSection
            title="Exploit Output"
            icon={AlertTriangle}
            defaultOpen={false}
          >
            <pre className="max-h-48 overflow-auto rounded-lg bg-secondary/50 p-3 text-xs text-muted-foreground font-mono border border-border/50">
              {scan.exploit_output}
            </pre>
          </CollapsibleSection>
        )}

        {scan.patch_diff && (
          <CollapsibleSection
            title="Patch Diff"
            icon={FileCode}
            defaultOpen={false}
          >
            <pre className="max-h-48 overflow-auto rounded-lg bg-secondary/50 p-3 text-xs text-muted-foreground font-mono border border-border/50">
              {scan.patch_diff}
            </pre>
          </CollapsibleSection>
        )}

        {scan.error_message && (
          <CollapsibleSection
            title="Error Details"
            icon={XCircle}
            defaultOpen={true}
          >
            <div className="rounded-lg bg-destructive/10 p-3 text-xs text-destructive border border-destructive/20">
              {scan.error_message}
            </div>
          </CollapsibleSection>
        )}

        {/* View details button */}
        <div className="pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs"
            onClick={() => router.push(`/scans/${scan.id}`)}
          >
            View Full Details
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
