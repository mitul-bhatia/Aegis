"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Search,
  Crosshair,
  Wrench,
  ShieldCheck,
  ArrowRight,
  GitBranch,
  CheckCircle2,
  Zap,
  Lock,
  GitPullRequest,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || "";

// ── Agent config ──────────────────────────────────────────
const AGENTS = [
  {
    id: "finder",
    icon: Search,
    label: "The Finder",
    tagline: "Reads every changed line. Finds what humans miss.",
    detail:
      "Combines Semgrep static analysis + RAG semantic search to identify SQL injection, XSS, path traversal, and 40+ CVE patterns — then ranks them by severity.",
    color: "violet",
    colorClasses: {
      border: "border-violet-500/25",
      borderHover: "group-hover:border-violet-500/60",
      bg: "bg-violet-500/10",
      icon: "text-violet-400",
      text: "text-violet-300",
      glow: "group-hover:shadow-[0_0_30px_oklch(0.70_0.18_285/0.15)]",
    },
  },
  {
    id: "exploiter",
    icon: Crosshair,
    label: "The Exploiter",
    tagline: "Doesn't guess. Writes code that proves it.",
    detail:
      "Generates and runs a real exploit script in an isolated Docker sandbox with no network access. If it can't crash your app, it's not a real vulnerability.",
    color: "red",
    colorClasses: {
      border: "border-red-500/25",
      borderHover: "group-hover:border-red-500/60",
      bg: "bg-red-500/10",
      icon: "text-red-400",
      text: "text-red-300",
      glow: "group-hover:shadow-[0_0_30px_oklch(0.65_0.22_25/0.15)]",
    },
  },
  {
    id: "engineer",
    icon: Wrench,
    label: "The Engineer",
    tagline: "Fixes the root cause, not the symptom.",
    detail:
      "Rewrites the vulnerable function with a secure implementation, respects your code style, and generates test cases to verify the fix before shipping.",
    color: "amber",
    colorClasses: {
      border: "border-amber-500/25",
      borderHover: "group-hover:border-amber-500/60",
      bg: "bg-amber-500/10",
      icon: "text-amber-400",
      text: "text-amber-300",
      glow: "group-hover:shadow-[0_0_30px_oklch(0.80_0.16_75/0.15)]",
    },
  },
  {
    id: "verifier",
    icon: ShieldCheck,
    label: "The Verifier",
    tagline: "Tries to break its own patch. If it can't, it ships.",
    detail:
      "Re-runs the original exploit + full unit test suite against the patched code. Loops back to the Engineer up to 3× if anything fails. Only opens a PR when it's certain.",
    color: "emerald",
    colorClasses: {
      border: "border-emerald-500/25",
      borderHover: "group-hover:border-emerald-500/60",
      bg: "bg-emerald-500/10",
      icon: "text-emerald-400",
      text: "text-emerald-300",
      glow: "group-hover:shadow-[0_0_30px_oklch(0.74_0.16_155/0.15)]",
    },
  },
];

// ── Pipeline demo stages ──────────────────────────────────
const PIPELINE_STAGES = [
  {
    icon: Search,
    label: "Finder",
    color: "text-violet-400",
    borderColor: "border-violet-500",
    bgColor: "bg-violet-500/15",
    glowColor: "shadow-[0_0_12px_oklch(0.70_0.18_285/0.4)]",
    output: "Found SQL Injection in db.py:42 · Severity: HIGH",
  },
  {
    icon: Crosshair,
    label: "Exploiter",
    color: "text-red-400",
    borderColor: "border-red-500",
    bgColor: "bg-red-500/15",
    glowColor: "shadow-[0_0_12px_oklch(0.65_0.22_25/0.4)]",
    output: "HTTP 500 · Database dump confirmed · VULNERABLE",
  },
  {
    icon: Wrench,
    label: "Engineer",
    color: "text-amber-400",
    borderColor: "border-amber-500",
    bgColor: "bg-amber-500/15",
    glowColor: "shadow-[0_0_12px_oklch(0.80_0.16_75/0.4)]",
    output: "Parameterized query applied · 3 lines changed",
  },
  {
    icon: ShieldCheck,
    label: "Verifier",
    color: "text-emerald-400",
    borderColor: "border-emerald-500",
    bgColor: "bg-emerald-500/15",
    glowColor: "shadow-[0_0_12px_oklch(0.74_0.16_155/0.4)]",
    output: "Exploit failed · Tests passing · Patch confirmed",
  },
  {
    icon: GitPullRequest,
    label: "PR Opened",
    color: "text-primary",
    borderColor: "border-primary",
    bgColor: "bg-primary/15",
    glowColor: "shadow-[0_0_12px_oklch(0.78_0.14_195/0.4)]",
    output: "PR #47 created · Ready for your review",
  },
];

// ── Stats ─────────────────────────────────────────────────
const STATS = [
  { value: "1,247", label: "Vulnerabilities Found", icon: Lock },
  { value: "891",   label: "Patches Generated",     icon: Wrench },
  { value: "891",   label: "PRs Opened",            icon: GitPullRequest },
  { value: "14.2s", label: "Avg. Fix Time",         icon: Zap },
];

// ── Components ────────────────────────────────────────────

function PipelineDemo() {
  const [activeIdx, setActiveIdx] = useState(0);
  const [completed, setCompleted] = useState<number[]>([]);

  useEffect(() => {
    const cycle = () => {
      setActiveIdx((prev) => {
        const next = (prev + 1) % PIPELINE_STAGES.length;
        if (next === 0) {
          setCompleted([]);
        } else {
          setCompleted((c) => [...c, prev]);
        }
        return next;
      });
    };
    const interval = setInterval(cycle, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/40 bg-card/50 p-6 backdrop-blur-sm">
      <p className="mb-6 text-center text-xs font-medium uppercase tracking-widest text-muted-foreground">
        Live Demo — Auto-playing
      </p>

      {/* Pipeline nodes */}
      <div className="flex items-center justify-between gap-2">
        {PIPELINE_STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const isActive = idx === activeIdx;
          const isDone = completed.includes(idx);

          return (
            <div key={stage.label} className="flex flex-1 items-center">
              <div className="flex flex-col items-center gap-2 flex-1">
                <div
                  className={`relative flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-500 ${
                    isActive
                      ? `${stage.bgColor} ${stage.borderColor} ${stage.glowColor} scale-110`
                      : isDone
                      ? `${stage.bgColor} ${stage.borderColor} opacity-70`
                      : "bg-white/3 border-white/10 opacity-30"
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className={`h-4 w-4 ${stage.color}`} />
                  ) : (
                    <Icon
                      className={`h-4 w-4 ${stage.color} ${isActive ? "animate-pulse" : ""}`}
                    />
                  )}
                  {isActive && (
                    <span
                      className={`absolute inset-0 rounded-full border ${stage.borderColor} opacity-0 animate-[pulse-ring_1.8s_ease-out_infinite]`}
                    />
                  )}
                </div>
                <span className={`text-xs font-medium ${isActive ? stage.color : "text-muted-foreground"}`}>
                  {stage.label}
                </span>
              </div>

              {/* Connector */}
              {idx < PIPELINE_STAGES.length - 1 && (
                <div className="relative h-px flex-1 mx-1">
                  <div className="absolute inset-0 bg-white/8" />
                  {isDone && (
                    <div
                      className={`pipeline-fill absolute inset-0 ${stage.borderColor.replace("border-", "bg-")} opacity-60`}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Active stage output */}
      <div className="mt-6 min-h-[36px] rounded-lg border border-border/30 bg-background/40 px-4 py-2">
        <p className={`text-xs font-mono ${PIPELINE_STAGES[activeIdx].color}`}>
          <span className="text-muted-foreground">▶ </span>
          {PIPELINE_STAGES[activeIdx].output}
        </p>
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: typeof AGENTS[0] }) {
  const Icon = agent.icon;
  const c = agent.colorClasses;
  return (
    <div
      className={`group animate-agent-appear relative overflow-hidden rounded-2xl border ${c.border} ${c.borderHover} ${c.glow} bg-card/60 p-5 backdrop-blur-sm transition-all duration-300`}
    >
      {/* Left accent bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-0.5 ${c.bg.replace("/10", "/60")}`} />

      <div className="flex items-start gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${c.bg} ${c.border} border`}>
          <Icon className={`h-4.5 w-4.5 ${c.icon}`} strokeWidth={1.8} />
        </div>
        <div>
          <h3 className={`font-semibold text-sm ${c.text}`}>{agent.label}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">{agent.tagline}</p>
        </div>
      </div>

      {/* Detail revealed on hover */}
      <div className="mt-3 overflow-hidden max-h-0 group-hover:max-h-20 transition-all duration-300 ease-out">
        <p className="text-xs text-muted-foreground/80 leading-relaxed border-t border-border/30 pt-3">
          {agent.detail}
        </p>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────
export default function LandingPage() {
  const router = useRouter();

  // Check if already logged in
  useEffect(() => {
    const uid = localStorage.getItem("aegis_user_id");
    if (uid) router.replace("/dashboard");
  }, [router]);

  function handleLogin() {
    const redirectUri = `${window.location.origin}/auth/callback`;
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=repo,write:repo_hook&redirect_uri=${redirectUri}`;
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 aegis-grid-pattern opacity-40" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-background/30 to-background" />

      {/* Orbs */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-primary/6 blur-[120px]" />
      <div className="pointer-events-none absolute top-1/2 -left-40 h-[400px] w-[400px] rounded-full bg-violet-500/5 blur-[100px]" />
      <div className="pointer-events-none absolute top-1/2 -right-40 h-[400px] w-[400px] rounded-full bg-red-500/5 blur-[100px]" />

      <main className="relative mx-auto max-w-5xl px-6 pb-24">

        {/* ── Nav ── */}
        <nav className="flex items-center justify-between py-6">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" strokeWidth={1.8} />
            <span className="text-lg font-bold">Aegis</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="gap-2 text-muted-foreground hover:text-foreground"
            onClick={handleLogin}
          >
            <GitBranch className="h-4 w-4" />
            Sign in
          </Button>
        </nav>

        {/* ── Hero ── */}
        <section className="py-16 text-center">
          {/* Shield */}
          <div className="relative mx-auto mb-8 flex h-24 w-24 items-center justify-center">
            <span className="absolute inset-0 rounded-full border border-primary/20 animate-[pulse-ring_3s_ease-out_infinite]" />
            <span className="absolute inset-[-12px] rounded-full border border-primary/10 animate-[pulse-ring_3s_ease-out_infinite_0.6s]" />
            <div className="relative flex h-24 w-24 items-center justify-center rounded-full border border-primary/30 bg-primary/10 aegis-glow">
              <Shield className="h-12 w-12 text-primary" strokeWidth={1.5} />
            </div>
          </div>

          <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl md:text-[3.5rem]">
            Your Code Gets a{" "}
            <span className="aegis-gradient-text">Security Team</span>
            <br />on Every Push
          </h1>

          <p className="mx-auto mt-5 max-w-2xl text-base text-muted-foreground leading-relaxed">
            Four AI agents — a{" "}
            <span className="text-violet-400 font-medium">Finder</span>,{" "}
            <span className="text-red-400 font-medium">Exploiter</span>,{" "}
            <span className="text-amber-400 font-medium">Engineer</span>, and{" "}
            <span className="text-emerald-400 font-medium">Verifier</span> — find every vulnerability,
            prove it with a real exploit, patch it, and open a PR.{" "}
            <span className="text-foreground font-medium">Automatically.</span>
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button
              size="lg"
              onClick={handleLogin}
              className="aegis-btn-shimmer aegis-glow gap-2.5 px-7 py-3 text-base font-semibold"
            >
              <GitBranch className="h-5 w-5" />
              Connect GitHub and Start
              <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-xs text-muted-foreground">Free · No credit card · Instant setup</p>
          </div>
        </section>

        {/* ── Pipeline Demo ── */}
        <section className="py-8">
          <p className="mb-4 text-center text-sm font-medium text-muted-foreground">
            Watch a vulnerability get found, proven, and fixed →
          </p>
          <PipelineDemo />
        </section>

        {/* ── Agent Showcase ── */}
        <section className="py-12">
          <div className="mb-8 text-center">
            <h2 className="text-2xl font-bold">Meet Your AI Security Swarm</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Four specialized agents. One automated mission.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {AGENTS.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        </section>

        {/* ── Stats Bar ── */}
        <section className="py-8">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {STATS.map((stat) => {
              const Icon = stat.icon;
              return (
                <div key={stat.label} className="aegis-glass rounded-xl p-4 text-center">
                  <Icon className="mx-auto mb-2 h-5 w-5 text-primary opacity-60" strokeWidth={1.6} />
                  <p className="text-2xl font-bold tabular-nums aegis-gradient-text">{stat.value}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{stat.label}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── How it works ── */}
        <section className="py-8">
          <h2 className="mb-6 text-center text-2xl font-bold">Zero config. Maximum security.</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              {
                step: "01",
                title: "Connect your repo",
                desc: "Paste a GitHub URL. Aegis installs a webhook and indexes your codebase in seconds.",
              },
              {
                step: "02",
                title: "Push your code",
                desc: "Every commit triggers the four-agent pipeline automatically. No commands to run.",
              },
              {
                step: "03",
                title: "Review the PR",
                desc: "A pull request with a verified, tested security patch is waiting for your approval.",
              },
            ].map(({ step, title, desc }) => (
              <div key={step} className="aegis-glass rounded-xl p-5">
                <span className="text-3xl font-black text-primary/20">{step}</span>
                <h3 className="mt-2 font-semibold">{title}</h3>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Bottom CTA ── */}
        <section className="py-12 text-center">
          <div className="aegis-gradient-border rounded-2xl p-px">
            <div className="rounded-2xl bg-card/80 px-8 py-10 backdrop-blur-sm">
              <h2 className="text-2xl font-bold">Ready to automate your security?</h2>
              <p className="mt-2 text-muted-foreground text-sm">
                Connect your first repo and watch the agents work.
              </p>
              <Button
                size="lg"
                onClick={handleLogin}
                className="mt-6 aegis-btn-shimmer aegis-glow gap-2.5 px-8 font-semibold"
              >
                <GitBranch className="h-5 w-5" />
                Get Started Free
              </Button>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
