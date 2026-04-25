
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ScanInfo, TERMINAL_STATUSES } from "@/lib/api";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { ExploitTerminal } from "@/components/ExploitTerminal";
import { CodeDiff } from "@/components/CodeDiff";

export default function ScanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const scanId = parseInt(params.id as string);

  const [scan, setScan] = useState<ScanInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isNaN(scanId)) return;

    let isSubscribed = true;
    let sse: { close: () => void } | null = null;

    // Initial fetch
    api.getScan(scanId)
      .then(data => {
        if (!isSubscribed) return;
        setScan(data);
        setLoading(false);

        // If not terminal, connect to SSE
        if (!TERMINAL_STATUSES.includes(data.status)) {
          sse = api.connectLiveFeed((update) => {
            if (update.id === scanId) {
              setScan(prev => prev ? { ...prev, ...update } : update);
              if (TERMINAL_STATUSES.includes(update.status) && sse) {
                sse.close();
              }
            }
          });
        }
      })
      .catch(err => {
        if (!isSubscribed) return;
        console.error(err);
        setError("Failed to load scan");
        setLoading(false);
      });

    return () => {
      isSubscribed = false;
      if (sse) sse.close();
    };
  }, [scanId]);

  if (loading) return <div className="p-8 text-slate-400 font-mono">Loading...</div>;
  if (error || !scan) return <div className="p-8 text-red-400 font-mono">{error || "Not found"}</div>;

  return (
    <div className="min-h-screen bg-[#050810] text-slate-200">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <button onClick={() => router.back()} className="text-slate-500 hover:text-slate-300 font-mono text-sm mb-6 flex items-center gap-2">
          <span>←</span> Back
        </button>

        <div className="flex items-center gap-4 mb-8">
          <h1 className="text-3xl font-bold font-mono tracking-tight text-white">
            Scan #{scan.id}
          </h1>
          <span className="text-slate-500 font-mono bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
            {scan.commit_sha.substring(0, 7)}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Panel: Pipeline Timeline (35%) */}
          <div className="lg:col-span-1">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 aegis-glass">
              <h2 className="text-sm font-mono font-bold text-slate-400 mb-6 uppercase tracking-wider">
                Swarm Pipeline
              </h2>
              <PipelineTimeline
                currentAgent={scan.current_agent || null}
                status={scan.status}
                agentMessage={scan.agent_message || null}
                createdAt={scan.created_at}
              />
            </div>
          </div>

          {/* Right Panel: Content (65%) */}
          <div className="lg:col-span-2 space-y-6">
            {scan.status === "failed" && (
              <div className="bg-red-950/20 border border-red-900/50 rounded-xl p-6">
                <h3 className="text-red-400 font-mono font-bold mb-2">Pipeline Failed</h3>
                <p className="text-slate-300 text-sm">{scan.error_message}</p>
              </div>
            )}

            {scan.status === "clean" || scan.status === "false_positive" ? (
              <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-xl p-6 flex flex-col items-center justify-center text-center py-12">
                <div className="text-4xl mb-4">🛡️</div>
                <h3 className="text-emerald-400 font-mono font-bold text-lg mb-2">Code is Secure</h3>
                <p className="text-slate-400 text-sm max-w-md">
                  {scan.status === "clean"
                    ? "No vulnerabilities were detected in this commit."
                    : "Potential issues were found, but our Exploiter agent verified they are not actually exploitable (False Positives)."}
                </p>
              </div>
            ) : null}

            {scan.status === "fixed" && scan.pr_url && (
              <div className="bg-emerald-950/30 border border-emerald-500/30 rounded-xl p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-emerald-400 font-mono font-bold mb-1">Vulnerability Patched</h3>
                  <p className="text-emerald-200/60 text-sm">A pull request has been opened with the fix.</p>
                </div>
                <a href={scan.pr_url} target="_blank" rel="noopener noreferrer"
                   className="bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-bold px-4 py-2 rounded-lg text-sm transition-colors">
                  View Pull Request
                </a>
              </div>
            )}

            {(scan.exploit_output || scan.exploit_script) && (
              <div className="space-y-2">
                <h3 className="text-sm font-mono font-bold text-slate-400 uppercase tracking-wider pl-1">
                  Exploit Proof
                </h3>
                <ExploitTerminal
                  exploitOutput={scan.exploit_output || null}
                  exploitScript={scan.exploit_script || null}
                />
              </div>
            )}

            {(scan.original_code || scan.patch_diff) && (
              <div className="space-y-2">
                <h3 className="text-sm font-mono font-bold text-slate-400 uppercase tracking-wider pl-1 flex justify-between items-center">
                  <span>Remediation Diff</span>
                  {scan.patch_attempts ? (
                    <span className="text-xs bg-slate-800 text-amber-400 px-2 py-0.5 rounded-full lowercase">
                      {scan.patch_attempts} attempt(s)
                    </span>
                  ) : null}
                </h3>
                <CodeDiff
                  originalCode={scan.original_code || null}
                  patchedCode={scan.patch_diff || null}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
