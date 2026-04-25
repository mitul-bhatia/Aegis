"use client";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Props {
  originalCode: string | null;
  patchedCode: string | null;
  language?: string;
}

export function CodeDiff({ originalCode, patchedCode, language = "python" }: Props) {
  if (!originalCode && !patchedCode) return null;

  return (
    <div className="grid grid-cols-2 gap-2 rounded-xl overflow-hidden border border-slate-700">
      <div>
        <div className="bg-red-950/30 border-b border-red-900/30 px-3 py-1.5">
          <span className="text-xs font-mono text-red-400">− before (vulnerable)</span>
        </div>
        <div className="max-h-72 overflow-y-auto bg-red-950/10">
          {originalCode ? (
            <SyntaxHighlighter language={language} style={vscDarkPlus}
                               customStyle={{ background: "transparent", fontSize: "11px", margin: 0 }}>
              {originalCode}
            </SyntaxHighlighter>
          ) : (
            <div className="p-4 text-xs text-slate-600 font-mono">No original code recorded</div>
          )}
        </div>
      </div>
      <div>
        <div className="bg-emerald-950/30 border-b border-emerald-900/30 px-3 py-1.5">
          <span className="text-xs font-mono text-emerald-400">+ after (patched)</span>
        </div>
        <div className="max-h-72 overflow-y-auto bg-emerald-950/10">
          {patchedCode ? (
            <SyntaxHighlighter language={language} style={vscDarkPlus}
                               customStyle={{ background: "transparent", fontSize: "11px", margin: 0 }}>
              {patchedCode}
            </SyntaxHighlighter>
          ) : (
            <div className="p-4 text-xs text-slate-600 font-mono">No patched code recorded</div>
          )}
        </div>
      </div>
    </div>
  );
}
