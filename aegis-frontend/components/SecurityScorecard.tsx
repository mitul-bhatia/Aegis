"use client";

import type { ScorecardData } from "@/lib/api";
import { Shield, AlertTriangle, Clock, CheckCircle2, TrendingDown } from "lucide-react";

// ── Grade config ──────────────────────────────────────────
const GRADE_CONFIG: Record<string, { colour: string; bg: string; border: string; label: string }> = {
  "A": { colour: "text-emerald-400", bg: "bg-emerald-500/15", border: "border-emerald-500/40", label: "Excellent" },
  "B": { colour: "text-blue-400",    bg: "bg-blue-500/15",    border: "border-blue-500/40",    label: "Good" },
  "C": { colour: "text-amber-400",   bg: "bg-amber-500/15",   border: "border-amber-500/40",   label: "Fair" },
  "D": { colour: "text-orange-400",  bg: "bg-orange-500/15",  border: "border-orange-500/40",  label: "Poor" },
  "F": { colour: "text-red-400",     bg: "bg-red-500/15",     border: "border-red-500/40",     label: "Critical" },
  "N/A": { colour: "text-muted-foreground", bg: "bg-white/5", border: "border-white/10",       label: "No data" },
};

const DIMENSION_ICONS: Record<string, React.ElementType> = {
  vulnerability_rate: Shield,
  fix_rate:           CheckCircle2,
  mttr:               Clock,
  open_severity:      AlertTriangle,
  regression_rate:    TrendingDown,
};

// ── Score bar ─────────────────────────────────────────────
function ScoreBar({ score }: { score: number }) {
  const colour =
    score >= 80 ? "bg-emerald-500"
    : score >= 60 ? "bg-amber-500"
    : "bg-red-500";

  return (
    <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${colour}`}
        style={{ width: `${score}%` }}
      />
    </div>
  );
}

// ── Main component ────────────────────────────────────────
export function SecurityScorecard({ data }: { data: ScorecardData }) {
  const grade = data.grade ?? "N/A";
  const cfg = GRADE_CONFIG[grade] ?? GRADE_CONFIG["N/A"];

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur-sm space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Security Scorecard
        </h2>
        <span className="text-xs text-muted-foreground">Last 30 days</span>
      </div>

      {data.message ? (
        <p className="text-sm text-muted-foreground py-4 text-center">{data.message}</p>
      ) : (
        <>
          {/* Grade + score */}
          <div className="flex items-center gap-5">
            <div className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl border-2 ${cfg.bg} ${cfg.border}`}>
              <span className={`text-4xl font-black ${cfg.colour}`}>{grade}</span>
            </div>
            <div className="flex-1 space-y-1.5">
              <div className="flex items-baseline justify-between">
                <span className={`text-lg font-bold ${cfg.colour}`}>{cfg.label}</span>
                <span className="text-sm text-muted-foreground">{data.score}/100</span>
              </div>
              <ScoreBar score={data.score ?? 0} />
              <div className="flex gap-4 text-xs text-muted-foreground pt-0.5">
                <span>{data.total_scans} scans</span>
                <span>{Math.round(data.fix_rate * 100)}% fix rate</span>
                {data.mttr_hours > 0 && <span>{data.mttr_hours}h avg fix time</span>}
                {data.open_vulns > 0 && (
                  <span className="text-red-400">{data.open_vulns} open high/critical</span>
                )}
              </div>
            </div>
          </div>

          {/* Dimension breakdown */}
          {Object.entries(data.dimensions).length > 0 && (
            <div className="space-y-3 pt-1">
              {Object.entries(data.dimensions).map(([key, dim]) => {
                const Icon = DIMENSION_ICONS[key] ?? Shield;
                const scoreColour =
                  dim.score >= 80 ? "text-emerald-400"
                  : dim.score >= 60 ? "text-amber-400"
                  : "text-red-400";

                return (
                  <div key={key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Icon className="h-3 w-3" />
                        <span>{dim.label}</span>
                        <span className="text-white/20">·</span>
                        <span className="text-white/30">{Math.round(dim.weight * 100)}% weight</span>
                      </div>
                      <span className={`font-semibold ${scoreColour}`}>{dim.score}</span>
                    </div>
                    <ScoreBar score={dim.score} />
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
