"use client";

import { ScanInfo, TERMINAL_STATUSES } from "@/lib/api";
import { AgentAvatar } from "./AgentAvatar";
import { LiveTimer } from "./LiveTimer";
import Link from "next/link";

interface Props {
  scan: ScanInfo;
}

export function VulnCard({ scan }: Props) {
  const isTerminal = TERMINAL_STATUSES.includes(scan.status);

  // Base styling depending on terminal state
  const isFixed = scan.status === "fixed";
  const isFailed = scan.status === "failed";
  const isClean = scan.status === "clean" || scan.status === "false_positive";

  let borderColor = "border-slate-800";
  if (isFixed) borderColor = "border-emerald-900/50";
  if (isFailed) borderColor = "border-red-900/50";
  if (isClean) borderColor = "border-slate-800"; // neutral

  // Active scan styling overrides
  if (!isTerminal) {
    if (scan.current_agent === "finder") borderColor = "border-violet-500/50 shadow-[0_0_15px_rgba(124,58,237,0.15)]";
    if (scan.current_agent === "exploiter") borderColor = "border-red-500/50 shadow-[0_0_15px_rgba(220,38,38,0.15)]";
    if (scan.current_agent === "engineer") borderColor = "border-amber-500/50 shadow-[0_0_15px_rgba(217,119,6,0.15)]";
    if (scan.current_agent === "verifier") borderColor = "border-emerald-500/50 shadow-[0_0_15px_rgba(5,150,105,0.15)]";
  }

  return (
    <div className={`bg-slate-900/40 rounded-xl p-5 border transition-all ${borderColor} ${!isTerminal ? "aegis-active-scan" : "hover:bg-slate-800/50"}`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <Link href={`/scans/${scan.id}`} className="text-lg font-bold font-mono text-slate-200 hover:text-white transition-colors">
            {scan.vulnerability_type || "Scanning..."}
          </Link>
          <div className="flex gap-2 items-center mt-1">
            <span className="text-xs font-mono text-slate-500">#{scan.commit_sha.substring(0, 7)}</span>
            {scan.severity && (
              <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded
                ${scan.severity === "ERROR" ? "bg-red-950 text-red-400" : "bg-amber-950 text-amber-400"}`}>
                {scan.severity}
              </span>
            )}
            <span className="text-xs font-mono text-slate-500">{scan.vulnerable_file}</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          {!isTerminal ? (
            <div className="flex items-center gap-3">
              <AgentAvatar agent={scan.current_agent || null} size="sm" pulse={true} />
              <LiveTimer startedAt={scan.created_at} />
            </div>
          ) : (
            <div className="flex flex-col items-end">
              <span className={`text-xs font-bold uppercase tracking-wider
                ${isFixed ? "text-emerald-500" : isFailed ? "text-red-500" : "text-slate-500"}`}>
                {scan.status.replace("_", " ")}
              </span>
              {isFixed && scan.pr_url && (
                <a href={scan.pr_url} target="_blank" rel="noopener noreferrer"
                   className="mt-2 text-xs bg-emerald-950/50 text-emerald-400 hover:text-emerald-300 border border-emerald-900/50 px-2 py-1 rounded transition-colors">
                  View PR ↗
                </a>
              )}
            </div>
          )}
        </div>
      </div>

      {!isTerminal && scan.agent_message && (
        <div className="mt-3 text-xs font-mono text-slate-400 bg-black/20 p-2 rounded border border-white/5 truncate">
          <span className="opacity-50 mr-2">&gt;</span>{scan.agent_message}
        </div>
      )}
    </div>
  );
}
