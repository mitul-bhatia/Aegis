"use client";

import { useEffect, useRef } from "react";

const THREATS = [
  { id: "CVE-2026-0381", msg: "CRITICAL · pyyaml RCE · EPSS 0.91" },
  { id: "AGENT-A", msg: "SQLi confirmed · repo: api-gateway · exploit in 4.2s" },
  { id: "CVE-2026-1142", msg: "HIGH · pillow heap overflow · EPSS 0.73" },
  { id: "AGENT-F", msg: "Path traversal detected · /uploads endpoint · auto-queued" },
  { id: "PATCH MERGED", msg: "CWE-89 remediated in 7m 22s · 0 test regressions" },
  { id: "CVE-2026-2049", msg: "CRITICAL · requests SSRF · EPSS 0.88" },
  { id: "AGENT-B", msg: "Parameterized query patch applied · 3 lines changed" },
  { id: "CVE-2026-0512", msg: "HIGH · flask debug RCE · EPSS 0.79" },
];

// Duplicate for seamless loop
const ALL = [...THREATS, ...THREATS];

export function ThreatBanner() {
  return (
    <div
      style={{
        background: "var(--red-dim)",
        borderBottom: "1px solid rgba(255,43,74,0.25)",
      }}
      className="flex items-center gap-0 overflow-hidden h-9 z-[200] relative"
    >
      {/* Label */}
      <div
        style={{
          fontFamily: "var(--font-share-tech-mono, monospace)",
          fontSize: "10px",
          color: "var(--red)",
          letterSpacing: "0.2em",
          border: "none",
          borderRight: "1px solid rgba(255,43,74,0.25)",
          whiteSpace: "nowrap",
          flexShrink: 0,
          padding: "0 16px",
          height: "100%",
          display: "flex",
          alignItems: "center",
        }}
      >
        ▸ LIVE THREATS
      </div>

      {/* Marquee track */}
      <div className="flex-1 overflow-hidden relative">
        {/* Fade edges */}
        <div className="pointer-events-none absolute left-0 top-0 h-full w-16 z-10"
          style={{ background: "linear-gradient(to right, var(--red-dim), transparent)" }} />
        <div className="pointer-events-none absolute right-0 top-0 h-full w-16 z-10"
          style={{ background: "linear-gradient(to left, var(--red-dim), transparent)" }} />

        <div
          className="flex gap-[60px] whitespace-nowrap"
          style={{ animation: "marquee 32s linear infinite" }}
        >
          {ALL.map((item, i) => (
            <span
              key={i}
              style={{
                fontFamily: "var(--font-share-tech-mono, monospace)",
                fontSize: "11px",
                color: "rgba(255,43,74,0.65)",
                letterSpacing: "0.06em",
              }}
            >
              <span style={{ color: "var(--red)", marginRight: "6px" }}>
                {item.id}
              </span>
              {item.msg}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
