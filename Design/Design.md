<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>SWARM — Autonomous Vulnerability Remediation</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
<style>
  :root {
    --black:    #06080B;
    --surface:  #0C1017;
    --card:     #111820;
    --border:   #1E2D3D;
    --green:    #00E87A;
    --green-dim:#00E87A33;
    --red:      #FF2B4A;
    --red-dim:  #FF2B4A22;
    --blue:     #4CB8FF;
    --blue-dim: #4CB8FF22;
    --amber:    #FFB800;
    --amber-dim:#FFB80022;
    --text:     #E8EFF7;
    --muted:    #5A7A94;
    --mono:     'Share Tech Mono', monospace;
    --display:  'Syne', sans-serif;
    --body:     'DM Sans', sans-serif;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--black);
    color: var(--text);
    font-family: var(--body);
    font-weight: 300;
    line-height: 1.65;
    overflow-x: hidden;
  }

  /* ─── SCROLLBAR ─── */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  /* ─── NAV ─── */
  nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 48px;
    background: rgba(6,8,11,0.85);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
  }
  .nav-logo {
    font-family: var(--display);
    font-weight: 800;
    font-size: 20px;
    letter-spacing: 0.08em;
    color: var(--text);
  }
  .nav-logo span { color: var(--green); }
  .nav-links { display: flex; gap: 36px; list-style: none; }
  .nav-links a {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--muted);
    text-decoration: none;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    transition: color 0.2s;
  }
  .nav-links a:hover { color: var(--green); }
  .nav-cta {
    font-family: var(--mono);
    font-size: 12px;
    padding: 10px 24px;
    border: 1px solid var(--green);
    color: var(--green);
    background: transparent;
    cursor: pointer;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    transition: background 0.2s, color 0.2s;
  }
  .nav-cta:hover { background: var(--green); color: var(--black); }

  /* ─── HERO ─── */
  .hero {
    position: relative;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 120px 48px 80px;
    overflow: hidden;
  }
  /* Scanning grid background */
  .hero-grid {
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(0,232,122,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,232,122,0.04) 1px, transparent 1px);
    background-size: 60px 60px;
    animation: gridShift 20s linear infinite;
  }
  @keyframes gridShift {
    0%   { background-position: 0 0, 0 0; }
    100% { background-position: 60px 60px, 60px 60px; }
  }
  /* Vignette */
  .hero::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 80% 60% at 50% 50%, transparent 30%, var(--black) 100%);
    pointer-events: none;
  }
  /* Scanning line */
  .scan-line {
    position: absolute;
    left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--green), transparent);
    animation: scanDown 4s ease-in-out infinite;
    opacity: 0.6;
  }
  @keyframes scanDown {
    0%   { top: -2px; opacity: 0; }
    10%  { opacity: 0.6; }
    90%  { opacity: 0.6; }
    100% { top: 100%; opacity: 0; }
  }
  /* Corner brackets */
  .corner { position: absolute; width: 32px; height: 32px; }
  .corner--tl { top: 80px; left: 48px; border-top: 2px solid var(--green); border-left: 2px solid var(--green); }
  .corner--tr { top: 80px; right: 48px; border-top: 2px solid var(--green); border-right: 2px solid var(--green); }
  .corner--bl { bottom: 40px; left: 48px; border-bottom: 2px solid var(--green); border-left: 2px solid var(--green); }
  .corner--br { bottom: 40px; right: 48px; border-bottom: 2px solid var(--green); border-right: 2px solid var(--green); }

  .hero-status {
    position: relative;
    display: inline-flex; align-items: center; gap: 10px;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--green);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 28px;
    padding: 8px 20px;
    border: 1px solid var(--green-dim);
    background: var(--green-dim);
  }
  .pulse {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.6); }
  }
  .hero h1 {
    position: relative;
    font-family: var(--display);
    font-weight: 800;
    font-size: clamp(44px, 7vw, 90px);
    line-height: 1.0;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
  }
  .hero h1 em {
    font-style: normal;
    color: var(--green);
    display: block;
  }
  .hero-sub {
    position: relative;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 28px;
  }
  .hero p {
    position: relative;
    max-width: 580px;
    font-size: 17px;
    color: var(--muted);
    margin: 0 auto 48px;
    font-weight: 300;
  }
  .hero-ctas { position: relative; display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
  .btn-primary {
    font-family: var(--mono);
    font-size: 12px;
    padding: 16px 36px;
    background: var(--green);
    color: var(--black);
    border: none;
    cursor: pointer;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
    transition: transform 0.15s, box-shadow 0.15s;
  }
  .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,232,122,0.3); }
  .btn-ghost {
    font-family: var(--mono);
    font-size: 12px;
    padding: 16px 36px;
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border);
    cursor: pointer;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    transition: border-color 0.2s, color 0.2s;
  }
  .btn-ghost:hover { border-color: var(--blue); color: var(--blue); }

  /* Hero metrics */
  .hero-metrics {
    position: relative;
    display: flex;
    gap: 0;
    margin-top: 72px;
    border: 1px solid var(--border);
    background: var(--surface);
  }
  .metric {
    padding: 28px 40px;
    text-align: center;
    border-right: 1px solid var(--border);
    flex: 1;
  }
  .metric:last-child { border-right: none; }
  .metric-num {
    font-family: var(--display);
    font-weight: 700;
    font-size: 36px;
    color: var(--text);
    display: block;
  }
  .metric-num .accent { color: var(--green); }
  .metric-label {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    display: block;
    margin-top: 4px;
  }

  /* ─── SECTION SHARED ─── */
  section { padding: 100px 48px; max-width: 1280px; margin: 0 auto; }
  .section-tag {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--green);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .section-tag::before { content: '//'; color: var(--border); }
  h2 {
    font-family: var(--display);
    font-weight: 700;
    font-size: clamp(28px, 4vw, 46px);
    line-height: 1.1;
    margin-bottom: 16px;
  }
  .section-lead { font-size: 17px; color: var(--muted); max-width: 520px; margin-bottom: 56px; }

  /* ─── LIVE FEED ─── */
  .live-section {
    padding: 0 48px 100px;
    max-width: 1280px;
    margin: 0 auto;
  }
  .live-panel {
    border: 1px solid var(--border);
    background: var(--surface);
    overflow: hidden;
  }
  .live-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--card);
  }
  .live-title {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dot-green { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
  .dot-amber { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); animation: pulse 2s 0.5s infinite; }
  .dot-red   { width: 6px; height: 6px; border-radius: 50%; background: var(--red);   animation: pulse 2s 1s infinite; }
  .live-log { padding: 0; max-height: 280px; overflow-y: auto; }
  .log-entry {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 12px 20px;
    border-bottom: 1px solid rgba(30,45,61,0.5);
    font-family: var(--mono);
    font-size: 12px;
    animation: fadeIn 0.4s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
  .log-time { color: var(--muted); white-space: nowrap; min-width: 64px; }
  .log-agent { min-width: 80px; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; padding: 2px 8px; text-align: center; }
  .agent-a { background: var(--red-dim); color: var(--red); }
  .agent-b { background: var(--blue-dim); color: var(--blue); }
  .agent-c { background: var(--amber-dim); color: var(--amber); }
  .agent-d { background: var(--green-dim); color: var(--green); }
  .agent-e { background: rgba(76,184,255,0.1); color: #8DD4FF; }
  .agent-f { background: rgba(180,100,255,0.1); color: #C87FFF; }
  .agent-s { background: rgba(255,255,255,0.05); color: var(--muted); }
  .log-msg { color: var(--text); flex: 1; }
  .log-msg .hi-green { color: var(--green); }
  .log-msg .hi-red   { color: var(--red); }
  .log-msg .hi-amber { color: var(--amber); }
  .log-msg .hi-blue  { color: var(--blue); }
  .log-status { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; white-space: nowrap; padding: 2px 10px; }
  .status-ok   { background: var(--green-dim); color: var(--green); }
  .status-warn { background: var(--amber-dim); color: var(--amber); }
  .status-crit { background: var(--red-dim); color: var(--red); }
  .status-info { background: var(--blue-dim); color: var(--blue); }

  /* ─── AGENTS GRID ─── */
  .agents-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
  }
  .agent-card {
    background: var(--card);
    padding: 36px 32px;
    position: relative;
    transition: background 0.25s;
    cursor: default;
    overflow: hidden;
  }
  .agent-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--agent-color, var(--border));
    transition: height 0.3s;
  }
  .agent-card:hover { background: #161E27; }
  .agent-card:hover::before { height: 3px; }
  .agent-id {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--agent-color, var(--muted));
    text-transform: uppercase;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .agent-id::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }
  .agent-icon {
    font-family: var(--mono);
    font-size: 28px;
    color: var(--agent-color, var(--muted));
    margin-bottom: 16px;
    display: block;
    opacity: 0.8;
  }
  .agent-name {
    font-family: var(--display);
    font-weight: 700;
    font-size: 20px;
    margin-bottom: 4px;
    color: var(--text);
  }
  .agent-role {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 16px;
  }
  .agent-desc {
    font-size: 14px;
    color: var(--muted);
    line-height: 1.6;
    margin-bottom: 20px;
  }
  .agent-model {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--agent-color, var(--muted));
    background: rgba(255,255,255,0.04);
    padding: 6px 12px;
    display: inline-block;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .agent-bg-num {
    position: absolute;
    right: 20px; bottom: 20px;
    font-family: var(--display);
    font-weight: 800;
    font-size: 80px;
    color: rgba(255,255,255,0.02);
    line-height: 1;
    pointer-events: none;
    user-select: none;
  }

  /* ─── PIPELINE ─── */
  .pipeline-wrap {
    border: 1px solid var(--border);
    background: var(--surface);
    padding: 48px;
    position: relative;
    overflow-x: auto;
  }
  .pipeline {
    display: flex;
    align-items: center;
    gap: 0;
    min-width: 700px;
  }
  .pipe-node {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    padding: 20px 16px;
    text-align: center;
    position: relative;
    transition: border-color 0.25s;
    cursor: default;
  }
  .pipe-node:hover { border-color: var(--node-color, var(--border)); }
  .pipe-label {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--node-color, var(--muted));
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .pipe-name {
    font-family: var(--display);
    font-weight: 700;
    font-size: 14px;
    color: var(--text);
  }
  .pipe-arrow {
    font-family: var(--mono);
    color: var(--border);
    font-size: 18px;
    padding: 0 8px;
    flex-shrink: 0;
    position: relative;
  }
  .pipe-arrow.animated { color: var(--green); animation: arrowPulse 2s ease infinite; }
  @keyframes arrowPulse {
    0%, 100% { opacity: 0.3; }
    50%       { opacity: 1; }
  }
  .pipe-parallel {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1.6;
  }
  .pipe-parallel .pipe-node { flex: unset; }

  /* ─── STATS ROW ─── */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    margin-bottom: 1px;
  }
  .stat-cell {
    background: var(--surface);
    padding: 40px 32px;
    position: relative;
    overflow: hidden;
  }
  .stat-num {
    font-family: var(--display);
    font-weight: 800;
    font-size: 52px;
    line-height: 1;
    margin-bottom: 8px;
    color: var(--text);
  }
  .stat-num .accent { color: var(--green); }
  .stat-label {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }
  .stat-bg {
    position: absolute;
    right: -10px; top: -10px;
    font-family: var(--mono);
    font-size: 100px;
    color: rgba(255,255,255,0.02);
    line-height: 1;
    pointer-events: none;
    user-select: none;
  }

  /* ─── SECURITY STACK ─── */
  .stack-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
  }
  .stack-cell {
    background: var(--card);
    padding: 32px;
  }
  .stack-cell h3 {
    font-family: var(--display);
    font-weight: 700;
    font-size: 18px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .stack-cell h3 .tag {
    font-family: var(--mono);
    font-size: 10px;
    padding: 3px 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .stack-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(30,45,61,0.6);
    font-size: 14px;
    color: var(--muted);
  }
  .stack-item:last-child { border-bottom: none; }
  .stack-item .check { color: var(--green); font-family: var(--mono); font-size: 12px; }
  .stack-item .warn  { color: var(--amber); font-family: var(--mono); font-size: 12px; }
  .stack-item strong { color: var(--text); font-weight: 500; }

  /* ─── CTA SECTION ─── */
  .cta-section {
    padding: 100px 48px;
    text-align: center;
    position: relative;
    overflow: hidden;
    border-top: 1px solid var(--border);
  }
  .cta-section::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 40% at 50% 100%, rgba(0,232,122,0.05) 0%, transparent 60%);
  }
  .cta-section h2 { position: relative; font-size: clamp(32px, 5vw, 56px); margin-bottom: 20px; }
  .cta-section p  { position: relative; font-size: 17px; color: var(--muted); margin-bottom: 40px; }

  /* ─── FOOTER ─── */
  footer {
    border-top: 1px solid var(--border);
    padding: 32px 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
  }
  footer .logo {
    font-family: var(--display);
    font-weight: 800;
    font-size: 16px;
    color: var(--muted);
  }
  footer .logo span { color: var(--green); }
  footer p {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.1em;
  }
  footer .links { display: flex; gap: 24px; }
  footer .links a {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    text-decoration: none;
    letter-spacing: 0.1em;
    transition: color 0.2s;
  }
  footer .links a:hover { color: var(--green); }

  /* ─── THREAT BANNER ─── */
  .threat-banner {
    background: var(--red-dim);
    border-bottom: 1px solid rgba(255,43,74,0.3);
    padding: 10px 48px;
    display: flex;
    align-items: center;
    gap: 20px;
    overflow: hidden;
  }
  .threat-banner .label {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--red);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    white-space: nowrap;
    padding: 4px 12px;
    border: 1px solid rgba(255,43,74,0.4);
    flex-shrink: 0;
  }
  .marquee-wrap { flex: 1; overflow: hidden; position: relative; }
  .marquee-track {
    display: flex;
    gap: 60px;
    white-space: nowrap;
    animation: marquee 28s linear infinite;
  }
  @keyframes marquee {
    from { transform: translateX(0); }
    to   { transform: translateX(-50%); }
  }
  .marquee-item {
    font-family: var(--mono);
    font-size: 11px;
    color: rgba(255,43,74,0.7);
    letter-spacing: 0.08em;
    white-space: nowrap;
  }
  .marquee-item span { color: var(--red); margin-right: 4px; }

  /* divider */
  .divider { border: none; border-top: 1px solid var(--border); margin: 0; }
</style>
</head>
<body>

<!-- ── THREAT BANNER ── -->
<div class="threat-banner">
  <div class="label">Live Threats</div>
  <div class="marquee-wrap">
    <div class="marquee-track">
      <span class="marquee-item"><span>CVE-2026-0381</span> CRITICAL · pyyaml RCE · EPSS 0.91</span>
      <span class="marquee-item"><span>AGENT-A</span> SQLi confirmed · repo: api-gateway · exploit in 4.2s</span>
      <span class="marquee-item"><span>CVE-2026-1142</span> HIGH · pillow heap overflow · EPSS 0.73</span>
      <span class="marquee-item"><span>AGENT-F</span> Path traversal detected · /uploads endpoint · auto-queued</span>
      <span class="marquee-item"><span>PATCH MERGED</span> CWE-89 remediated in 7m 22s · 0 test regressions</span>
      <span class="marquee-item"><span>CVE-2026-0381</span> CRITICAL · pyyaml RCE · EPSS 0.91</span>
      <span class="marquee-item"><span>AGENT-A</span> SQLi confirmed · repo: api-gateway · exploit in 4.2s</span>
      <span class="marquee-item"><span>CVE-2026-1142</span> HIGH · pillow heap overflow · EPSS 0.73</span>
      <span class="marquee-item"><span>AGENT-F</span> Path traversal detected · /uploads endpoint · auto-queued</span>
      <span class="marquee-item"><span>PATCH MERGED</span> CWE-89 remediated in 7m 22s · 0 test regressions</span>
    </div>
  </div>
</div>

<!-- ── NAV ── -->
<nav>
  <div class="nav-logo">SW<span>A</span>RM</div>
  <ul class="nav-links">
    <li><a href="#agents">Agents</a></li>
    <li><a href="#pipeline">Pipeline</a></li>
    <li><a href="#security">Security</a></li>
    <li><a href="#research">Research</a></li>
  </ul>
  <button class="nav-cta">Request Access</button>
</nav>

<!-- ── HERO ── -->
<div class="hero">
  <div class="hero-grid"></div>
  <div class="scan-line"></div>
  <div class="corner corner--tl"></div>
  <div class="corner corner--tr"></div>
  <div class="corner corner--bl"></div>
  <div class="corner corner--br"></div>

  <div class="hero-status">
    <div class="pulse"></div>
    System Operational · 7 Agents Active · 0 Escalations
  </div>

  <h1>
    Autonomous<br>
    <em>Vulnerability</em>
    Remediation
  </h1>
  <div class="hero-sub">// White-Hat AI Swarm · v2.0 · April 2026</div>
  <p>
    A 7-agent AI pipeline that detects, exploits, patches,
    and validates security vulnerabilities — fully autonomously,
    around the clock.
  </p>
  <div class="hero-ctas">
    <button class="btn-primary">View Live Dashboard →</button>
    <button class="btn-ghost">Read Architecture Docs</button>
  </div>

  <div class="hero-metrics">
    <div class="metric">
      <span class="metric-num"><span class="accent">71</span>%</span>
      <span class="metric-label">Patch Correctness (AIxCC)</span>
    </div>
    <div class="metric">
      <span class="metric-num"><span class="accent">45</span>m</span>
      <span class="metric-label">Avg Remediation Time</span>
    </div>
    <div class="metric">
      <span class="metric-num">$<span class="accent">152</span></span>
      <span class="metric-label">Cost Per Task</span>
    </div>
    <div class="metric">
      <span class="metric-num"><span class="accent">54M</span></span>
      <span class="metric-label">Lines of Code Processed</span>
    </div>
  </div>
</div>

<!-- ── LIVE FEED ── -->
<div class="live-section">
  <div class="live-panel">
    <div class="live-header">
      <div class="live-title">
        <div class="dot-green"></div>
        Swarm Activity Feed — Live
      </div>
      <div style="display:flex;gap:16px;align-items:center;">
        <div style="display:flex;gap:8px;align-items:center;">
          <div class="dot-green"></div><span style="font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:0.1em">ALL SYSTEMS OK</span>
        </div>
        <div style="font-family:var(--mono);font-size:10px;color:var(--muted);" id="clock">--:--:--</div>
      </div>
    </div>
    <div class="live-log" id="log"></div>
  </div>
</div>

<!-- ── AGENTS ── -->
<section id="agents">
  <div class="section-tag">Agent Architecture</div>
  <h2>Seven-Agent Swarm</h2>
  <p class="section-lead">Modeled after a real security team — taint analyst, red teamer, engineer, reviewer — running 24/7 at machine speed.</p>

  <div class="agents-grid">

    <div class="agent-card" style="--agent-color: var(--red);">
      <div class="agent-id">Agent A</div>
      <span class="agent-icon">⚡</span>
      <div class="agent-name">The Hacker</div>
      <div class="agent-role">Exploit Generation</div>
      <div class="agent-desc">Analyzes every commit diff, generates proof-of-concept exploits, and executes them in a sandboxed VM. The exploit result is the only ground truth.</div>
      <div class="agent-model">claude-opus-4-6 + extended thinking</div>
      <div class="agent-bg-num">A</div>
    </div>

    <div class="agent-card" style="--agent-color: var(--blue);">
      <div class="agent-id">Agent B</div>
      <span class="agent-icon">⚙</span>
      <div class="agent-name">The Engineer</div>
      <div class="agent-role">Secure Patch Generation</div>
      <div class="agent-desc">Given a confirmed exploit, rewrites the vulnerable section using CWE-specific fix patterns. Switches to GPT-5 on retry ≥ 2 for cross-model validation.</div>
      <div class="agent-model">claude-sonnet-4-6 → gpt-5 (retry)</div>
      <div class="agent-bg-num">B</div>
    </div>

    <div class="agent-card" style="--agent-color: var(--amber);">
      <div class="agent-id">Agent C</div>
      <span class="agent-icon">✓</span>
      <div class="agent-name">The Reviewer</div>
      <div class="agent-role">Patch Validation Gate</div>
      <div class="agent-desc">Runs the test suite (3/3 pass required), re-executes the original exploit against the patched code, and scans for regressions. The final quality gate.</div>
      <div class="agent-model">gpt-4.1 + SandboxAgent (E2B)</div>
      <div class="agent-bg-num">C</div>
    </div>

    <div class="agent-card" style="--agent-color: var(--green);">
      <div class="agent-id">Agent D</div>
      <span class="agent-icon">⬡</span>
      <div class="agent-name">Taint Analyst</div>
      <div class="agent-role">Multi-File Taint Analysis</div>
      <div class="agent-desc">Runs in parallel with Agent A on every commit. Builds a complete call graph and taint flow — enabling detection of multi-file vulnerability chains across the entire codebase.</div>
      <div class="agent-model">claude-haiku-4-5 + CodeQL MCP</div>
      <div class="agent-bg-num">D</div>
    </div>

    <div class="agent-card" style="--agent-color: #8DD4FF;">
      <div class="agent-id">Agent E</div>
      <span class="agent-icon">◎</span>
      <div class="agent-name">CVE Scout</div>
      <div class="agent-role">Dependency Intelligence</div>
      <div class="agent-desc">Triggered by every dependency file change. Cross-references new versions against NVD, OSV, and GitHub Advisory — posting critical CVEs as instant PR comments.</div>
      <div class="agent-model">claude-haiku-4-5 + NVD/OSV MCP</div>
      <div class="agent-bg-num">E</div>
    </div>

    <div class="agent-card" style="--agent-color: #C87FFF;">
      <div class="agent-id">Agent F</div>
      <span class="agent-icon">◈</span>
      <div class="agent-name">Red Teamer</div>
      <div class="agent-role">Proactive Scanning</div>
      <div class="agent-desc">Runs daily on a risk-based prioritization model. Scans the existing codebase — not just new commits — catching vulnerabilities that were always there.</div>
      <div class="agent-model">claude-opus-4-6 (scheduled)</div>
      <div class="agent-bg-num">F</div>
    </div>

  </div>
</section>

<!-- ── PIPELINE ── -->
<section id="pipeline" style="padding-top:0;">
  <div class="section-tag">Data Flow</div>
  <h2>The Autonomous Pipeline</h2>
  <p class="section-lead">A hybrid sequential + event-driven + hierarchical architecture. Every step is auditable and cost-bounded.</p>

  <div class="pipeline-wrap">
    <div class="pipeline">

      <div class="pipe-node" style="--node-color: var(--muted);">
        <div class="pipe-label">Trigger</div>
        <div class="pipe-name">GitHub Webhook</div>
      </div>

      <div class="pipe-arrow animated">→</div>

      <div class="pipe-node" style="--node-color: var(--blue); flex:1.2;">
        <div class="pipe-label">Supervisor</div>
        <div class="pipe-name">LangGraph Commander</div>
      </div>

      <div class="pipe-arrow animated">→</div>

      <div class="pipe-parallel">
        <div class="pipe-node" style="--node-color: var(--green);">
          <div class="pipe-label">Agent D</div>
          <div class="pipe-name">Taint Graph</div>
        </div>
        <div class="pipe-node" style="--node-color: var(--red);">
          <div class="pipe-label">Agent A</div>
          <div class="pipe-name">Exploit Gen</div>
        </div>
        <div class="pipe-node" style="--node-color: #8DD4FF;">
          <div class="pipe-label">Agent E</div>
          <div class="pipe-name">CVE Scan</div>
        </div>
      </div>

      <div class="pipe-arrow animated">→</div>

      <div class="pipe-node" style="--node-color: var(--blue);">
        <div class="pipe-label">Agent B</div>
        <div class="pipe-name">Patch Engineer</div>
      </div>

      <div class="pipe-arrow animated">→</div>

      <div class="pipe-node" style="--node-color: var(--amber);">
        <div class="pipe-label">Agent C</div>
        <div class="pipe-name">Sandbox Review</div>
      </div>

      <div class="pipe-arrow animated">→</div>

      <div class="pipe-node" style="--node-color: var(--green);">
        <div class="pipe-label">Output</div>
        <div class="pipe-name">Auto-Merge PR</div>
      </div>

    </div>

    <!-- Feedback loop label -->
    <div style="margin-top:20px; padding-top:20px; border-top:1px solid var(--border); display:flex;align-items:center;gap:16px;">
      <div style="font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:0.15em;text-transform:uppercase;">Feedback Loop (max 3 retries)</div>
      <div style="flex:1;height:1px;background:repeating-linear-gradient(90deg,var(--amber) 0,var(--amber) 6px,transparent 6px,transparent 12px);"></div>
      <div style="font-family:var(--mono);font-size:10px;color:var(--amber);letter-spacing:0.1em;">C → B with patch-locked context</div>
    </div>
  </div>
</section>

<!-- ── STATS ── -->
<section style="padding-top:0; padding-bottom:0;">
  <div class="stats-row">
    <div class="stat-cell">
      <div class="stat-num"><span class="accent">86</span>%</div>
      <div class="stat-label">False Positive Rate (Industry Baseline)</div>
      <div class="stat-bg">!</div>
    </div>
    <div class="stat-cell">
      <div class="stat-num"><span class="accent">50</span>%+</div>
      <div class="stat-label">Target TP Rate (Post Fine-Tune)</div>
      <div class="stat-bg">✓</div>
    </div>
    <div class="stat-cell">
      <div class="stat-num"><span class="accent">3</span></div>
      <div class="stat-label">Max Retry Attempts Before Escalation</div>
      <div class="stat-bg">#</div>
    </div>
    <div class="stat-cell">
      <div class="stat-num">$<span class="accent">10</span></div>
      <div class="stat-label">Hard Cost Budget Per Commit</div>
      <div class="stat-bg">$</div>
    </div>
  </div>
</section>

<!-- ── SECURITY STACK ── -->
<section id="security">
  <div class="section-tag">Defense in Depth</div>
  <h2>Security Architecture</h2>
  <p class="section-lead">A system that executes AI-generated exploit code must be hardened against every attack vector — especially itself.</p>

  <div class="stack-grid">
    <div class="stack-cell">
      <h3>Prompt Injection Defense <span class="tag" style="background:var(--green-dim);color:var(--green);">Critical</span></h3>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Document blocks</strong> — untrusted code diff isolated from instructions structurally</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>OpenAI Guardrails</strong> — parallel injection detector on Agent C</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Append-only audit log</strong> → Elasticsearch for SOC 2 evidence</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Signed MCP tool definitions</strong> — prevents tool poisoning via repo</div></div>
    </div>
    <div class="stack-cell">
      <h3>Sandbox Isolation <span class="tag" style="background:var(--red-dim);color:var(--red);">High Risk</span></h3>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Firecracker microVMs</strong> (prod) — hardware-level isolation per exploit</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>E2B managed sandboxes</strong> (dev) — 30s timeout, 256MB cap, no network</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>cap_drop ALL</strong> + pids_limit 50 + non-root user in Docker fallback</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Exploit-only: stdlib + requests</strong> — pre-validated before sandbox submission</div></div>
    </div>
    <div class="stack-cell">
      <h3>Patch Validation <span class="tag" style="background:var(--blue-dim);color:var(--blue);">Multi-Layer</span></h3>
      <div class="stack-item"><span class="check">▶</span> <div><strong>semgrep p/security-audit</strong> on every patch diff before sandbox</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>OSV scanner</strong> on all new dependencies Agent B introduces</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>50-line surface area cap</strong> — larger patches require human approval</div></div>
      <div class="stack-item"><span class="warn">⚠</span> <div><strong>Semantic equivalence</strong> — differential fuzzing on 10K random inputs (WIP)</div></div>
    </div>
    <div class="stack-cell">
      <h3>MCP Hardening <span class="tag" style="background:var(--amber-dim);color:var(--amber);">Protocol-Level</span></h3>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Mutual TLS + DPoP tokens</strong> (300s TTL) — all MCP gateway traffic</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>Per-agent RBAC</strong> — Agent B cannot merge; only write_pr drafts</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>OpenTelemetry traces</strong> on 100% of tool calls — anomaly alerting</div></div>
      <div class="stack-item"><span class="check">▶</span> <div><strong>HashiCorp Vault</strong> dynamic secrets — 24-hour TTL API key rotation</div></div>
    </div>
  </div>
</section>

<!-- ── CTA ── -->
<div class="cta-section" id="research">
  <div class="section-tag" style="justify-content:center;">// Validated at DARPA AIxCC · DEF CON 33 · August 2025</div>
  <h2>Security at Machine Speed</h2>
  <p>From commit webhook to merged patch, fully autonomous — averaging 45 minutes and $152 per remediated vulnerability.</p>
  <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
    <button class="btn-primary">Deploy the Swarm →</button>
    <button class="btn-ghost">Read Full Architecture</button>
  </div>
</div>

<!-- ── FOOTER ── -->
<footer>
  <div class="logo">SW<span>A</span>RM</div>
  <p>v3.0 · April 2026 · Internal Research</p>
  <div class="links">
    <a href="#">Architecture Docs</a>
    <a href="#">GitHub</a>
    <a href="#">Security Policy</a>
    <a href="#">AIxCC Results</a>
  </div>
</footer>

<script>
  // Clock
  function tick() {
    const el = document.getElementById('clock');
    if (el) el.textContent = new Date().toLocaleTimeString('en-GB', {hour12:false});
  }
  tick(); setInterval(tick, 1000);

  // Live feed data
  const logs = [
    { a:'agent-s', ag:'SUPERVISOR', m:'Swarm initialized. 7 agents online. Cost budget: <span class="hi-green">$10.00</span> per commit.', s:'status-ok', sl:'READY' },
    { a:'agent-a', ag:'AGENT A', m:'Analyzing commit <span class="hi-amber">a3f7c91</span> · diff +142 / -37 lines · <span class="hi-blue">api/routes.py</span>', s:'status-info', sl:'SCANNING' },
    { a:'agent-d', ag:'AGENT D', m:'Taint graph built: 3 sources → 2 sinks · <span class="hi-amber">multi-file chain detected</span> · 3 files', s:'status-warn', sl:'MULTI-FILE' },
    { a:'agent-e', ag:'AGENT E', m:'requirements.txt changed · checking NVD/OSV… <span class="hi-amber">pillow 9.1.0</span> → CVE-2022-45198 EPSS:<span class="hi-red">0.73</span>', s:'status-warn', sl:'CVE FOUND' },
    { a:'agent-a', ag:'AGENT A', m:'SQLi detected · CWE-89 · <span class="hi-red">CRITICAL</span> · chain: routes.py:45 → user.py:23 → queries.py:12', s:'status-crit', sl:'CONFIRMED' },
    { a:'agent-a', ag:'AGENT A', m:'Exploit generated · executing in sandbox… <span class="hi-green">EXPLOIT_SUCCESS: admin@example.com | hash_f3a9...</span>', s:'status-crit', sl:'EXPLOITED' },
    { a:'agent-b', ag:'AGENT B', m:'Applying parameterized query patch · SKILL.md: sql-injection · surface: <span class="hi-green">18 lines</span>', s:'status-info', sl:'PATCHING' },
    { a:'agent-b', ag:'AGENT B', m:'Searching all instances of vulnerable pattern… found <span class="hi-amber">2 occurrences</span> in auth.py:45, auth.py:87', s:'status-warn', sl:'2 FOUND' },
    { a:'agent-c', ag:'AGENT C', m:'Patch received. Running test suite 1/3… <span class="hi-green">47/47 passed</span> ✓', s:'status-ok', sl:'PASS 1/3' },
    { a:'agent-c', ag:'AGENT C', m:'Test suite 2/3… <span class="hi-green">47/47 passed</span> ✓ · Re-running exploit against patched code…', s:'status-ok', sl:'PASS 2/3' },
    { a:'agent-c', ag:'AGENT C', m:'3/3 pass · Exploit result: <span class="hi-green">EXPLOIT_FAILED: parameterized query rejected input</span> · semgrep clean', s:'status-ok', sl:'APPROVED' },
    { a:'agent-s', ag:'SUPERVISOR', m:'Verdict: <span class="hi-green">APPROVED</span> · Creating PR · Memory consolidation queued · Total cost: <span class="hi-green">$4.21</span>', s:'status-ok', sl:'PATCHED' },
  ];

  const logEl = document.getElementById('log');
  let idx = 0;
  const times = [];
  const now = new Date();
  for (let i = 0; i < logs.length; i++) {
    const t = new Date(now.getTime() - (logs.length - i) * 38000);
    times.push(t.toLocaleTimeString('en-GB', {hour12:false}));
  }

  function addLog(i) {
    if (i >= logs.length) return;
    const d = logs[i];
    const row = document.createElement('div');
    row.className = 'log-entry';
    row.innerHTML = `
      <span class="log-time">${times[i]}</span>
      <span class="log-agent ${d.a}">${d.ag}</span>
      <span class="log-msg">${d.m}</span>
      <span class="log-status ${d.s}">${d.sl}</span>
    `;
    logEl.appendChild(row);
    logEl.scrollTop = logEl.scrollHeight;
  }

  // Show all initial logs quickly, then loop
  let delay = 0;
  logs.forEach((_, i) => {
    setTimeout(() => addLog(i), delay);
    delay += i < 3 ? 100 : 600;
  });

  // Loop feed after first cycle
  setTimeout(() => {
    let li = 0;
    setInterval(() => {
      if (logEl.children.length > 60) logEl.removeChild(logEl.firstChild);
      const now2 = new Date();
      const d = logs[li % logs.length];
      const row = document.createElement('div');
      row.className = 'log-entry';
      row.innerHTML = `
        <span class="log-time">${now2.toLocaleTimeString('en-GB',{hour12:false})}</span>
        <span class="log-agent ${d.a}">${d.ag}</span>
        <span class="log-msg">${d.m}</span>
        <span class="log-status ${d.s}">${d.sl}</span>
      `;
      logEl.appendChild(row);
      logEl.scrollTop = logEl.scrollHeight;
      li++;
    }, 3200);
  }, delay + 2000);
</script>
</body>
</html>