"use client";

import React, { useState, useEffect, useRef } from "react";

const LOGS = [
  { agent: "SUPERVISOR", agClass: "agent-s", text: "Swarm initialized. 4 agents online. Cost budget: $10.00 per commit.", status: "READY", statusClass: "status-ok" },
  { agent: "FINDER",     agClass: "agent-d", text: "Analyzing commit a3f7c91 · diff +142 / -37 lines · api/routes.py", status: "SCANNING", statusClass: "status-info" },
  { agent: "FINDER",     agClass: "agent-d", text: "Semgrep + RAG pass complete. Potential SQLi in db.py:42 · Severity: HIGH", status: "FOUND", statusClass: "status-warn" },
  { agent: "EXPLOITER",  agClass: "agent-a", text: "Spinning up isolated Docker sandbox · no network · 256MB cap", status: "SANDBOX", statusClass: "status-info" },
  { agent: "EXPLOITER",  agClass: "agent-a", text: "SQLi confirmed · CWE-89 · CRITICAL · executing payload...", status: "CONFIRMED", statusClass: "status-crit" },
  { agent: "EXPLOITER",  agClass: "agent-a", text: "EXPLOIT_SUCCESS: Database dump confirmed · admin@example.com", status: "EXPLOITED", statusClass: "status-crit" },
  { agent: "ENGINEER",   agClass: "agent-b", text: "Applying parameterized query patch · surface: 18 lines", status: "PATCHING", statusClass: "status-info" },
  { agent: "ENGINEER",   agClass: "agent-b", text: "Patch complete. Generating unit tests for CWE-89 coverage.", status: "DONE", statusClass: "status-ok" },
  { agent: "VERIFIER",   agClass: "agent-c", text: "Re-running exploit against patched code... EXPLOIT_FAILED ✓", status: "PASS 1/3", statusClass: "status-ok" },
  { agent: "VERIFIER",   agClass: "agent-c", text: "Running test suite... 47/47 passed ✓", status: "PASS 3/3", statusClass: "status-ok" },
  { agent: "SUPERVISOR", agClass: "agent-s", text: "Verdict: APPROVED · PR #47 opened · Total cost: $4.21", status: "PATCHED", statusClass: "status-ok" },
];

const agentColors: Record<string, string> = {
  "agent-s": "#5A7A94",
  "agent-a": "#FF2B4A",
  "agent-b": "#4CB8FF",
  "agent-c": "#FFB800",
  "agent-d": "#B47FFF",
};

const statusColors: Record<string, { bg: string; color: string }> = {
  "status-ok":   { bg: "rgba(0,232,122,0.12)",   color: "#00E87A" },
  "status-warn": { bg: "rgba(255,184,0,0.12)",    color: "#FFB800" },
  "status-crit": { bg: "rgba(255,43,74,0.15)",    color: "#FF2B4A" },
  "status-info": { bg: "rgba(76,184,255,0.12)",   color: "#4CB8FF" },
};

function getTime() {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

export function SwarmTerminal() {
  const [lines, setLines] = useState<typeof LOGS>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      if (index < LOGS.length) {
        setLines(LOGS.slice(0, index + 1));
        index++;
      } else {
        setTimeout(() => { setLines([]); index = 0; }, 3000);
      }
    }, 900);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div className="aegis-terminal overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 16px",
        borderBottom: "1px solid var(--border)",
        background: "rgba(17,24,32,0.8)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#00E87A", display: "inline-block", animation: "pulse 2s infinite" }} />
          <span style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: "11px", color: "var(--muted)", letterSpacing: "0.15em", textTransform: "uppercase" }}>
            AGENT ACTIVITY FEED — LIVE
          </span>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ fontFamily: "var(--font-share-tech-mono)", fontSize: "10px", color: "var(--muted)" }}>
            {typeof window !== "undefined" ? getTime() : "--:--:--"}
          </span>
        </div>
      </div>

      {/* Log lines */}
      <div ref={scrollRef} style={{ maxHeight: "260px", overflowY: "auto", padding: 0 }}>
        {lines.map((line, i) => {
          const agColor = agentColors[line.agClass] ?? "#5A7A94";
          const sc = statusColors[line.statusClass] ?? { bg: "rgba(255,255,255,0.05)", color: "#5A7A94" };
          return (
            <div key={i} style={{
              display: "flex", alignItems: "flex-start", gap: 14,
              padding: "10px 16px",
              borderBottom: "1px solid rgba(30,45,61,0.4)",
              fontFamily: "var(--font-share-tech-mono)",
              fontSize: "12px",
              animation: "fadeInUp 0.3s ease both",
            }}>
              <span style={{ color: "var(--muted)", whiteSpace: "nowrap", minWidth: 60 }}>
                {getTime()}
              </span>
              <span style={{
                minWidth: 90, fontSize: "10px", letterSpacing: "0.1em",
                textTransform: "uppercase", padding: "2px 8px", textAlign: "center",
                background: `${agColor}18`, color: agColor,
              }}>
                {line.agent}
              </span>
              <span style={{ color: "var(--foreground)", flex: 1, lineHeight: 1.5 }}>
                {line.text}
              </span>
              <span style={{
                fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase",
                padding: "2px 10px", whiteSpace: "nowrap",
                background: sc.bg, color: sc.color,
              }}>
                {line.status}
              </span>
            </div>
          );
        })}
        {/* Blinking cursor */}
        <div style={{ padding: "10px 16px", fontFamily: "var(--font-share-tech-mono)", fontSize: "12px", color: "var(--muted)" }}>
          <span style={{ animation: "cursor-blink 1s step-end infinite", display: "inline-block", background: "#00E87A", width: 8, height: 14, verticalAlign: "text-bottom" }} />
        </div>
      </div>
    </div>
  );
}
