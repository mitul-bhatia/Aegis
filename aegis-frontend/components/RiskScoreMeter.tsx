/**
 * RiskScoreMeter Component
 * 
 * Visual meter showing ML-predicted risk score with color gradient.
 * Displays risk level from 0.0 (low) to 1.0 (high) with appropriate colors.
 */

import { Progress } from "@/components/ui/progress";
import { Brain } from "lucide-react";

interface RiskScoreMeterProps {
  score: number; // 0.0 to 1.0
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function RiskScoreMeter({ 
  score, 
  showLabel = true,
  size = "md",
  className = "" 
}: RiskScoreMeterProps) {
  // Clamp score between 0 and 1
  const clampedScore = Math.max(0, Math.min(1, score));
  const percentage = clampedScore * 100;

  // Get risk level text
  const getRiskLevel = () => {
    if (clampedScore >= 0.8) return "Critical";
    if (clampedScore >= 0.6) return "High";
    if (clampedScore >= 0.4) return "Medium";
    return "Low";
  };

  // Get color based on risk score
  const getColor = () => {
    if (clampedScore >= 0.8) return "text-red-500";
    if (clampedScore >= 0.6) return "text-orange-500";
    if (clampedScore >= 0.4) return "text-amber-500";
    return "text-emerald-500";
  };

  // Get progress bar color
  const getProgressColor = () => {
    if (clampedScore >= 0.8) return "bg-red-500";
    if (clampedScore >= 0.6) return "bg-orange-500";
    if (clampedScore >= 0.4) return "bg-amber-500";
    return "bg-emerald-500";
  };

  // Size classes
  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3"
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {showLabel && (
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1 text-gray-400">
            <Brain className="h-3 w-3" />
            <span>ML Risk</span>
          </div>
          <span className={`font-medium ${getColor()}`}>
            {(clampedScore * 100).toFixed(0)}% ({getRiskLevel()})
          </span>
        </div>
      )}
      <div className="relative">
        <Progress 
          value={percentage} 
          className={`${sizeClasses[size]} bg-gray-700`}
        />
        <div 
          className={`absolute top-0 left-0 h-full ${getProgressColor()} rounded-full transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
