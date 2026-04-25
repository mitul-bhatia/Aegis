"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, GitBranch, Search, Crosshair, Wrench, ShieldCheck, GitPullRequest, CheckCircle2, ArrowRight } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SwarmTerminal } from "@/components/SwarmTerminal";
import { api } from "@/lib/api";

const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || "";

// ── Data ────────────────────────────────────────────────────
const AGENTS = [
  {
    id: "A", color: "var(--red)", label: "The Finder",
    role: "Exploit Generation",
    icon: "⚡",
    desc: "Analyzes every commit diff using Semgrep + RAG semantic search. Identifies SQL injection, XSS, path traversal, and 40+ CVE patterns — ranked by severity.",
    model: "llama-3.3-70b-versatile + Semgrep",
  },
  {
    id: "B", color: "var(--blue)", label: "The Engineer",
    role: "Secure Patch Generation",
    icon: "⚙",
    desc: "Given a confirmed exploit, rewrites the vulnerable section using CWE-specific fix patterns. Respects code style, generates test cases, retries up to 3×.",
    model: "devstral-small-2505",
  },
  {
    id: "C", color: "var(--amber)", label: "The Verifier",
    role: "Patch Validation Gate",
    icon: "✓",
    desc: "Runs the full test suite, re-executes the original exploit against patched code, and scans for regressions. The final quality gate before any PR is opened.",
    model: "llama-3.3-70b-versatile + Sandbox",
  },
  {
    id: "D", color: "var(--agent-finder)", label: "The Exploiter",
    role: "Sandbox Proof-of-Concept",
    icon: "◎",
    desc: "Generates and runs a real exploit script in an isolated Docker sandbox — no network, 256MB cap. If it can't crash your app, it's not a real vulnerability.",
    model: "llama-3.3-70b-versatile + Docker",
  },
];

const PIPELINE_NODES = [
  { label: "Trigger", name: "GitHub Webhook", color: "var(--muted)" },
  { label: "Supervisor", name: "LangGraph", color: "var(--blue)" },
  { label: "Agent A", name: "Exploit Gen", color: "var(--red)" },
  { label: "Agent B", name: "Patch Engineer", color: "var(--blue)" },
  { label: "Agent C", name: "Sandbox Review", color: "var(--amber)" },
  { label: "Output", name: "Auto-Merge PR", color: "var(--agent-verifier)" },
];

const STATS = [
  { num: "86", suffix: "%", label: "False Positive Rate (Industry Baseline)", bg: "!" },
  { num: "50", suffix: "%+", label: "Target TP Rate (Post Fine-Tune)", bg: "✓" },
  { num: "3", suffix: "", label: "Max Retry Attempts Before Escalation", bg: "#" },
  { num: "$10", suffix: "", label: "Hard Cost Budget Per Commit", bg: "$" },
];

const HERO_METRICS = [
  { num: "71", suffix: "%", label: "Patch Correctness (AIxCC)" },
  { num: "45", suffix: "m", label: "Avg Remediation Time" },
  { num: "$152", suffix: "", label: "Cost Per Task" },
  { num: "54M", suffix: "", label: "Lines of Code Processed" },
];

const STACK = [
  {
    title: "Prompt Injection Defense", tag: "Critical", tagColor: "var(--agent-verifier)", tagBg: "var(--green-dim)",
    items: [
      { ok: true, bold: "Document blocks", rest: "— untrusted code diff isolated from instructions structurally" },
      { ok: true, bold: "Append-only audit log", rest: "→ SOC 2 evidence trail" },
      { ok: true, bold: "Signed tool definitions", rest: "— prevents tool poisoning via repo" },
      { ok: true, bold: "Input sanitisation", rest: "— all LLM inputs scrubbed before prompt injection" },
    ],
  },
  {
    title: "Sandbox Isolation", tag: "High Risk", tagColor: "var(--red)", tagBg: "var(--red-dim)",
    items: [
      { ok: true, bold: "Docker container", rest: "(dev) — 30s timeout, 256MB cap, no network" },
      { ok: true, bold: "cap_drop ALL", rest: "+ pids_limit 50 + non-root user" },
      { ok: true, bold: "Exploit-only: stdlib + requests", rest: "— pre-validated before sandbox" },
      { ok: false, bold: "Firecracker microVMs", rest: "(prod) — hardware-level isolation (WIP)" },
    ],
  },
  {
    title: "Patch Validation", tag: "Multi-Layer", tagColor: "var(--blue)", tagBg: "var(--blue-dim)",
    items: [
      { ok: true, bold: "Semgrep security-audit", rest: "on every patch diff before merge" },
      { ok: true, bold: "OSV scanner", rest: "on all new dependencies introduced by patch" },
      { ok: true, bold: "50-line surface area cap", rest: "— larger patches require human approval" },
      { ok: false, bold: "Semantic equivalence", rest: "— differential fuzzing on 10K inputs (WIP)" },
    ],
  },
  {
    title: "MCP Hardening", tag: "Protocol-Level", tagColor: "var(--amber)", tagBg: "var(--amber-dim)",
    items: [
      { ok: true, bold: "Mutual TLS + DPoP tokens", rest: "(300s TTL) — all gateway traffic" },
      { ok: true, bold: "Per-agent RBAC", rest: "— Engineer cannot merge; only writes PR drafts" },
      { ok: true, bold: "OpenTelemetry traces", rest: "on 100% of tool calls — anomaly alerting" },
      { ok: true, bold: "HashiCorp Vault", rest: "dynamic secrets — 24-hour TTL API key rotation" },
    ],
  },
];

// ── Sub-components ────────────────────────────────────────

function Mono({ children, className = "", style = {} }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <span className={className} style={{ fontFamily: "var(--font-share-tech-mono, monospace)", ...style }}>
      {children}
    </span>
  );
}

function PipelineDemo() {
  const [activeIdx, setActiveIdx] = useState(0);
  const [completed, setCompleted] = useState<number[]>([]);
  useEffect(() => {
    const id = setInterval(() => {
      setActiveIdx((prev) => {
        const next = (prev + 1) % 5;
        if (next === 0) setCompleted([]);
        else setCompleted((c) => [...c, prev]);
        return next;
      });
    }, 1600);
    return () => clearInterval(id);
  }, []);

  const stages = [
    { label: "Finder", color: "var(--agent-finder)", output: "Found SQL Injection in db.py:42 · HIGH" },
    { label: "Exploiter", color: "var(--red)", output: "EXPLOIT_SUCCESS · Database dump confirmed · CRITICAL" },
    { label: "Engineer", color: "var(--blue)", output: "Parameterized query applied · 3 lines changed" },
    { label: "Verifier", color: "var(--agent-verifier)", output: "Exploit FAILED on patch ✓ · 47/47 tests passed" },
    { label: "PR #47", color: "var(--green)", output: "Pull request opened · Ready for review" },
  ];

  return (
    <div style={{ border: "1px solid var(--border)", background: "var(--surface)", padding: "24px 20px" }}>
      <Mono style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase", display: "block", textAlign: "center", marginBottom: 20 }}>
        Live Demo — Auto-playing
      </Mono>
      <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
        {stages.map((s, i) => {
          const isActive = i === activeIdx;
          const isDone = completed.includes(i);
          return (
            <div key={s.label} style={{ display: "flex", alignItems: "center", flex: 1 }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: "50%", border: `1px solid ${isActive || isDone ? s.color : "var(--border)"}`,
                  background: isActive || isDone ? `${s.color}18` : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  position: "relative",
                  boxShadow: isActive ? `0 0 12px ${s.color}40` : "none",
                  transition: "all 0.4s",
                }}>
                  {isDone
                    ? <span style={{ color: s.color, fontSize: 14 }}>✓</span>
                    : <span style={{ color: isActive ? s.color : "var(--border)", fontSize: 12 }}>●</span>}
                  {isActive && <span style={{ position: "absolute", inset: -4, borderRadius: "50%", border: `1px solid ${s.color}`, animation: "pulse-ring 1.8s ease-out infinite" }} />}
                </div>
                <Mono style={{ fontSize: 10, color: isActive ? s.color : "var(--muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                  {s.label}
                </Mono>
              </div>
              {i < stages.length - 1 && (
                <div style={{ height: 1, width: 24, flexShrink: 0, background: isDone ? s.color : "var(--border)", transition: "background 0.4s" }} />
              )}
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 20, padding: "8px 14px", border: "1px solid var(--border)", background: "var(--card)" }}>
        <Mono style={{ fontSize: 11, color: stages[activeIdx].color }}>
          <span style={{ color: "var(--muted)" }}>▶ </span>{stages[activeIdx].output}
        </Mono>
      </div>
    </div>
  );
}

export { AGENTS, PIPELINE_NODES, STATS, HERO_METRICS, STACK, Mono, PipelineDemo };
