"use client";

interface StatCardProps {
  icon?: React.ElementType;
  label: string;
  value: string | number;
  subLabel?: string;
  accentClass?: string;
  isActive?: boolean;
}

export function StatCard({ icon: Icon, label, value, subLabel, accentClass, isActive }: StatCardProps) {
  // Map old Tailwind accent classes to CSS vars
  const colorMap: Record<string, string> = {
    "text-primary":       "var(--green)",
    "text-emerald-400":   "var(--agent-verifier)",
    "text-amber-400":     "var(--amber)",
    "text-muted-foreground": "var(--muted)",
    "text-red-400":       "var(--red)",
    "text-blue-400":      "var(--blue)",
    "text-violet-400":    "var(--agent-finder)",
  };
  const color = accentClass ? (colorMap[accentClass] ?? "var(--green)") : "var(--green)";

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", padding: "20px 20px", position: "relative", overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        {isActive && (
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block", animation: "pulse 2s ease-in-out infinite" }} />
        )}
        {Icon && <Icon size={14} color="var(--muted)" />}
        <span style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 10, color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase" }}>{label}</span>
      </div>
      <div style={{ fontFamily: "var(--font-syne,sans-serif)", fontWeight: 800, fontSize: 36, lineHeight: 1, color }}>
        {value}
      </div>
      {subLabel && (
        <div style={{ fontFamily: "var(--font-share-tech-mono,monospace)", fontSize: 10, color: "var(--muted)", marginTop: 4, letterSpacing: "0.08em" }}>{subLabel}</div>
      )}
    </div>
  );
}
