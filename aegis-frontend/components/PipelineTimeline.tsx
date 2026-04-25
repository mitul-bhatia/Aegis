"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { AgentAvatar } from "./AgentAvatar";
import type { ScanInfo, ScanStatus } from "@/lib/api";

type AgentType = "finder" | "exploiter" | "engineer" | "verifier" | "safety_validator" | "approval_gate";

const AGENT_COLORS: Record<AgentType, string> = {
  finder:           "var(--agent-finder)",
  exploiter:        "var(--agent-exploiter)",
  engineer:         "var(--agent-engineer)",
  verifier:         "var(--agent-verifier)",
  safety_validator: "var(--amber)",
  approval_gate:    "var(--blue)",
};

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
    id: "finder", label: "Finder",
    activeStatuses: ["scanning"],
    doneStatuses: ["exploiting", "exploit_confirmed", "patching", "verifying", "fixed", "false_positive", "clean"],
    getDetail: (s) => s.vulnerability_type ? `Found: ${s.vulnerability_type}${s.severity ? ` · ${s.severity}` : ""}` : s.status === "clean" ? "No vulnerabilities" : null,
  },
  {
    id: "exploiter", label: "Exploiter",
    activeStatuses: ["exploiting"],
    doneStatuses: ["exploit_confirmed", "patching", "verifying", "fixed", "false_positive"],
    failStatus: "false_positive",
    getDetail: (s) => s.status === "false_positive" ? "Exploit failed — false positive" : ["exploit_confirmed", "patching", "verifying", "fixed"].includes(s.status) ? `Confirmed: ${s.vulnerability_type ?? "vulnerability"}` : null,
  },
  {
    id: "engineer", label: "Engineer",
    activeStatuses: ["patching"],
    doneStatuses: ["verifying", "fixed", "awaiting_approval"],
    getDetail: (s) => ["verifying", "fixed", "awaiting_approval"].includes(s.status) ? `Patch generated${(s.patch_attempts ?? 1) > 1 ? ` after ${s.patch_attempts} attempts` : ""}` : null,
  },
  {
    id: "verifier", label: "Verifier",
    activeStatuses: ["verifying"],
    doneStatuses: ["fixed", "awaiting_approval"],
    getDetail: (s) => ["fixed", "awaiting_approval"].includes(s.status) ? "Exploit blocked · Tests passing" : null,
  },
  {
    id: "safety_validator", label: "Safety Check",
    activeStatuses: ["verifying"],
    doneStatuses: ["fixed", "awaiting_approval"],
    getDetail: (s) => ["fixed", "awaiting_approval"].includes(s.status) ? "Full diff re-scan passed" : null,
  },
  {
    id: "approval_gate", label: "Approval Gate",
    activeStatuses: ["awaiting_approval"],
    doneStatuses: ["fixed"],
    getDetail: (s) => s.status === "awaiting_approval" ? "CRITICAL — awaiting human approval" : s.status === "fixed" ? "Approved · PR opened" : null,
  },
];

type StepState = "pending" | "active" | "done" | "failed" | "skipped";

function getStepState(step: PipelineStep, scan: ScanInfo): StepState {
  if (step.doneStatuses.includes(scan.status as ScanStatus)) return "done";
  if (step.failStatus && scan.status === step.failStatus) return step.id === "exploiter" ? "done" : "skipped";
  if (step.activeStatuses.includes(scan.status as ScanStatus)) return "active";
  if (scan.current_agent === step.id) return "active";
  if (scan.status === "failed" && scan.current_agent === step.id) return "failed";
  return "pending";
}

export function PipelineTimeline({ scan }: { scan: ScanInfo; className?: string }) {
  const isEarlyClean = scan.status === "clean";
  const isEarlyFP = scan.status === "false_positive";
  const steps = isEarlyClean ? PIPELINE_STEPS.slice(0, 1) : isEarlyFP ? PIPELINE_STEPS.slice(0, 2) : PIPELINE_STEPS;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {steps.map((step, idx) => {
        const state = getStepState(step, scan);
        const isActive = state === "active";
        const isDone = state === "done";
        const isFailed = state === "failed";
        const isLast = idx === steps.length - 1;
        const color = AGENT_COLORS[step.id];
        const detail = step.getDetail(scan);

        return (
          <div key={step.id} style={{ display: "flex", gap: 0 }}>
            {/* Left column: dot + connector */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 40, flexShrink: 0 }}>
              {/* Node */}
              <div style={{ width: 32, height: 32, position: "relative", flexShrink: 0 }}>
                {isActive || isDone ? (
                  <AgentAvatar agent={step.id} size="sm" showRing={isActive} />
                ) : isFailed ? (
                  <div style={{ width: 28, height: 28, borderRadius: "50%", border: "1px solid var(--red)", background: "var(--red-dim)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <XCircle size={13} color="var(--red)" />
                  </div>
                ) : (
                  <div style={{ width: 28, height: 28, borderRadius: "50%", border: "1px dashed var(--border)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--border)" }} />
                  </div>
                )}
              </div>
              {/* Connector */}
              {!isLast && (
                <div style={{ width: 1, flex: 1, minHeight: 24, background: isDone ? color : "var(--border)", opacity: isDone ? 0.6 : 0.3, margin: "4px 0", transition: "background 0.4s" }} />
              )}
            </div>

            {/* Right column: label + detail */}
            <div style={{ paddingLeft: 12, paddingBottom: isLast ? 0 : 20, paddingTop: 4, flex: 1 }}>
              <div style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.12em", color: isActive ? color : isDone ? "var(--foreground)" : "var(--muted)", marginBottom: 4 }}>
                {step.label}
                {isActive && (
                  <span style={{ marginLeft: 8, fontSize: 9, color: color, animation: "pulse 2s infinite" }}>● Active</span>
                )}
              </div>
              {detail && (
                <div style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 10, color: "var(--muted)", lineHeight: 1.5 }}>{detail}</div>
              )}
              {step.id === "engineer" && (scan.patch_attempts ?? 0) > 1 && (
                <div style={{ display: "inline-flex", marginTop: 4, padding: "1px 8px", background: "var(--amber-dim)", color: "var(--amber)", fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 9, letterSpacing: "0.1em" }}>
                  ↻ Retry ×{(scan.patch_attempts ?? 1) - 1}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
