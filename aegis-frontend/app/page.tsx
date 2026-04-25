"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SwarmTerminal } from "@/components/SwarmTerminal";
import { api } from "@/lib/api";
import { AGENTS, PIPELINE_NODES, STATS, HERO_METRICS, STACK, Mono, PipelineDemo } from "./_landing";

const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || "";

export default function LandingPage() {
  const router = useRouter();

  useEffect(() => {
    api.getMe().then((user) => { if (user) router.replace("/dashboard"); });
  }, [router]);

  function handleLogin() {
    const redirectUri = `${window.location.origin}/auth/callback`;
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=repo,write:repo_hook&redirect_uri=${redirectUri}`;
  }

  return (
    <div style={{ background: "var(--background)", color: "var(--foreground)", overflowX: "hidden" }}>

      {/* ── NAV ── */}
      <nav className="aegis-glass-nav" style={{ position: "sticky", top: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 48px" }}>
        <div style={{ fontFamily: "var(--font-syne, sans-serif)", fontWeight: 800, fontSize: 20, letterSpacing: "0.08em" }}>
          AE<span style={{ color: "var(--green)" }}>G</span>IS
        </div>
        <ul style={{ display: "flex", gap: 36, listStyle: "none", margin: 0, padding: 0 }}>
          {["Agents", "Pipeline", "Security", "Research"].map((item) => (
            <li key={item}>
              <a href={`#${item.toLowerCase()}`} style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 12, color: "var(--muted)", textDecoration: "none", letterSpacing: "0.12em", textTransform: "uppercase", transition: "color 0.2s" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--green)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--muted)")}>
                {item}
              </a>
            </li>
          ))}
        </ul>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ThemeToggle />
          <button onClick={handleLogin} className="aegis-btn-shimmer" style={{
            fontFamily: "var(--font-share-tech-mono)", fontSize: 12, padding: "9px 22px",
            border: "1px solid var(--green)", color: "var(--green)", background: "transparent",
            cursor: "pointer", letterSpacing: "0.1em", textTransform: "uppercase", transition: "background 0.2s, color 0.2s",
          }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--green)"; (e.currentTarget as HTMLButtonElement).style.color = "var(--background)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.color = "var(--green)"; }}>
            Connect GitHub →
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <div style={{ position: "relative", minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "80px 48px 60px", overflow: "hidden" }}>
        {/* Scanning grid */}
        <div className="aegis-grid-bg" style={{ position: "absolute", inset: 0, pointerEvents: "none" }} />
        {/* Vignette */}
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 80% 60% at 50% 50%, transparent 30%, var(--background) 100%)", pointerEvents: "none" }} />
        {/* Scan line */}
        <div style={{ position: "absolute", left: 0, right: 0, height: 2, background: "linear-gradient(90deg, transparent, var(--green), transparent)", animation: "scanDown 4s ease-in-out infinite", opacity: 0.6, pointerEvents: "none" }} />
        {/* Corner brackets */}
        {[["top:72px", "left:44px", "borderTop", "borderLeft"], ["top:72px", "right:44px", "borderTop", "borderRight"], ["bottom:32px", "left:44px", "borderBottom", "borderLeft"], ["bottom:32px", "right:44px", "borderBottom", "borderRight"]].map((corners, i) => (
          <div key={i} style={{ position: "absolute", width: 28, height: 28, [corners[0].split(":")[0]]: corners[0].split(":")[1], [corners[1].split(":")[0]]: corners[1].split(":")[1], [corners[2]]: "2px solid var(--green)", [corners[3]]: "2px solid var(--green)" }} />
        ))}

        {/* Content */}
        <div style={{ position: "relative", zIndex: 1 }}>
          {/* Status badge */}
          <div style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: "var(--font-share-tech-mono)", fontSize: 11, color: "var(--green)", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 28, padding: "7px 18px", border: "1px solid var(--green-dim)", background: "var(--green-dim)" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--green)", animation: "pulse 2s ease-in-out infinite" }} />
            System Operational · 4 Agents Active · 0 Escalations
          </div>

          {/* H1 */}
          <h1 style={{ fontFamily: "var(--font-syne)", fontWeight: 800, fontSize: "clamp(44px, 7vw, 88px)", lineHeight: 1.0, letterSpacing: "-0.02em", marginBottom: 12 }}>
            Autonomous<br />
            <em style={{ fontStyle: "normal", color: "var(--green)", display: "block" }}>Vulnerability</em>
            Remediation
          </h1>

          {/* Sub */}
          <div style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 12, color: "var(--muted)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 24 }}>
            // White-Hat AI Swarm · v2.0 · April 2026
          </div>

          <p style={{ maxWidth: 560, margin: "0 auto 44px", fontSize: 17, color: "var(--muted)", fontWeight: 300, lineHeight: 1.65 }}>
            A 4-agent AI pipeline that detects, exploits, patches, and validates security vulnerabilities — fully autonomously, around the clock.
          </p>

          <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap" }}>
            <button onClick={handleLogin} className="aegis-btn-shimmer" style={{
              fontFamily: "var(--font-share-tech-mono)", fontSize: 12, padding: "14px 32px",
              background: "var(--green)", color: "var(--background)", border: "none",
              cursor: "pointer", letterSpacing: "0.1em", textTransform: "uppercase",
              fontWeight: 600, transition: "transform 0.15s, box-shadow 0.15s",
            }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 8px 24px rgba(0,232,122,0.3)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = ""; (e.currentTarget as HTMLButtonElement).style.boxShadow = ""; }}>
              View Live Dashboard →
            </button>
            <button style={{
              fontFamily: "var(--font-share-tech-mono)", fontSize: 12, padding: "14px 32px",
              background: "transparent", color: "var(--foreground)", border: "1px solid var(--border)",
              cursor: "pointer", letterSpacing: "0.1em", textTransform: "uppercase", transition: "border-color 0.2s, color 0.2s",
            }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--blue)"; (e.currentTarget as HTMLButtonElement).style.color = "var(--blue)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLButtonElement).style.color = "var(--foreground)"; }}>
              Read Architecture Docs
            </button>
          </div>

          {/* Hero metrics bar */}
          <div style={{ display: "flex", gap: 0, marginTop: 64, border: "1px solid var(--border)", background: "var(--surface)" }}>
            {HERO_METRICS.map((m, i) => (
              <div key={m.label} style={{ padding: "24px 36px", textAlign: "center", borderRight: i < HERO_METRICS.length - 1 ? "1px solid var(--border)" : "none", flex: 1 }}>
                <span style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: 34, color: "var(--foreground)", display: "block" }}>
                  <span style={{ color: "var(--green)" }}>{m.num}</span>{m.suffix}
                </span>
                <Mono style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase", display: "block", marginTop: 4 }}>
                  {m.label}
                </Mono>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── LIVE FEED ── */}
      <div style={{ padding: "0 48px 80px", maxWidth: 1280, margin: "0 auto" }}>
        <SwarmTerminal />
      </div>

      {/* ── AGENTS ── */}
      <section id="agents" style={{ padding: "80px 48px", maxWidth: 1280, margin: "0 auto" }}>
        <div className="aegis-section-tag" style={{ marginBottom: 14 }}>Agent Architecture</div>
        <h2 style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: "clamp(28px, 4vw, 44px)", lineHeight: 1.1, marginBottom: 12 }}>
          Four-Agent Swarm
        </h2>
        <p style={{ fontSize: 16, color: "var(--muted)", maxWidth: 500, marginBottom: 48, fontWeight: 300 }}>
          Modeled after a real security team — finder, red teamer, engineer, reviewer — running 24/7 at machine speed.
        </p>

        {/* Agent grid — 1px gap creates Design.md border effect */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 1, background: "var(--border)", border: "1px solid var(--border)" }}>
          {AGENTS.map((agent) => (
            <div key={agent.id} className="animate-agent-appear" style={{ background: "var(--card)", padding: "32px 28px", position: "relative", transition: "background 0.25s", overflow: "hidden", cursor: "default" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#161E27")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "var(--card)")}>
              {/* Top accent line */}
              <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: agent.color, transition: "height 0.2s" }} />
              {/* Agent ID row */}
              <div style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 10, letterSpacing: "0.2em", color: agent.color, textTransform: "uppercase", marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
                Agent {agent.id}
                <span style={{ flex: 1, height: 1, background: "var(--border)", display: "block" }} />
              </div>
              <span style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 26, color: agent.color, display: "block", marginBottom: 14, opacity: 0.85 }}>{agent.icon}</span>
              <div style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: 19, marginBottom: 3 }}>{agent.label}</div>
              <div style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 14 }}>{agent.role}</div>
              <p style={{ fontSize: 13.5, color: "var(--muted)", lineHeight: 1.6, marginBottom: 18 }}>{agent.desc}</p>
              <div style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 10, color: agent.color, background: "rgba(255,255,255,0.04)", padding: "5px 10px", display: "inline-block", border: "1px solid rgba(255,255,255,0.06)" }}>
                {agent.model}
              </div>
              {/* Large background letter */}
              <div style={{ position: "absolute", right: 16, bottom: 16, fontFamily: "var(--font-syne)", fontWeight: 800, fontSize: 76, color: "rgba(255,255,255,0.02)", lineHeight: 1, pointerEvents: "none", userSelect: "none" }}>
                {agent.id}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── PIPELINE ── */}
      <section id="pipeline" style={{ padding: "0 48px 80px", maxWidth: 1280, margin: "0 auto" }}>
        <div className="aegis-section-tag" style={{ marginBottom: 14 }}>Data Flow</div>
        <h2 style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: "clamp(28px, 4vw, 44px)", lineHeight: 1.1, marginBottom: 12 }}>The Autonomous Pipeline</h2>
        <p style={{ fontSize: 16, color: "var(--muted)", maxWidth: 500, marginBottom: 40, fontWeight: 300 }}>
          A sequential + event-driven architecture. Every step is auditable and cost-bounded.
        </p>
        <PipelineDemo />
      </section>

      {/* ── STATS ROW ── */}
      <section style={{ padding: "0 48px 0", maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, background: "var(--border)", border: "1px solid var(--border)", marginBottom: 1 }}>
          {STATS.map((s) => (
            <div key={s.label} style={{ background: "var(--surface)", padding: "36px 28px", position: "relative", overflow: "hidden" }}>
              <div style={{ fontFamily: "var(--font-syne)", fontWeight: 800, fontSize: 48, lineHeight: 1, marginBottom: 6 }}>
                <span style={{ color: "var(--green)" }}>{s.num}</span>{s.suffix}
              </div>
              <Mono style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase" }}>{s.label}</Mono>
              <div style={{ position: "absolute", right: -8, top: -8, fontFamily: "var(--font-share-tech-mono)", fontSize: 96, color: "rgba(255,255,255,0.02)", lineHeight: 1, pointerEvents: "none" }}>{s.bg}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECURITY STACK ── */}
      <section id="security" style={{ padding: "80px 48px", maxWidth: 1280, margin: "0 auto" }}>
        <div className="aegis-section-tag" style={{ marginBottom: 14 }}>Defense in Depth</div>
        <h2 style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: "clamp(28px, 4vw, 44px)", lineHeight: 1.1, marginBottom: 12 }}>Security Architecture</h2>
        <p style={{ fontSize: 16, color: "var(--muted)", maxWidth: 500, marginBottom: 48, fontWeight: 300 }}>
          A system that executes AI-generated exploit code must be hardened against every attack vector — especially itself.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: "var(--border)", border: "1px solid var(--border)" }}>
          {STACK.map((cell) => (
            <div key={cell.title} style={{ background: "var(--card)", padding: 28 }}>
              <h3 style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: 17, marginBottom: 18, display: "flex", alignItems: "center", gap: 10 }}>
                {cell.title}
                <span style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 10, padding: "2px 8px", letterSpacing: "0.1em", textTransform: "uppercase", background: cell.tagBg, color: cell.tagColor }}>
                  {cell.tag}
                </span>
              </h3>
              {cell.items.map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "9px 0", borderBottom: i < cell.items.length - 1 ? "1px solid rgba(30,45,61,0.5)" : "none", fontSize: 13.5, color: "var(--muted)" }}>
                  <span style={{ color: item.ok ? "var(--green)" : "var(--amber)", fontFamily: "var(--font-share-tech-mono)", fontSize: 12, marginTop: 1, flexShrink: 0 }}>{item.ok ? "▶" : "⚠"}</span>
                  <span><strong style={{ color: "var(--foreground)", fontWeight: 500 }}>{item.bold}</strong> {item.rest}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <div id="research" style={{ padding: "80px 48px", textAlign: "center", position: "relative", overflow: "hidden", borderTop: "1px solid var(--border)" }}>
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 60% 40% at 50% 100%, rgba(0,232,122,0.05), transparent 60%)", pointerEvents: "none" }} />
        <div className="aegis-section-tag" style={{ justifyContent: "center", marginBottom: 20, position: "relative" }}>// Validated at DARPA AIxCC · DEF CON 33 · August 2025</div>
        <h2 style={{ fontFamily: "var(--font-syne)", fontWeight: 700, fontSize: "clamp(32px, 5vw, 54px)", marginBottom: 16, position: "relative" }}>Security at Machine Speed</h2>
        <p style={{ fontSize: 17, color: "var(--muted)", marginBottom: 36, position: "relative", fontWeight: 300 }}>
          From commit webhook to merged patch, fully autonomous — averaging 45 minutes and $152 per remediated vulnerability.
        </p>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap", position: "relative" }}>
          <button onClick={handleLogin} className="aegis-btn-shimmer" style={{
            fontFamily: "var(--font-share-tech-mono)", fontSize: 12, padding: "14px 32px",
            background: "var(--green)", color: "var(--background)", border: "none",
            cursor: "pointer", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600,
          }}>Deploy the Swarm →</button>
          <button style={{
            fontFamily: "var(--font-share-tech-mono)", fontSize: 12, padding: "14px 32px",
            background: "transparent", color: "var(--foreground)", border: "1px solid var(--border)",
            cursor: "pointer", letterSpacing: "0.1em", textTransform: "uppercase",
          }}>Read Full Architecture</button>
        </div>
      </div>

      {/* ── FOOTER ── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "28px 48px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
        <div style={{ fontFamily: "var(--font-syne)", fontWeight: 800, fontSize: 16, color: "var(--muted)" }}>
          AE<span style={{ color: "var(--green)" }}>G</span>IS
        </div>
        <Mono style={{ fontSize: 11, color: "var(--muted)" }}>v2.0 · April 2026 · Autonomous Security Remediation</Mono>
        <div style={{ display: "flex", gap: 24 }}>
          {["Architecture Docs", "GitHub", "Security Policy"].map((l) => (
            <a key={l} href="#" style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: 11, color: "var(--muted)", textDecoration: "none", transition: "color 0.2s" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--green)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--muted)")}>
              {l}
            </a>
          ))}
        </div>
      </footer>
    </div>
  );
}
