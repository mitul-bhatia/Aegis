"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { 
  Copy, 
  GitCompare, 
  FileText, 
  Plus, 
  Minus,
  ArrowRight,
  Eye
} from "lucide-react";

interface DiffLine {
  lineNumber: number;
  type: "context" | "added" | "removed";
  content: string;
  originalLine?: number;
  newLine?: number;
}

interface CodeDiffProps {
  before: string;
  after: string;
  filename: string;
  language?: string;
  showLineNumbers?: boolean;
  className?: string;
  viewMode?: "split" | "unified";
}

export default function CodeDiff({ 
  before, 
  after, 
  filename, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  language = "text",
  showLineNumbers = true,
  className,
  viewMode = "split"
}: CodeDiffProps) {
  const [currentViewMode, setCurrentViewMode] = useState<"split" | "unified">(viewMode);
  const [copied, setCopied] = useState(false);

  // Simple diff calculation (in production, use a proper diff library)
  const calculateDiff = (): DiffLine[] => {
    const beforeLines = before.split('\n');
    const afterLines = after.split('\n');
    const diff: DiffLine[] = [];
    
    let beforeIndex = 0;
    let afterIndex = 0;
    
    while (beforeIndex < beforeLines.length || afterIndex < afterLines.length) {
      const beforeLine = beforeLines[beforeIndex];
      const afterLine = afterLines[afterIndex];
      
      if (beforeIndex >= beforeLines.length) {
        // Line was added
        diff.push({
          lineNumber: afterIndex + 1,
          type: "added",
          content: afterLine,
          newLine: afterIndex + 1
        });
        afterIndex++;
      } else if (afterIndex >= afterLines.length) {
        // Line was removed
        diff.push({
          lineNumber: beforeIndex + 1,
          type: "removed",
          content: beforeLine,
          originalLine: beforeIndex + 1
        });
        beforeIndex++;
      } else if (beforeLine === afterLine) {
        // Context line (unchanged)
        diff.push({
          lineNumber: beforeIndex + 1,
          type: "context",
          content: beforeLine,
          originalLine: beforeIndex + 1,
          newLine: afterIndex + 1
        });
        beforeIndex++;
        afterIndex++;
      } else {
        // Line was changed (remove then add)
        diff.push({
          lineNumber: beforeIndex + 1,
          type: "removed",
          content: beforeLine,
          originalLine: beforeIndex + 1
        });
        diff.push({
          lineNumber: afterIndex + 1,
          type: "added",
          content: afterLine,
          newLine: afterIndex + 1
        });
        beforeIndex++;
        afterIndex++;
      }
    }
    
    return diff;
  };

  const diff = calculateDiff();
  const addedLines = diff.filter(line => line.type === "added").length;
  const removedLines = diff.filter(line => line.type === "removed").length;

  const handleCopy = async () => {
    try {
      const diffText = diff.map(line => {
        const prefix = line.type === "added" ? "+ " : line.type === "removed" ? "- " : "  ";
        return prefix + line.content;
      }).join('\n');
      
      await navigator.clipboard.writeText(diffText);
      setCopied(true);
      
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy diff:", err);
    }
  };

  const getLineClass = (type: string) => {
    switch (type) {
      case "added": return "bg-emerald-500/20 border-l-2 border-emerald-500";
      case "removed": return "bg-red-500/20 border-l-2 border-red-500";
      default: return "border-l-2 border-transparent";
    }
  };

  const getLinePrefix = (type: string) => {
    switch (type) {
      case "added": return <Plus className="h-3 w-3 text-emerald-400" />;
      case "removed": return <Minus className="h-3 w-3 text-red-400" />;
      default: return <span className="w-3 h-3"></span>;
    }
  };

  const renderUnifiedView = () => (
    <div className="space-y-0">
      {diff.map((line, index) => (
        <div
          key={index}
          className={cn(
            "flex items-start gap-2 py-1 px-2 font-mono text-sm transition-colors",
            getLineClass(line.type)
          )}
        >
          {showLineNumbers && (
            <div className="text-xs text-gray-500 w-8 text-right">
              {line.originalLine || line.newLine || ''}
            </div>
          )}
          
          <div className="w-3 flex justify-center">
            {getLinePrefix(line.type)}
          </div>
          
          <pre className="flex-1 text-gray-300 whitespace-pre-wrap">
            {line.content}
          </pre>
        </div>
      ))}
    </div>
  );

  const renderSplitView = () => {
    // Build aligned pairs: for each diff line, show it on the correct side with context on both
    const beforeLines: (DiffLine | null)[] = [];
    const afterLines: (DiffLine | null)[] = [];

    diff.forEach((line) => {
      if (line.type === "context") {
        beforeLines.push(line);
        afterLines.push(line);
      } else if (line.type === "removed") {
        beforeLines.push(line);
        afterLines.push(null);
      } else {
        beforeLines.push(null);
        afterLines.push(line);
      }
    });

    return (
      <div className="grid grid-cols-2 divide-x divide-gray-700">
        {/* Before */}
        <div>
          <div className="text-xs font-semibold text-red-400 px-3 py-1.5 border-b border-gray-700 bg-red-500/5">
            Before (Vulnerable)
          </div>
          {beforeLines.map((line, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 py-0.5 px-2 font-mono text-sm min-h-[24px] ${
                line?.type === "removed" ? "bg-red-500/15 border-l-2 border-red-500" : "border-l-2 border-transparent"
              }`}
            >
              {showLineNumbers && (
                <div className="text-xs text-gray-500 w-7 text-right shrink-0 select-none">
                  {line?.originalLine ?? ""}
                </div>
              )}
              <pre className={`flex-1 whitespace-pre-wrap break-all text-xs ${line?.type === "removed" ? "text-red-300" : "text-gray-400"}`}>
                {line?.content ?? ""}
              </pre>
            </div>
          ))}
        </div>

        {/* After */}
        <div>
          <div className="text-xs font-semibold text-emerald-400 px-3 py-1.5 border-b border-gray-700 bg-emerald-500/5">
            After (Patched)
          </div>
          {afterLines.map((line, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 py-0.5 px-2 font-mono text-sm min-h-[24px] ${
                line?.type === "added" ? "bg-emerald-500/15 border-l-2 border-emerald-500" : "border-l-2 border-transparent"
              }`}
            >
              {showLineNumbers && (
                <div className="text-xs text-gray-500 w-7 text-right shrink-0 select-none">
                  {line?.newLine ?? ""}
                </div>
              )}
              <pre className={`flex-1 whitespace-pre-wrap break-all text-xs ${line?.type === "added" ? "text-emerald-300" : "text-gray-400"}`}>
                {line?.content ?? ""}
              </pre>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <Card className={cn("border-gray-700 bg-gray-800/50", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="flex items-center gap-2 text-cyan-400">
              <GitCompare className="h-5 w-5" />
              Code Diff
            </CardTitle>
            
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                <FileText className="h-3 w-3 mr-1" />
                {filename}
              </Badge>
              
              <Badge variant="outline" className="text-xs border-emerald-500 text-emerald-400">
                +{addedLines}
              </Badge>
              
              <Badge variant="outline" className="text-xs border-red-500 text-red-400">
                -{removedLines}
              </Badge>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* View mode toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCurrentViewMode(currentViewMode === "split" ? "unified" : "split")}
              className="h-8 px-2 text-xs"
            >
              {currentViewMode === "split" ? "Unified" : "Split"}
            </Button>
            
            {/* Copy button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 w-8 p-0 text-gray-400 hover:text-cyan-400"
            >
              {copied ? <Eye className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="border border-gray-700 rounded-lg overflow-hidden">
          <div className="max-h-96 overflow-y-auto">
            {currentViewMode === "split" ? renderSplitView() : renderUnifiedView()}
          </div>
        </div>
        
        {/* Footer */}
        <div className="mt-3 pt-3 border-t border-gray-700 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>Total changes: {addedLines + removedLines}</span>
            <span>Lines: {diff.length}</span>
          </div>
          
          <div className="flex items-center gap-2">
            <ArrowRight className="h-3 w-3 text-cyan-400" />
            <span className="text-cyan-400">Security patch applied</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
