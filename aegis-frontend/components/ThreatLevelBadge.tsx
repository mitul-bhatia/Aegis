/**
 * ThreatLevelBadge Component
 * 
 * Displays threat level with appropriate color coding and icon.
 * Used to show security threat levels across the application.
 */

import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Shield, AlertCircle, Info } from "lucide-react";

interface ThreatLevelBadgeProps {
  level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  showIcon?: boolean;
  className?: string;
}

export function ThreatLevelBadge({ 
  level, 
  showIcon = true,
  className = "" 
}: ThreatLevelBadgeProps) {
  // Get color classes based on threat level
  const getColorClasses = () => {
    switch (level) {
      case "CRITICAL":
        return "bg-red-500/10 text-red-500 border-red-500 hover:bg-red-500/20";
      case "HIGH":
        return "bg-orange-500/10 text-orange-500 border-orange-500 hover:bg-orange-500/20";
      case "MEDIUM":
        return "bg-amber-500/10 text-amber-500 border-amber-500 hover:bg-amber-500/20";
      case "LOW":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500 hover:bg-emerald-500/20";
      default:
        return "bg-gray-500/10 text-gray-500 border-gray-500";
    }
  };

  // Get icon based on threat level
  const getIcon = () => {
    const iconClass = "h-3 w-3";
    switch (level) {
      case "CRITICAL":
        return <AlertTriangle className={iconClass} />;
      case "HIGH":
        return <AlertCircle className={iconClass} />;
      case "MEDIUM":
        return <Info className={iconClass} />;
      case "LOW":
        return <Shield className={iconClass} />;
      default:
        return null;
    }
  };

  return (
    <Badge 
      variant="outline" 
      className={`${getColorClasses()} ${className}`}
    >
      {showIcon && <span className="mr-1">{getIcon()}</span>}
      {level}
    </Badge>
  );
}
