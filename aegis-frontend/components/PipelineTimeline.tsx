"use client";
import { AgentAvatar } from "./AgentAvatar";
import { LiveTimer } from "./LiveTimer";

const STEPS = [
  { key: "finder",    label: "Finder",    icon: "🔍", statuses: ["scanning"],                     color: "#7c3aed" },
  { key: "exploiter", label: "Exploiter", icon: "⚡", statuses: ["exploiting","exploit_confirmed"], color: "#dc2626" },
  { key: "engineer",  label: "Engineer",  icon: "🔧", statuses: ["patching"],                      color: "#d97706" },
  { key: "verifier",  label: "Verifier",  icon: "🛡️", statuses: ["verifying"],                     color: "#059669" },
] as const;

interface Props {
  currentAgent: string | null;
  status: string;
  agentMessage: string | null;
  createdAt: string;
}

export function PipelineTimeline({ currentAgent, status, agentMessage, createdAt }: Props) {
  const TERMINAL = ["fixed", "failed", "false_positive", "clean", "no_vulnerability"];
  const isDone = TERMINAL.includes(status);
  const successDone = status === "fixed" || status === "clean";

  const getStepState = (step: typeof STEPS[number]) => {
    if (step.statuses.includes(status as never) || step.key === currentAgent) return "active";
    const stepIdx = STEPS.findIndex(s => s.key === step.key);
    const curIdx  = STEPS.findIndex(s => s.key === currentAgent || s.statuses.includes(status as never));
    if (isDone) return "complete";
    if (stepIdx < curIdx) return "complete";
    return "pending";
  };

  return (
    <div className="flex flex-col gap-0 py-4">
      {STEPS.map((step, i) => {
        const state = getStepState(step);
        return (
          <div key={step.key}>
            <div className="flex items-start gap-3 px-4">
              <div className="flex flex-col items-center">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-base relative z-10
                             border-2 transition-all duration-500"
                  style={{
                    borderColor: state !== "pending" ? step.color : "#334155",
                    backgroundColor: state === "active" ? `${step.color}22` : state === "complete" ? `${step.color}11` : "#0f172a",
                    boxShadow: state === "active" ? `0 0 14px ${step.color}` : undefined,
                    animation: state === "active" ? "status-glow 2s ease-in-out infinite" : undefined,
                  }}
                >
                  {state === "complete" ? "✓" : step.icon}
                </div>
              </div>
              <div className="pb-6 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-semibold text-sm"
                        style={{ color: state !== "pending" ? step.color : "#475569" }}>
                    {step.label}
                  </span>
                  {state === "active" && <LiveTimer startedAt={createdAt} />}
                  {state === "complete" && (
                    <span className="text-xs text-emerald-500 font-mono">done</span>
                  )}
                </div>
                {state === "active" && agentMessage && (
                  <p className="text-xs text-slate-400 font-mono leading-relaxed animate-pulse">
                    {agentMessage}
                  </p>
                )}
                {state === "complete" && (
                  <p className="text-xs text-slate-600">Completed</p>
                )}
                {state === "pending" && (
                  <p className="text-xs text-slate-700">Waiting...</p>
                )}
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div className="ml-[2.125rem] w-0.5 h-6"
                   style={{ backgroundColor: state === "complete" ? step.color : "#1e293b" }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
