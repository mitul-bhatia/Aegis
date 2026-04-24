/**
 * PriorityIndicator Component
 * 
 * Shows scan priority level with pulsing animation for critical priorities.
 * Used to indicate how urgently a repository needs scanning.
 */

import { Badge } from "@/components/ui/badge";
import { Zap, TrendingUp, Activity, Clock, Minus } from "lucide-react";

interface PriorityIndicatorProps {
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "ROUTINE";
  showIcon?: boolean;
  animated?: boolean;
  className?: string;
}

export function PriorityIndicator({ 
  priority, 
  showIcon = true,
  animated = true,
  className = "" 
}: PriorityIndicatorProps) {
  // Get color and animation classes
  const getClasses = () => {
    const baseClasses = "border";
    const pulseClass = animated && priority === "CRITICAL" ? "animate-pulse" : "";
    
    switch (priority) {
      case "CRITICAL":
        return `${baseClasses} bg-red-500/10 text-red-500 border-red-500 ${pulseClass}`;
      case "HIGH":
        return `${baseClasses} bg-orange-500/10 text-orange-500 border-orange-500`;
      case "MEDIUM":
        return `${baseClasses} bg-amber-500/10 text-amber-500 border-amber-500`;
      case "LOW":
        return `${baseClasses} bg-emerald-500/10 text-emerald-500 border-emerald-500`;
      case "ROUTINE":
        return `${baseClasses} bg-gray-500/10 text-gray-500 border-gray-500`;
      default:
        return baseClasses;
    }
  };

  // Get icon based on priority
  const getIcon = () => {
    const iconClass = "h-3 w-3";
    switch (priority) {
      case "CRITICAL":
        return <Zap className={iconClass} />;
      case "HIGH":
        return <TrendingUp className={iconClass} />;
      case "MEDIUM":
        return <Activity className={iconClass} />;
      case "LOW":
        return <Clock className={iconClass} />;
      case "ROUTINE":
        return <Minus className={iconClass} />;
      default:
        return null;
    }
  };

  return (
    <Badge 
      variant="outline" 
      className={`${getClasses()} ${className}`}
    >
      {showIcon && <span className="mr-1">{getIcon()}</span>}
      {priority}
    </Badge>
  );
}
