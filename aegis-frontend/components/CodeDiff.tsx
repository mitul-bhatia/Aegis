"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { 
  Copy, 
  GitCompare, 
  FileText, 
  Eye,
  Columns2,
  AlignJustify,
  Shield,
} from "lucide-react";

// Dynamically import ReactDiffViewer to avoid SSR issues
const ReactDiffViewer = dynamic(
  () => import("react-diff-viewer-continued"),
  { ssr: false }
);

// Import DiffMethod enum
import { DiffMethod } from "react-diff-viewer-continued";

interface CodeDiffProps {
  before: string;
  after: string;
  filename: string;
  language?: string;
  className?: string;
}

export default function CodeDiff({ 
  before, 
  after, 
  filename, 
  language = "python",
  className,
}: CodeDiffProps) {
  const [viewMode, setViewMode] = useState<"split" | "unified">("split");
  const [copied, setCopied] = useState(false);

  // Calculate stats
  const beforeLines = before.split('\n');
  const afterLines = after.split('\n');
  const addedLines = afterLines.filter((line, i) => !beforeLines.includes(line)).length;
  const removedLines = beforeLines.filter((line, i) => !afterLines.includes(line)).length;

  async function handleCopy() {
    try {
      const diffText = `--- ${filename} (before)\n+++ ${filename} (after)\n\n${before}\n---\n${after}`;
      await navigator.clipboard.writeText(diffText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy diff:", err);
    }
  }

  // Custom dark theme styles for the diff viewer
  const customStyles = {
    variables: {
      dark: {
        diffViewerBackground: '#000000',
        diffViewerColor: '#e5e5e5',
        addedBackground: '#0d3a1a',
        addedColor: '#86efac',
        removedBackground: '#3a0d0d',
        removedColor: '#fca5a5',
        wordAddedBackground: '#166534',
        wordRemovedBackground: '#7f1d1d',
        addedGutterBackground: '#0f2e1a',
        removedGutterBackground: '#2e0f0f',
        gutterBackground: '#000000',
        gutterBackgroundDark: '#050505',
        highlightBackground: '#1e293b',
        highlightGutterBackground: '#1e293b',
        codeFoldGutterBackground: '#000000',
        codeFoldBackground: '#000000',
        emptyLineBackground: '#000000',
        gutterColor: '#71717a',
        addedGutterColor: '#4ade80',
        removedGutterColor: '#f87171',
        codeFoldContentColor: '#71717a',
        diffViewerTitleBackground: '#050505',
        diffViewerTitleColor: '#e5e5e5',
        diffViewerTitleBorderColor: '#27272a',
      },
    },
    line: {
      padding: '2px 8px',
      fontSize: '12px',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      lineHeight: '1.5',
    },
    gutter: {
      padding: '0 8px',
      minWidth: '40px',
      fontSize: '11px',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    },
    marker: {
      padding: '0 4px',
    },
    contentText: {
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      fontSize: '12px',
    },
  };

  return (
    <div className={cn("rounded-md overflow-hidden border border-border/50 bg-black shadow-2xl", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-white/5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-cyan-400" />
            <span className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">Security Patch</span>
          </div>
          
          <div className="h-4 w-px bg-border/50" />
          
          <Badge variant="outline" className="text-xs border-border/50 bg-black">
            <FileText className="h-3 w-3 mr-1" />
            {filename}
          </Badge>
          
          <Badge variant="outline" className="text-xs border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
            +{addedLines}
          </Badge>
          
          <Badge variant="outline" className="text-xs border-red-500/30 text-red-400 bg-red-500/10">
            -{removedLines}
          </Badge>
        </div>
        
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center gap-1 rounded-md border border-border/50 bg-background/50 p-0.5">
            <Button
              variant={viewMode === "split" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("split")}
              className="h-6 px-2 text-xs"
            >
              <Columns2 className="h-3 w-3 mr-1" />
              Split
            </Button>
            <Button
              variant={viewMode === "unified" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("unified")}
              className="h-6 px-2 text-xs"
            >
              <AlignJustify className="h-3 w-3 mr-1" />
              Unified
            </Button>
          </div>
          
          {/* Copy button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-cyan-400"
          >
            {copied ? <Eye className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>
      
      {/* Diff viewer */}
      <div className="diff-viewer-container">
        <ReactDiffViewer
          oldValue={before}
          newValue={after}
          splitView={viewMode === "split"}
          useDarkTheme={true}
          compareMethod={DiffMethod.WORDS}
          styles={customStyles}
          leftTitle="Before (Vulnerable)"
          rightTitle="After (Patched)"
          hideLineNumbers={false}
          showDiffOnly={false}
        />
      </div>
      
      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2.5 border-t border-border/50 bg-white/5 text-xs text-muted-foreground">
        <div className="flex items-center gap-4 font-mono">
          <span>Total changes: {addedLines + removedLines}</span>
          <span>Language: {language}</span>
        </div>
        
        <div className="flex items-center gap-2 text-emerald-400 font-medium">
          <Shield className="h-3.5 w-3.5" />
          <span>Vulnerability Patched</span>
        </div>
      </div>
      
      {/* Custom CSS for the diff viewer */}
      <style jsx global>{`
        .diff-viewer-container {
          max-height: 500px;
          overflow-y: auto;
          background: #000000;
        }
        
        .diff-viewer-container::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        .diff-viewer-container::-webkit-scrollbar-track {
          background: #000000;
        }
        
        .diff-viewer-container::-webkit-scrollbar-thumb {
          background: #27272a;
          border-radius: 4px;
        }
        
        .diff-viewer-container::-webkit-scrollbar-thumb:hover {
          background: #3f3f46;
        }
        
        /* Override some default styles */
        .diff-viewer-container table {
          border-collapse: collapse;
          width: 100%;
        }
        
        .diff-viewer-container pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-all;
        }
      `}</style>
    </div>
  );
}
