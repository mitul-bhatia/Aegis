"use client";

interface AgentAvatarProps {
  agent: "finder" | "exploiter" | "engineer" | "verifier" | null;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}

const AGENT_CONFIG = {
  finder:    { label: "Finder",    color: "#7c3aed", icon: "🔍", bg: "bg-violet-950" },
  exploiter: { label: "Exploiter", color: "#dc2626", icon: "⚡", bg: "bg-red-950"    },
  engineer:  { label: "Engineer",  color: "#d97706", icon: "🔧", bg: "bg-amber-950"  },
  verifier:  { label: "Verifier",  color: "#059669", icon: "🛡️", bg: "bg-emerald-950"},
};

const SIZE = { sm: "w-6 h-6 text-xs", md: "w-8 h-8 text-sm", lg: "w-12 h-12 text-lg" };

export function AgentAvatar({ agent, size = "md", pulse = false }: AgentAvatarProps) {
  if (!agent) return null;
  const cfg = AGENT_CONFIG[agent];
  return (
    <div className="flex items-center gap-2">
      <div
        className={`${SIZE[size]} ${cfg.bg} rounded-full flex items-center justify-center
                    border-2 relative flex-shrink-0`}
        style={{
          borderColor: cfg.color,
          boxShadow: pulse ? `0 0 12px ${cfg.color}` : undefined,
          animation: pulse ? "status-glow 2s ease-in-out infinite" : undefined,
        }}
      >
        <span>{cfg.icon}</span>
        {pulse && (
          <span
            className="absolute inset-0 rounded-full animate-ping opacity-30"
            style={{ backgroundColor: cfg.color }}
          />
        )}
      </div>
      {size !== "sm" && (
        <span className="text-xs font-mono font-semibold" style={{ color: cfg.color }}>
          {cfg.label}
        </span>
      )}
    </div>
  );
}
