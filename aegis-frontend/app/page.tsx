"use client";

import { Button } from "@/components/ui/button";
import { Shield, Zap, GitPullRequest, Bug, Lock, ArrowRight } from "lucide-react";

const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || "";
const GITHUB_OAUTH_URL = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=repo,admin:repo_hook`;

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="group relative rounded-xl border border-border/50 bg-card/50 p-6 backdrop-blur-sm aegis-card-hover">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
        <Icon className="h-6 w-6 text-primary" />
      </div>
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

function PipelineStep({
  step,
  title,
  description,
  isLast,
}: {
  step: number;
  title: string;
  description: string;
  isLast?: boolean;
}) {
  return (
    <div className="flex items-start gap-4">
      <div className="flex flex-col items-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-primary bg-primary/10 text-sm font-bold text-primary">
          {step}
        </div>
        {!isLast && <div className="mt-2 h-12 w-px bg-border" />}
      </div>
      <div className="pb-8">
        <p className="font-semibold">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

export default function LandingPage() {
  // Check if user is already logged in
  const userId =
    typeof window !== "undefined" ? localStorage.getItem("aegis_user_id") : null;

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background grid pattern */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-5 md:px-12">
        <div className="flex items-center gap-2">
          <Shield className="h-7 w-7 text-primary" />
          <span className="text-xl font-bold tracking-tight">Aegis</span>
        </div>
        {userId ? (
          <Button asChild>
            <a href="/dashboard">Dashboard <ArrowRight className="ml-2 h-4 w-4" /></a>
          </Button>
        ) : (
          <Button asChild>
            <a href={GITHUB_OAUTH_URL}>Sign in with GitHub</a>
          </Button>
        )}
      </nav>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 pt-20 text-center md:pt-32">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
          <Zap className="h-3.5 w-3.5" />
          Autonomous white-hat security
        </div>

        <h1 className="mb-6 text-4xl font-extrabold tracking-tight md:text-6xl">
          Find, exploit, and fix <br />
          <span className="aegis-gradient-text">vulnerabilities automatically</span>
        </h1>

        <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground leading-relaxed">
          Aegis monitors your GitHub repos. On every commit, it scans for
          security bugs, proves they&apos;re exploitable in a sandbox, patches them,
          and opens a PR — all without human intervention.
        </p>

        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          {userId ? (
            <Button size="lg" className="aegis-glow" asChild>
              <a href="/dashboard">
                Go to Dashboard <ArrowRight className="ml-2 h-4 w-4" />
              </a>
            </Button>
          ) : (
            <Button size="lg" className="aegis-glow" asChild>
              <a href={GITHUB_OAUTH_URL}>
                Get Started with GitHub <ArrowRight className="ml-2 h-4 w-4" />
              </a>
            </Button>
          )}
        </div>
      </section>

      {/* Features */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-28">
        <div className="grid gap-6 md:grid-cols-3">
          <FeatureCard
            icon={Bug}
            title="Detect & Exploit"
            description="Semgrep finds potential vulnerabilities. Our AI hacker agent writes a real exploit and runs it in an isolated Docker sandbox to prove it's real."
          />
          <FeatureCard
            icon={Lock}
            title="Patch & Verify"
            description="An AI engineer agent writes a security patch. The exploit is re-run against the patched code — if it fails, the fix is confirmed."
          />
          <FeatureCard
            icon={GitPullRequest}
            title="PR with Proof"
            description="Aegis opens a GitHub PR containing the patch, exploit proof, and remediation details. Review and merge — done."
          />
        </div>
      </section>

      {/* How it works */}
      <section className="relative z-10 mx-auto max-w-3xl px-6 pt-28 pb-20">
        <h2 className="mb-12 text-center text-2xl font-bold md:text-3xl">
          How it works
        </h2>
        <PipelineStep
          step={1}
          title="Connect your repo"
          description="Paste a GitHub repo URL. Aegis installs a webhook automatically."
        />
        <PipelineStep
          step={2}
          title="Push code"
          description="Every commit and PR triggers an automatic security scan."
        />
        <PipelineStep
          step={3}
          title="Exploit in sandbox"
          description="AI generates a real exploit and runs it in an isolated Docker container."
        />
        <PipelineStep
          step={4}
          title="Patch & verify"
          description="AI writes a fix, re-runs the exploit to confirm it's patched."
        />
        <PipelineStep
          step={5}
          title="Review the PR"
          description="A GitHub PR with exploit proof and patch is ready for your review."
          isLast
        />
      </section>
    </div>
  );
}
