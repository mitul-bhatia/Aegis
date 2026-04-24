"use client";

import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  subLabel?: string;
  accentClass?: string;
  isActive?: boolean;
  className?: string;
}

export function StatCard({
  icon: Icon,
  label,
  value,
  subLabel,
  accentClass = "text-primary",
  isActive = false,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "aegis-glass relative flex items-center gap-4 rounded-xl p-4 transition-all duration-300",
        isActive && "aegis-active-scan",
        className
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/5",
          accentClass
        )}
      >
        <Icon className="h-5 w-5" strokeWidth={1.8} />
      </div>

      {/* Text */}
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={cn("text-2xl font-bold tabular-nums leading-tight", accentClass)}>
          {typeof value === "number" ? value.toLocaleString() : value}
        </p>
        {subLabel && (
          <p className="mt-0.5 text-xs text-muted-foreground">{subLabel}</p>
        )}
      </div>

      {/* Active pulse dot */}
      {isActive && (
        <span className="absolute right-3 top-3 flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
        </span>
      )}
    </div>
  );
}
