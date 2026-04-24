"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { AgentAvatar, type AgentType } from "./AgentAvatar";
import { LiveTimer } from "./LiveTimer";
import { cn } from "@/lib/utils";
import type { ScanInfo, ScanStatus } from "@/lib/api";

// ── Pipeline Step Definition ──────────────────────────────
interface PipelineStep {
  id: AgentType;
  label: string;
  activeStatuses: ScanStatus[];
  doneStatuses: ScanStatus[];
  failStatus?: ScanStatus;
  getDetail: (scan: ScanInfo) => string | null;
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    id: "finder",
    label: "Finder",
    activeStatuses: ["scanning"],
    doneStatuses: ["exploiting", "exploit_confirmed", "patching", "verifying", "fixed", "false_positive", "clean"],
    getDetail: (scan) => {
      if (scan.vulnerability_type) return `Found: ${scan.vulnerability_type}${scan.severity ? ` [${scan.severity}]` : ""}`;
      if (scan.status === "clean") return "No vulnerabilities detected";
      return null;
    },
  },
  {
    id: "exploiter",
    label: "Exploiter",
    activeStatuses: ["exploiting"],
    doneStatuses: ["exploit_confirmed", "patching", "verifying", "fixed", "false_positive"],
    failStatus: "false_positive",
    getDetail: (scan) => {
      if (scan.status === "false_positive") return "Exploit failed — marked as false positive";
      if (["exploit_confirmed", "patching", "verifying", "fixed"].includes(scan.status))
        return `Exploit confirmed: ${scan.vulnerability_type ?? "vulnerability"}`;
      return null;
    },
  },
  {
    id: "engineer",
    label: "Engineer",
    activeStatuses: ["patching"],
    doneStatuses: ["verifying", "fixed"],
    getDetail: (scan) => {
      if (["verifying", "fixed"].includes(scan.status)) {
        const attempts = scan.patch_attempts ?? 1;
        return `Patch generated${attempts > 1 ? ` (${attempts} attempt${attempts > 1 ? "s" : ""})` : ""}`;
      }
      return null;
    },
  },
  {
    id: "verifier",
    label: "Verifier",
    activeStatuses: ["verifying"],
    doneStatuses: ["fixed"],
    getDetail: (scan) => {
      if (scan.status === "fixed") return "Exploit blocked · Tests passing · PR opened";
      return null;
    },
  },
];

// ── Step State Resolver ───────────────────────────────────
type StepState = "pending" | "active" | "done" | "failed" | "skipped";

function getStepState(step: PipelineStep, scan: ScanInfo): StepState {
  if (step.doneStatuses.includes(scan.status as ScanStatus)) return "done";
  if (step.failStatus && scan.status === step.failStatus) {
    return step.id === "exploiter" ? "done" : "skipped";
  }
  if (step.activeStatuses.includes(scan.status as ScanStatus)) return "active";
  if (scan.current_agent === step.id) return "active";
  if (scan.status === "failed" && scan.current_agent === step.id) return "failed";
  return "pending";
}

// ── Connector Line ────────────────────────────────────────
function ConnectorLine({ filled, agentColor }: { filled: boolean; agentColor: string }) {
  return (
    <div className="relative ml-[19px] h-8 w-px">
      <div className="absolute inset-0 border-l-2 border-dashed border-white/10" />
      {filled && (
        <div className={cn("pipeline-fill absolute inset-0 border-l-2", agentColor)} />
      )}
    </div>
  );
}

// ── Agent color maps ──────────────────────────────────────
const AGENT_COLORS: Record<AgentType, string> = {
  finder:    "border-violet-500",
  exploiter: "border-red-500",
  engineer:  "border-amber-500",
  verifier:  "border-emerald-500",
};

const AGENT_TEXT_COLORS: Record<AgentType, string> = {
  finder:    "text-violet-400",
  exploiter: "text-red-400",
  engineer:  "text-amber-400",
  verifier:  "text-emerald-400",
};

// ── Single Step Row ───────────────────────────────────────
interface StepProps {
  step: PipelineStep;
  state: StepState;
  scan: ScanInfo;
}

function PipelineStepRow({ step, state, scan }: StepProps) {
  const detail = step.getDetail(scan);
  const agentMessage = scan.current_agent === step.id ? scan.agent_message : null;
  const isActive = state === "active";
  const isDone = state === "done";
  const isFailed = state === "failed";
  const isPending = state === "pending" || state === "skipped";

  return (
    <div className="flex items-start gap-3">
      {/* Node */}
      <div className="shrink-0">
        {isPending ? (
          <div className="h-10 w-10 rounded-full border-2 border-dashed border-white/15 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-white/15" />
          </div>
        ) : isDone ? (
          <div className={cn(
            "h-10 w-10 rounded-full border flex items-center justify-center bg-white/5",
            AGENT_COLORS[step.id]
          )}>
            <CheckCircle2 className={cn("h-5 w-5", AGENT_TEXT_COLORS[step.id])} strokeWidth={2} />
          </div>
        ) : isFailed ? (
          <div className="h-10 w-10 rounded-full border border-red-500/50 bg-red-500/10 flex items-center justify-center">
            <XCircle className="h-5 w-5 text-red-400" strokeWidth={2} />
          </div>
        ) : (
          <AgentAvatar agent={step.id} size="md" showRing={isActive} />
        )}
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0 pt-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className={cn(
            "text-sm font-semibold",
            isPending    ? "text-muted-foreground"
              : isFailed ? "text-red-400"
              : isDone   ? "text-foreground"
              : AGENT_TEXT_COLORS[step.id]
          )}>
            {step.label}
          </span>
          {isActive && scan.created_at && (
            <LiveTimer startTime={scan.created_at} isActive={true} className="shrink-0" />
          )}
        </div>

        {(agentMessage || detail) && (
          <p className={cn(
            "mt-0.5 text-xs leading-relaxed",
            isActive ? AGENT_TEXT_COLORS[step.id] : "text-muted-foreground"
          )}>
            {isActive ? (agentMessage ?? detail) : detail}
          </p>
        )}

        {isActive && !agentMessage && !detail && (
          <p className={cn("mt-0.5 text-xs", AGENT_TEXT_COLORS[step.id])}>
            Working...
          </p>
        )}
      </div>
    </div>
  );
}

// ── Main PipelineTimeline ─────────────────────────────────
interface PipelineTimelineProps {
  scan: ScanInfo;
  className?: string;
}

export function PipelineTimeline({ scan, className }: PipelineTimelineProps) {
  const isEarlyClean = scan.status === "clean";
  const isEarlyFP    = scan.status === "false_positive";
  const stepsToShow  = isEarlyClean ? PIPELINE_STEPS.slice(0, 1)
    : isEarlyFP ? PIPELINE_STEPS.slice(0, 2)
    : PIPELINE_STEPS;

  return (
    <div className={cn("space-y-0", className)}>
      {stepsToShow.map((step, idx) => {
        const state = getStepState(step, scan);
        const isLast = idx === stepsToShow.length - 1;

        return (
          <div key={step.id}>
            <PipelineStepRow step={step} state={state} scan={scan} />
            {!isLast && (
              <ConnectorLine
                filled={state === "done"}
                agentColor={AGENT_COLORS[step.id]}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
