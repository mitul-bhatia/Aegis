"use client";

import { Search, Crosshair, Wrench, ShieldCheck, LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Agent Config ──────────────────────────────────────────
export type AgentType = "finder" | "exploiter" | "engineer" | "verifier";

interface AgentConfig {
  icon: LucideIcon;
  label: string;
  description: string;
  colorClass: string;
  bgClass: string;
  borderClass: string;
  glowClass: string;
  textClass: string;
}

const AGENTS: Record<AgentType, AgentConfig> = {
  finder: {
    icon: Search,
    label: "Finder",
    description: "Analyzes code for vulnerabilities",
    colorClass: "text-violet-400",
    bgClass: "bg-violet-500/15",
    borderClass: "border-violet-500/30",
    glowClass: "shadow-[0_0_16px_oklch(0.70_0.18_285/0.35)]",
    textClass: "text-violet-300",
  },
  exploiter: {
    icon: Crosshair,
    label: "Exploiter",
    description: "Proves vulnerabilities are real",
    colorClass: "text-red-400",
    bgClass: "bg-red-500/15",
    borderClass: "border-red-500/30",
    glowClass: "shadow-[0_0_16px_oklch(0.65_0.22_25/0.35)]",
    textClass: "text-red-300",
  },
  engineer: {
    icon: Wrench,
    label: "Engineer",
    description: "Patches the vulnerable code",
    colorClass: "text-amber-400",
    bgClass: "bg-amber-500/15",
    borderClass: "border-amber-500/30",
    glowClass: "shadow-[0_0_16px_oklch(0.80_0.16_75/0.35)]",
    textClass: "text-amber-300",
  },
  verifier: {
    icon: ShieldCheck,
    label: "Verifier",
    description: "Confirms the fix is complete",
    colorClass: "text-emerald-400",
    bgClass: "bg-emerald-500/15",
    borderClass: "border-emerald-500/30",
    glowClass: "shadow-[0_0_16px_oklch(0.74_0.16_155/0.35)]",
    textClass: "text-emerald-300",
  },
};

// ── Size Config ───────────────────────────────────────────
const SIZES = {
  sm: { container: "h-7 w-7",   icon: "h-3.5 w-3.5", label: "text-xs" },
  md: { container: "h-10 w-10", icon: "h-5 w-5",     label: "text-sm" },
  lg: { container: "h-16 w-16", icon: "h-8 w-8",     label: "text-base" },
};

// ── AgentAvatar Component ─────────────────────────────────
interface AgentAvatarProps {
  agent: AgentType;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  showRing?: boolean;
  className?: string;
}

export function AgentAvatar({
  agent,
  size = "md",
  showLabel = false,
  showRing = false,
  className,
}: AgentAvatarProps) {
  const config = AGENTS[agent];
  const sizeConfig = SIZES[size];
  const Icon = config.icon;

  return (
    <div className={cn("flex flex-col items-center gap-1.5", className)}>
      <div className="relative inline-flex items-center justify-center">
        {/* Pulse rings for active state */}
        {showRing && (
          <>
            <span
              className={cn(
                "absolute rounded-full border opacity-0",
                config.borderClass
              )}
              style={{
                inset: "-6px",
                animation: "pulse-ring 1.8s ease-out infinite",
              }}
            />
            <span
              className={cn(
                "absolute rounded-full border opacity-0",
                config.borderClass
              )}
              style={{
                inset: "-12px",
                animation: "pulse-ring 1.8s ease-out infinite 0.4s",
              }}
            />
          </>
        )}

        {/* Avatar circle */}
        <div
          className={cn(
            "relative flex items-center justify-center rounded-full border transition-shadow duration-300",
            config.bgClass,
            config.borderClass,
            config.colorClass,
            showRing && config.glowClass,
            sizeConfig.container
          )}
        >
          <Icon className={cn("shrink-0", sizeConfig.icon)} strokeWidth={1.8} />
        </div>
      </div>

      {showLabel && (
        <span className={cn("font-medium", config.textClass, sizeConfig.label)}>
          {config.label}
        </span>
      )}
    </div>
  );
}

export { AGENTS };
export type { AgentConfig };
