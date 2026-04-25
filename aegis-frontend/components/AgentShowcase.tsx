"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { 
  Search, 
  Crosshair, 
  Wrench, 
  ShieldCheck, 
  Brain,
  Zap,
  ArrowRight,
  Play
} from "lucide-react";

interface Agent {
  id: string;
  name: string;
  type: "finder" | "exploiter" | "engineer" | "verifier";
  icon: React.ElementType;
  description: string;
  tagline: string;
  details: string;
  color: string;
  bgColor: string;
  borderColor: string;
  textColor: string;
  capabilities: string[];
  stats: {
    accuracy: number;
    speed: number;
    reliability: number;
  };
}

interface AgentShowcaseProps {
  onAgentClick?: (agent: Agent) => void;
  className?: string;
}

const AGENTS: Agent[] = [
  {
    id: "finder",
    name: "The Finder",
    type: "finder",
    icon: Search,
    tagline: "Analyzes every changed line. Finds what humans miss.",
    description: "Combines Semgrep static analysis + RAG context to identify SQLi, XSS, path traversal, and 40+ other CVE patterns.",
    details: "Advanced pattern recognition with ML-enhanced detection. Learns from past vulnerabilities to improve accuracy.",
    color: "violet",
    bgColor: "bg-violet-500/10",
    borderColor: "border-violet-500",
    textColor: "text-violet-400",
    capabilities: [
      "Static code analysis",
      "Pattern recognition",
      "CVE database matching",
      "RAG context analysis",
      "ML prediction"
    ],
    stats: {
      accuracy: 94,
      speed: 85,
      reliability: 92
    }
  },
  {
    id: "exploiter",
    name: "The Exploiter",
    type: "exploiter",
    icon: Crosshair,
    tagline: "Doesn't guess. Writes code that proves it.",
    description: "Generates and runs a real exploit script in an isolated Docker sandbox. If it doesn't crash your app, it's not a real vulnerability.",
    details: "Advanced exploit generation with multiple attack vectors. Tests in isolated containers to ensure safety.",
    color: "red",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500",
    textColor: "text-red-400",
    capabilities: [
      "Exploit generation",
      "Sandbox testing",
      "Impact assessment",
      "Bypass techniques",
      "Proof of concept"
    ],
    stats: {
      accuracy: 89,
      speed: 78,
      reliability: 95
    }
  },
  {
    id: "engineer",
    name: "The Engineer",
    type: "engineer",
    icon: Wrench,
    tagline: "Fixes the root cause, not the symptom.",
    description: "Rewrites the vulnerable function, respects your code style, and ensures existing tests still pass.",
    details: "Intelligent patch generation with security best practices. Maintains code functionality while eliminating vulnerabilities.",
    color: "amber",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500",
    textColor: "text-amber-400",
    capabilities: [
      "Patch generation",
      "Code style preservation",
      "Test compatibility",
      "Security best practices",
      "Automated refactoring"
    ],
    stats: {
      accuracy: 91,
      speed: 82,
      reliability: 88
    }
  },
  {
    id: "verifier",
    name: "The Verifier",
    type: "verifier",
    icon: ShieldCheck,
    tagline: "Tries to break its own patch. If it can't, it ships.",
    description: "Re-runs the exploit + unit tests against the patched code. Loops back to the Engineer up to 3× if anything fails.",
    details: "Comprehensive verification with exploit testing and regression analysis. Ensures patches are truly effective.",
    color: "emerald",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500",
    textColor: "text-emerald-400",
    capabilities: [
      "Patch verification",
      "Regression testing",
      "Exploit validation",
      "Quality assurance",
      "Security confirmation"
    ],
    stats: {
      accuracy: 96,
      speed: 88,
      reliability: 94
    }
  }
];

export default function AgentShowcase({ onAgentClick, className }: AgentShowcaseProps) {
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-cyan-400 mb-2">
          Meet Your AI Security Swarm
        </h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Four specialized AI agents working together to find, prove, fix, and verify vulnerabilities automatically
        </p>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {AGENTS.map((agent, index) => {
          const Icon = agent.icon;
          const isHovered = hoveredAgent === agent.id;
          const isSelected = selectedAgent === agent.id;
          
          return (
            <Card
              key={agent.id}
              className={cn(
                "relative overflow-hidden transition-all duration-300 cursor-pointer",
                "border border-gray-700 bg-gray-800/50",
                isHovered && `${agent.borderColor} ${agent.bgColor} shadow-lg transform scale-105`,
                isSelected && `${agent.borderColor} ${agent.bgColor} ring-2 ring-${agent.color}-500/50`
              )}
              onMouseEnter={() => setHoveredAgent(agent.id)}
              onMouseLeave={() => setHoveredAgent(null)}
              onClick={() => {
                setSelectedAgent(agent.id);
                onAgentClick?.(agent);
              }}
              style={{ animationDelay: `${index * 150}ms` }}
            >
              {/* Animated gradient background */}
              <div className={cn(
                "absolute inset-0 opacity-0 transition-opacity duration-300",
                `bg-gradient-to-br from-${agent.color}-500/10 to-transparent`,
                isHovered && "opacity-100"
              )} />
              
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className={cn(
                    "p-2 rounded-lg transition-colors",
                    agent.bgColor,
                    isHovered && "bg-opacity-30"
                  )}>
                    <Icon className={cn("h-6 w-6", agent.textColor)} />
                  </div>
                  
                  <Badge variant="outline" className={cn(
                    "text-xs border-2",
                    agent.borderColor,
                    agent.textColor
                  )}>
                    {agent.name}
                  </Badge>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Tagline */}
                <div className={cn("text-sm font-medium", agent.textColor)}>
                  {agent.tagline}
                </div>
                
                {/* Description */}
                <div className="text-sm text-gray-300 leading-relaxed">
                  {agent.description}
                </div>
                
                {/* Stats */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Accuracy</span>
                    <div className="flex items-center gap-1">
                      <div className="w-16 bg-gray-700 rounded-full h-1.5">
                        <div 
                          className={cn("h-1.5 rounded-full bg-emerald-500")}
                          style={{ width: `${agent.stats.accuracy}%` }}
                        />
                      </div>
                      <span className="text-emerald-400">{agent.stats.accuracy}%</span>
                    </div>
                  </div>
                  
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Speed</span>
                    <div className="flex items-center gap-1">
                      <div className="w-16 bg-gray-700 rounded-full h-1.5">
                        <div 
                          className={cn("h-1.5 rounded-full bg-cyan-500")}
                          style={{ width: `${agent.stats.speed}%` }}
                        />
                      </div>
                      <span className="text-cyan-400">{agent.stats.speed}%</span>
                    </div>
                  </div>
                  
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Reliability</span>
                    <div className="flex items-center gap-1">
                      <div className="w-16 bg-gray-700 rounded-full h-1.5">
                        <div 
                          className={cn("h-1.5 rounded-full bg-violet-500")}
                          style={{ width: `${agent.stats.reliability}%` }}
                        />
                      </div>
                      <span className="text-violet-400">{agent.stats.reliability}%</span>
                    </div>
                  </div>
                </div>
                
                {/* Capabilities (show on hover) */}
                {isHovered && (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-gray-400">
                      Capabilities:
                    </div>
                    <div className="space-y-1">
                      {agent.capabilities.slice(0, 3).map((capability, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                          <Brain className="h-3 w-3 text-cyan-400" />
                          <span>{capability}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Action button */}
                <Button
                  variant="outline"
                  size="sm"
                  className={cn(
                    "w-full transition-colors",
                    agent.borderColor,
                    agent.textColor,
                    isHovered && "bg-opacity-20"
                  )}
                >
                  {isSelected ? "Selected" : "View Details"}
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
      
      {/* Expanded details for selected agent */}
      {selectedAgent && (
        <Card className="border-cyan-500/30 bg-cyan-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-3 text-cyan-400">
              {(() => {
                const agent = AGENTS.find(a => a.id === selectedAgent);
                const Icon = agent?.icon;
                return Icon ? <Icon className="h-6 w-6" /> : null;
              })()}
              {AGENTS.find(a => a.id === selectedAgent)?.name}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-gray-300">
              {AGENTS.find(a => a.id === selectedAgent)?.details}
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {AGENTS.find(a => a.id === selectedAgent)?.capabilities.map((capability, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-cyan-300">
                  <Zap className="h-3 w-3" />
                  <span>{capability}</span>
                </div>
              ))}
            </div>
            
            <Button
              className="w-full bg-cyan-500 hover:bg-cyan-600 text-white"
              onClick={() => {
                const agent = AGENTS.find(a => a.id === selectedAgent);
                if (agent) {
                  onAgentClick?.(agent);
                }
              }}
            >
              <Play className="h-4 w-4 mr-2" />
              Watch Agent Work
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
