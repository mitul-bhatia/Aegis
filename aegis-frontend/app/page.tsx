"use client";

import { useAuth } from "@/lib/auth";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const { user, login } = useAuth();
  const router = useRouter();

  useEffect(() => {
<<<<<<< HEAD
    if (user) {
      router.push("/dashboard");
    }
  }, [user, router]);
=======
    const uid = localStorage.getItem("aegis_user_id");
    if (uid) router.replace("/dashboard");
  }, [router]);

  function handleLogin() {
    const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, ''); // Remove trailing slash
    const redirectUri = `${apiUrl}/api/auth/github/callback`;
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=repo,write:repo_hook&redirect_uri=${redirectUri}`;
  }
>>>>>>> origin/main

  return (
    <div className="min-h-screen bg-[#050810] text-slate-200 relative overflow-hidden flex flex-col">
      {/* Grid Pattern Background */}
      <div className="absolute inset-0 aegis-grid-pattern opacity-50 z-0"></div>

      {/* Glow Effects */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-violet-900/20 blur-[120px] rounded-full z-0 pointer-events-none"></div>

      {/* Navbar */}
      <nav className="relative z-10 border-b border-white/5 bg-black/20 backdrop-blur-md px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-white/5 flex items-center justify-center font-bold font-mono border border-white/10 text-white">
            A
          </div>
          <span className="font-bold font-mono tracking-tight text-white text-lg">Aegis</span>
        </div>
        <button
          onClick={login}
          className="bg-white hover:bg-slate-200 text-black font-bold font-mono px-4 py-2 rounded text-sm transition-colors"
        >
          Sign in
        </button>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 text-center pb-20 pt-10">

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-950/30 border border-violet-900/50 mb-8 aegis-glow">
          <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse"></span>
          <span className="text-xs font-mono text-violet-300 font-bold uppercase tracking-wider">Multi-Agent Security Swarm</span>
        </div>

        <h1 className="text-5xl md:text-7xl font-bold font-mono tracking-tighter text-white mb-6 max-w-4xl leading-tight">
          Find vulnerabilities.<br />
          <span className="aegis-gradient-text">Prove they exist.</span><br />
          Write the patch.
        </h1>

        <p className="text-lg md:text-xl text-slate-400 font-mono mb-10 max-w-2xl leading-relaxed">
          Aegis is an autonomous swarm of AI agents that connects to your GitHub repository, finds critical security flaws, proves them in an isolated sandbox, and opens a PR with the fix.
        </p>

        <button
          onClick={login}
          className="bg-violet-600 hover:bg-violet-500 text-white font-bold font-mono px-8 py-4 rounded-lg text-lg transition-all aegis-card-hover border border-violet-500 mb-20 flex items-center gap-3"
        >
          <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
          Connect GitHub
        </button>

        {/* Pipeline Demo Horizontal Flow */}
        <div className="w-full max-w-5xl bg-slate-900/40 border border-slate-800 rounded-2xl p-8 backdrop-blur-sm">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
            {/* Connecting Line */}
            <div className="hidden md:block absolute top-1/2 left-[10%] right-[10%] h-0.5 bg-slate-800 -translate-y-1/2 z-0"></div>

            {/* Agents */}
            {[
              { role: "Finder", icon: "🔍", color: "text-violet-400", border: "border-violet-900", bg: "bg-violet-950", desc: "Scans for vulnerabilities" },
              { role: "Exploiter", icon: "⚡", color: "text-red-400", border: "border-red-900", bg: "bg-red-950", desc: "Proves it in sandbox" },
              { role: "Engineer", icon: "🔧", color: "text-amber-400", border: "border-amber-900", bg: "bg-amber-950", desc: "Writes secure patch" },
              { role: "Verifier", icon: "🛡️", color: "text-emerald-400", border: "border-emerald-900", bg: "bg-emerald-950", desc: "Tests & opens PR" },
            ].map((agent, i) => (
              <div key={i} className="relative z-10 flex flex-col items-center bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className={`w-12 h-12 rounded-full ${agent.bg} ${agent.border} border-2 flex items-center justify-center text-xl mb-3 shadow-lg`}>
                  {agent.icon}
                </div>
                <h3 className={`font-mono font-bold ${agent.color} mb-1`}>{agent.role}</h3>
                <p className="text-xs text-slate-500 font-mono text-center leading-relaxed">
                  {agent.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mt-12 flex flex-wrap justify-center gap-8 text-sm font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span className="text-emerald-400">✓</span> Zero False Positives
          </div>
          <div className="flex items-center gap-2">
            <span className="text-emerald-400">✓</span> Isolated Docker Sandbox
          </div>
          <div className="flex items-center gap-2">
            <span className="text-emerald-400">✓</span> Automated PR Generation
          </div>
        </div>
      </main>
    </div>
  );
}
