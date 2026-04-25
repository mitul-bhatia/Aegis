"use client";

import { Search, Crosshair, Wrench, ShieldCheck, GitPullRequest, Shield } from "lucide-react";

type AgentKey = "finder" | "exploiter" | "engineer" | "verifier" | "safety_validator" | "approval_gate";

const AGENT_CONFIG: Record<AgentKey, { color: string; bg: string; label: string; icon: React.ElementType }> = {
  finder:           { color: "var(--agent-finder)",    bg: "var(--violet-dim)",  label: "Finder",     icon: Search },
  exploiter:        { color: "var(--agent-exploiter)", bg: "var(--red-dim)",     label: "Exploiter",  icon: Crosshair },
  engineer:         { color: "var(--agent-engineer)",  bg: "var(--amber-dim)",   label: "Engineer",   icon: Wrench },
  verifier:         { color: "var(--agent-verifier)",  bg: "var(--green-dim)",   label: "Verifier",   icon: ShieldCheck },
  safety_validator: { color: "var(--amber)",           bg: "var(--amber-dim)",   label: "Safety",     icon: Shield },
  approval_gate:    { color: "var(--blue)",            bg: "var(--blue-dim)",    label: "Approval",   icon: GitPullRequest },
};

const SIZES = { sm: 28, md: 40, lg: 56 };

export function AgentAvatar({
  agent, size = "md", showRing = false, showLabel = false,
}: { agent: AgentKey; size?: "sm" | "md" | "lg"; showRing?: boolean; showLabel?: boolean }) {
  const cfg = AGENT_CONFIG[agent] ?? AGENT_CONFIG.finder;
  const Icon = cfg.icon;
  const px = SIZES[size];
  const iconPx = size === "sm" ? 13 : size === "lg" ? 24 : 17;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, width: "fit-content" }}>
      <div style={{ position: "relative", width: px, height: px }}>
        {/* Pulse rings */}
        {showRing && (
          <>
            <div style={{ position: "absolute", inset: -4, borderRadius: "50%", border: `1.5px solid ${cfg.color}`, animation: "pulse-ring 1.8s ease-out infinite", pointerEvents: "none" }} />
            <div style={{ position: "absolute", inset: -10, borderRadius: "50%", border: `1px solid ${cfg.color}`, animation: "pulse-ring-2 1.8s ease-out infinite 0.4s", pointerEvents: "none" }} />
          </>
        )}
        <div style={{
          width: px, height: px, borderRadius: "50%",
          background: cfg.bg,
          border: `1px solid ${cfg.color}`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon size={iconPx} color={cfg.color} strokeWidth={1.8} />
        </div>
      </div>
      {showLabel && (
        <span style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: cfg.color }}>{cfg.label}</span>
      )}
    </div>
  );
}
