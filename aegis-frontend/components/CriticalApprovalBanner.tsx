"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle2, XCircle, Shield, Loader2 } from "lucide-react";
import type { ScanInfo } from "@/lib/api";
import ExploitTerminal from "./ExploitTerminal";
import CodeDiff from "./CodeDiff";

interface CriticalApprovalBannerProps {
  scan: ScanInfo;
  onApprove: () => Promise<void>;
  onReject: (reason: string) => Promise<void>;
}

export function CriticalApprovalBanner({ scan, onApprove, onReject }: CriticalApprovalBannerProps) {
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  async function handleApprove() {
    setApproving(true);
    try {
      await onApprove();
    } catch (err) {
      console.error("Approval failed:", err);
      alert("Failed to approve patch. Please try again.");
    } finally {
      setApproving(false);
    }
  }

  async function handleReject() {
    if (!showRejectInput) {
      setShowRejectInput(true);
      return;
    }

    setRejecting(true);
    try {
      await onReject(rejectReason);
    } catch (err) {
      console.error("Rejection failed:", err);
      alert("Failed to reject patch. Please try again.");
    } finally {
      setRejecting(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Alert banner */}
      <div className="border-2 border-amber-500/50 bg-amber-500/5 rounded-xl p-6 aegis-glow-amber">
        <div className="flex items-start gap-4 mb-4">
          <div className="h-12 w-12 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
            <AlertTriangle className="h-6 w-6 text-amber-400" />
          </div>
          <div className="flex-1">
            <p className="font-bold text-amber-300 text-lg mb-1">
              Critical Vulnerability — Human Approval Required
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Aegis found and patched a <span className="text-amber-400 font-semibold">{scan.vulnerability_type}</span> vulnerability
              {scan.vulnerable_file && (
                <> in <code className="text-primary font-mono text-xs">{scan.vulnerable_file}</code></>
              )}.
              Please review the exploit proof and patch below before approving the PR creation.
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-col gap-3">
          {!showRejectInput ? (
            <div className="flex gap-3">
              <Button
                onClick={handleApprove}
                disabled={approving || rejecting}
                className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-black font-semibold h-11 text-base aegis-glow-emerald"
              >
                {approving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Approving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Approve & Create PR
                  </>
                )}
              </Button>
              <Button
                onClick={handleReject}
                disabled={approving || rejecting}
                variant="outline"
                className="flex-1 text-red-400 border-red-500/30 hover:bg-red-500/10 h-11 text-base"
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject Patch
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">
                  Rejection reason (optional)
                </label>
                <input
                  type="text"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="e.g., Patch breaks existing functionality"
                  className="w-full px-3 py-2 rounded-md border border-border/50 bg-background/50 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50"
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={handleReject}
                  disabled={rejecting}
                  variant="destructive"
                  className="flex-1 h-10"
                >
                  {rejecting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Rejecting...
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 mr-2" />
                      Confirm Rejection
                    </>
                  )}
                </Button>
                <Button
                  onClick={() => {
                    setShowRejectInput(false);
                    setRejectReason("");
                  }}
                  disabled={rejecting}
                  variant="ghost"
                  className="flex-1 h-10"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Exploit proof */}
      {scan.exploit_output && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Exploit Proof
          </h3>
          <ExploitTerminal
            output={scan.exploit_output}
            exploitScript={scan.exploit_script}
            status="vulnerable"
            title="Exploit Confirmed — Docker Sandbox"
          />
        </div>
      )}

      {/* Patch diff */}
      {scan.original_code && scan.patch_diff && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Proposed Patch
          </h3>
          <CodeDiff
            before={scan.original_code}
            after={scan.patch_diff}
            filename={scan.vulnerable_file ?? "patch"}
            language="python"
          />
        </div>
      )}
    </div>
  );
}
