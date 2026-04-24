"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface LiveTimerProps {
  startTime: string;      // ISO string
  isActive?: boolean;     // If false, shows final elapsed (frozen)
  className?: string;
  showPulse?: boolean;    // Subtle color pulse on each tick
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

export function LiveTimer({ startTime, isActive = true, className, showPulse = true }: LiveTimerProps) {
  const [elapsed, setElapsed] = useState(0);
  const [tick, setTick] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const start = new Date(startTime).getTime();

    const update = () => {
      setElapsed(Date.now() - start);
      if (showPulse) {
        setTick(true);
        setTimeout(() => setTick(false), 300);
      }
    };

    update();

    if (isActive) {
      intervalRef.current = setInterval(update, 1000);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [startTime, isActive, showPulse]);

  return (
    <span
      className={cn(
        "font-mono tabular-nums text-xs transition-colors duration-300",
        isActive
          ? tick
            ? "text-primary"
            : "text-muted-foreground"
          : "text-muted-foreground",
        className
      )}
    >
      {formatElapsed(elapsed)}
    </span>
  );
}

export { formatElapsed };
