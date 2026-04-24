"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { FindingInfo } from "@/lib/api";
import { ChevronDown, ChevronRight, FileCode2, AlertTriangle } from "lucide-react";

const SEVERITY_CONFIG: Record<string, { cls: string; dot: string }> = {
  CRITICAL: { cls: "text-red-400 border-red-500/40 bg-red-500/10",   dot: "bg-red-500" },
  HIGH:     { cls: "text-red-400 border-red-500/30 bg-red-500/8",    dot: "bg-red-400" },
  MEDIUM:   { cls: "text-amber-400 border-amber-500/30 bg-amber-500/8", dot: "bg-amber-400" },
  LOW:      { cls: "text-blue-400 border-blue-500/30 bg-blue-500/8",  dot: "bg-blue-400" },
};

const CONFIDENCE_CONFIG: Record<string, string> = {
  HIGH:   "text-emerald-400",
  MEDIUM: "text-amber-400",
  LOW:    "text-red-400",
};

interface FindingRowProps {
  finding: FindingInfo;
  index: number;
  isConfirmed: boolean;
}

function FindingRow({ finding, index, isConfirmed }: FindingRowProps) {
  const [expanded, setExpanded] = useState(false);
  const sev = SEVERITY_CONFIG[finding.severity] ?? SEVERITY_CONFIG.LOW;
  const conf = CONFIDENCE_CONFIG[finding.confidence] ?? "text-muted-foreground";

  return (
    <div className={cn(
      "rounded-lg border transition-colors",
      isConfirmed ? "border-red-500/30 bg-red-500/5" : "border-border/40 bg-card/30"
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3 text-left"
      >
        <span className="text-xs text-muted-foreground w-4 shrink-0">{index + 1}</span>

        {/* Severity badge */}
        <span className={cn("inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-medium shrink-0", sev.cls)}>
          <span className={cn("h-1.5 w-1.5 rounded-full", sev.dot)} />
          {finding.severity}
        </span>

        {/* Vuln type */}
        <span className="text-xs font-medium text-foreground flex-1 truncate">{finding.vuln_type}</span>

        {/* File + line */}
        <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <FileCode2 className="h-3 w-3" />
          <code className="text-primary">{finding.file}:{finding.line_start}</code>
        </span>

        {/* Confidence */}
        <span className={cn("text-xs shrink-0", conf)}>
          {finding.confidence}
        </span>

        {/* Confirmed badge */}
        {isConfirmed && (
          <span className="text-xs text-red-400 font-semibold shrink-0">CONFIRMED</span>
        )}

        {expanded
          ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        }
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-border/30 pt-2">
          <p className="text-xs text-muted-foreground leading-relaxed">{finding.description}</p>
          {finding.relevant_code && (
            <pre className="text-xs font-mono bg-black/40 rounded p-2 overflow-x-auto text-emerald-300/80 whitespace-pre-wrap">
              {finding.relevant_code}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

interface FindingsPanelProps {
  findings: FindingInfo[];
  confirmedVulnType?: string | null;
  className?: string;
}

export function FindingsPanel({ findings, confirmedVulnType, className }: FindingsPanelProps) {
  if (!findings.length) return null;

  const critical = findings.filter(f => f.severity === "CRITICAL").length;
  const high = findings.filter(f => f.severity === "HIGH").length;

  return (
    <div className={cn("rounded-xl border border-border/50 bg-card/60 p-4 space-y-3", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-violet-400" />
          <h3 className="text-sm font-semibold text-violet-400">All Findings — Finder Agent</h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {critical > 0 && <span className="text-red-400 font-medium">{critical} critical</span>}
          {high > 0 && <span className="text-red-400/70">{high} high</span>}
          <span>{findings.length} total</span>
        </div>
      </div>

      {/* Findings list */}
      <div className="space-y-1.5">
        {findings.map((f, i) => (
          <FindingRow
            key={i}
            finding={f}
            index={i}
            isConfirmed={!!confirmedVulnType && f.vuln_type === confirmedVulnType}
          />
        ))}
      </div>

      {findings.length > 1 && (
        <p className="text-xs text-muted-foreground">
          Only the highest-severity confirmed finding is patched per scan. Remaining findings will be addressed in subsequent scans.
        </p>
      )}
    </div>
  );
}
