# Aegis Frontend Redesign — Phased Implementation Plan

> **Reference**: All visual decisions derive from `Design.md` (the HTML mockup).
> **Stack**: Next.js 14 App Router · Tailwind CSS · shadcn/ui · next-themes · lucide-react
> **Theme**: Dark/Light mode toggle. Dark follows `Design.md` exactly. Light = crisp white + same semantic accents.

---

## Design Philosophy (from Design.md Analysis)

| Token | Value |
|---|---|
| Display font | `Syne` — bold, geometric headings |
| Mono font | `Share Tech Mono` — all data, labels, code, timestamps |
| Body font | `DM Sans` — readable body copy |
| Dark BG | `#06080B` → `#0C1017` → `#111820` (3-level depth) |
| Light BG | `#F8FAFC` → `#FFFFFF` → `#F1F5F9` |
| Green (primary) | `#00E87A` — success, active, operational |
| Red (exploiter) | `#FF2B4A` — threats, exploit confirmed |
| Blue (info) | `#4CB8FF` — engineer, info states |
| Amber (review) | `#FFB800` — verifier, warnings |
| Muted text | `#5A7A94` dark / `#64748B` light |
| Border | `#1E2D3D` dark / `#E2E8F0` light |
| Border radius | `4px` — sharp, professional (not pill-shaped) |
| Buttons | Rectangular, monospace label, uppercase, `letter-spacing: 0.1em` |

### Anti-Patterns to Avoid (what makes it look "AI-generated")
- No giant gradient blobs floating in background
- No rounded-2xl on everything — use sharp 4px corners
- No generic purple/blue color scheme — stick to Design.md palette
- No excessive glassmorphism everywhere — use it sparingly for nav only
- No generic hero with just text — must have live interactive element
- No flat sans-serif badges — use monospace font for all status/data labels

---

## Phase 1 — Design System Foundation
**Files**: `globals.css`, `tailwind.config.js`
**Goal**: Get all tokens, keyframes, and utility classes perfectly matching Design.md.

### 1.1 — CSS Variables Overhaul (`globals.css`)

**Dark Mode** (`:root` with `class="dark"` strategy):
```css
--background:  #06080B;
--surface:     #0C1017;
--card:        #111820;
--border:      #1E2D3D;
--foreground:  #E8EFF7;
--muted:       #5A7A94;

/* Semantic accents */
--green:       #00E87A;
--green-dim:   rgba(0,232,122,0.12);
--red:         #FF2B4A;
--red-dim:     rgba(255,43,74,0.12);
--blue:        #4CB8FF;
--blue-dim:    rgba(76,184,255,0.12);
--amber:       #FFB800;
--amber-dim:   rgba(255,184,0,0.12);

/* Agent identity */
--agent-finder:    #B47FFF;  /* violet */
--agent-exploiter: #FF2B4A;  /* red */
--agent-engineer:  #FFB800;  /* amber */
--agent-verifier:  #00E87A;  /* green */
```

**Light Mode** (`:root` default, dark applied via `.dark` class):
```css
--background:  #F8FAFC;
--surface:     #FFFFFF;
--card:        #F1F5F9;
--border:      #E2E8F0;
--foreground:  #0F172A;
--muted:       #64748B;

/* Same semantic accents — slightly deeper for contrast */
--green:       #00C96A;
--green-dim:   rgba(0,201,106,0.10);
--red:         #E8192C;
--red-dim:     rgba(232,25,44,0.10);
--blue:        #2B9FE8;
--blue-dim:    rgba(43,159,232,0.10);
--amber:       #D49700;
--amber-dim:   rgba(212,151,0,0.10);
```

**Required Keyframes** (keep existing, add missing):
- `gridShift` — hero grid background drift (20s linear infinite)
- `scanDown` — scanning line from top to bottom
- `pulse` — dot pulse (2s ease-in-out)
- `marquee` — threat banner scroll
- `arrowPulse` — pipeline arrow glow
- `fadeInUp` — log entry entrance (0.4s)
- `shimmerSweep` — CTA button hover shimmer
- `pulse-ring` — agent active rings
- `pipeline-fill` — connector line fill left-to-right
- `scanline-drift` — terminal CRT scanline

**Required Utility Classes**:
- `.aegis-terminal` — dark terminal container with CRT scanlines
- `.aegis-grid-bg` — hero scanning grid pattern
- `.aegis-glass-nav` — frosted nav: `bg-[#06080B]/85 backdrop-blur-[12px]`
- `.aegis-card` — base card with `bg-card border border-border`
- `.aegis-btn-primary` — green fill, mono font, uppercase
- `.aegis-btn-ghost` — transparent, border, mono font
- `.aegis-btn-outline` — border only, hover: border-green
- `.aegis-status-dot` — pulsing colored dot
- `.aegis-section-tag` — `// TAG` label in mono green
- `.aegis-gradient-border` — animated gradient border wrapper
- `.aegis-noise` — SVG noise overlay for premium texture
- `.aegis-active-scan` — glowing border animation for active scan cards

### 1.2 — Tailwind Config Update (`tailwind.config.js`)

Add to `theme.extend`:
```js
colors: {
  // Map all CSS vars
  green: 'var(--green)',
  'green-dim': 'var(--green-dim)',
  red: 'var(--red)',
  'red-dim': 'var(--red-dim)',
  // ... all semantic colors
  'agent-finder': 'var(--agent-finder)',
  'agent-exploiter': 'var(--agent-exploiter)',
  'agent-engineer': 'var(--agent-engineer)',
  'agent-verifier': 'var(--agent-verifier)',
},
borderRadius: {
  DEFAULT: '4px',
  sm: '2px',
  md: '4px',
  lg: '6px',
  xl: '8px',
},
fontFamily: {
  sans:    ['var(--font-dm-sans)', 'sans-serif'],
  mono:    ['var(--font-share-tech-mono)', 'monospace'],
  display: ['var(--font-syne)', 'sans-serif'],
},
```

---

## Phase 2 — Global Shell Components
**Files**: `components/ThreatBanner.tsx`, `components/GlobalNav.tsx`, `components/Footer.tsx`, `app/layout.tsx`
**Goal**: Every page gets the threat banner + blurred nav + footer shell.

### 2.1 — ThreatBanner Component
Matches Design.md exactly:
- `background: var(--red-dim)` · `border-bottom: 1px solid rgba(255,43,74,0.3)`
- Left: `[LIVE THREATS]` label in red mono box
- Right: Infinite marquee with real CVE data items
- Items format: `<span class="accent">CVE-2026-XXXX</span> CRITICAL · description · EPSS 0.91`
- Full-width, always on top (z-index 200), fixed position

### 2.2 — GlobalNav Component (NEW — for app pages)
Fixed, frosted-glass navigation:
- `position: fixed; top: [threat-banner-height]; left: 0; right: 0;`
- `background: rgba(6,8,11,0.85); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border);`
- Left: `AEGIS` logo in Syne Bold with green accent letter
- Center: Nav links in Share Tech Mono, uppercase, muted → green on hover
- Right: ThemeToggle + user avatar + Sign out

### 2.3 — ThemeToggle Component
Replace current basic toggle with Design.md-styled component:
- Icon-only button with `Sun` / `Moon` icon
- No label, just icon in a bordered square button (not rounded)
- Smooth icon transition animation
- Respects `--border` and `--foreground` tokens

### 2.4 — Footer Component
Matches Design.md footer:
- `border-top: 1px solid var(--border); padding: 32px 48px;`
- Left: `AEGIS` logo in muted
- Center: version + copyright in mono
- Right: links in mono
- No heavy multi-column footer on app pages — just this slim one-liner

### 2.5 — Layout.tsx Update
```
ThreatBanner (fixed, z-200)
GlobalNav    (fixed, z-100, top = threat banner height)
{children}   (padding-top = threat banner + nav height)
Footer
```

---

## Phase 3 — Landing Page Complete Overhaul
**File**: `app/page.tsx`
**Goal**: Match Design.md hero section structure + agent grid + pipeline + stats.

### 3.1 — Hero Section
Structure from Design.md:
```
[Corner TL]                    [Corner TR]
         [Scanning grid background]
         [Scan line animating down]

  [• SYSTEM OPERATIONAL · 4 Agents Active]   ← hero-status badge

  Autonomous
  VULNERABILITY                              ← green em block
  Remediation

  // White-Hat AI Swarm · v2.0 · April 2026  ← hero-sub in mono muted

  [4-agent AI pipeline... description]

  [VIEW LIVE DASHBOARD →]  [Read Architecture Docs]

  ┌─────────┬─────────┬─────────┬─────────┐
  │  71%    │  45m    │ $152    │  54M    │   ← hero-metrics bar
  │ Patch % │ Avg Fix │ Per Fix │ Lines   │
  └─────────┴─────────┴─────────┴─────────┘

[Corner BL]                    [Corner BR]
```

Implementation details:
- Corner brackets: `position: absolute` divs with `border-top + border-left` (2px solid green)
- Hero grid: CSS `background-image` repeating linear gradients at 60px × 60px, animated with `gridShift`
- Scan line: `position: absolute; height: 2px; background: linear-gradient(90deg, transparent, green, transparent); animation: scanDown 4s infinite`
- Hero status: green mono badge with pulsing dot
- H1: Syne 800, `clamp(44px, 7vw, 90px)`, line-height 1.0, letter-spacing -0.02em; `em` tag = green block
- Subline: Share Tech Mono, 12px, muted, `// ...` prefix
- Metrics bar: full-width, `border: 1px solid var(--border)`, `background: var(--surface)`, equal flex cells with `border-right` dividers. Numbers in Syne 700 36px, labels in mono muted uppercase

### 3.2 — Live Activity Feed
Below hero, full-width container:
- Header row: `● AGENT ACTIVITY FEED — LIVE` + clock
- Scrollable log list, auto-advancing every 3.2s
- Each entry: `[timestamp] [AGENT TAG] [message with colored spans] [STATUS]`
- Agent tag colors: red=exploiter, blue=engineer, amber=verifier, green=finder/supervisor
- Status pills: `SCANNING` `EXPLOITING` `PATCHED` `CONFIRMED` in matching dim backgrounds

### 3.3 — Agent Showcase Grid
Matches Design.md agent-card grid exactly:
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ A · red      │ B · blue     │ C · amber    │ D · green    │
│ ──────────── │ ──────────── │ ──────────── │ ──────────── │
│ ⚡ icon      │ ⚙ icon      │ ✓ icon      │ ⬡ icon      │
│ The Finder   │ The Engineer │ The Verifier │ Taint Analyst│
│ EXPLOIT GEN  │ PATCH GEN    │ VALIDATION   │ MULTI-FILE   │
│ description  │ description  │ description  │ description  │
│ [model tag]  │ [model tag]  │ [model tag]  │ [model tag]  │
│            A │            B │            C │            D │ ← large faint bg letter
└──────────────┴──────────────┴──────────────┴──────────────┘
```
- Grid: `display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1px; background: var(--border);`
- Each card: `background: var(--card); padding: 36px 32px;`
- Top accent line: `position: absolute; top: 0; height: 2px; background: var(--agent-color);` — thickens to 3px on hover
- Agent ID row: `AGENT X` in mono with line extending after (::after `flex: 1; height: 1px; background: border`)
- Background letter: `position: absolute; right: 20px; bottom: 20px; font-size: 80px; opacity: 0.02;` in Syne

### 3.4 — Pipeline Visualization Section
Horizontal pipeline matching Design.md:
```
[GitHub Webhook] → [LangGraph Commander] → ┌[Taint Graph ]┐ → [Patch Engineer] → [Sandbox Review] → [Auto-Merge PR]
                                            ├[Exploit Gen  ]┤
                                            └[CVE Scan     ]┘
Feedback Loop ════════════════════════════════════════════════ C → B with patch-locked context
```
- Overflow-x: auto container
- Pipe nodes: bordered rectangles with label (mono) + name (Syne)
- Pipe arrows: `→` in mono green, `animation: arrowPulse 2s infinite`
- Feedback loop: dashed amber line below, mono label
- On hover: `border-color` transitions to node's accent color

### 3.5 — Stats Row
4 stats in bordered grid matching Design.md:
- Numbers: Syne 800, 52px
- Labels: mono 11px muted uppercase
- Background symbol (absolute, opacity 0.02): `!` `✓` `#` `$`

### 3.6 — Security Stack Section
2×2 grid of stack cells:
- Each cell: `background: var(--card); padding: 32px; border: 1px solid var(--border);`
- Title: Syne 700 18px + status tag pill (Critical/High Risk/Multi-Layer/Protocol-Level)
- Items: `▶` check in green/amber + bold label + description

### 3.7 — CTA Section + Footer
- CTA: centered, radial green glow from bottom, large Syne headline + 2 buttons
- Footer: slim, 3-column (logo · copyright · links)

---

## Phase 4 — Dashboard Page Redesign
**File**: `app/dashboard/page.tsx`
**Goal**: "Mission Control" feel. Bento grid. Dense data. Real-time.

### 4.1 — Stats Row (Top)
4 stat cells in Design.md `stats-row` style:
- Full width, 1px gap grid, `background: var(--border)` creates dividers
- Each: large display number + mono label + faint background symbol
- Values from real API (`/api/v1/stats`)
- Active scans stat: pulsing green dot when > 0

### 4.2 — Main Two-Column Bento Layout
```
┌─────────────────────────┬──────────────────────────────────────────┐
│   MONITORED REPOS       │   LIVE ACTIVITY                          │
│   [+ Monitor Repo]      │   ● 3 active · [search] [filter]        │
│                         │                                          │
│  ┌─────────────────┐    │  ┌──────────────────────────────────┐   │
│  │ org/repo-name   │    │  │ [EXPLOITER] a3f7c91 on main      │   │
│  │ monitoring ✓    │    │  │ SQL Injection · CRITICAL          │   │
│  │ [Scan] [Delete] │    │  │ 2m 34s                  [EXPLOIT] │   │
│  └─────────────────┘    │  └──────────────────────────────────┘   │
│                         │                                          │
│  [40% width]            │  [60% width]                             │
└─────────────────────────┴──────────────────────────────────────────┘
```

**Repo Card** (matches Design.md `stack-cell`):
- Sharp corners, `border: 1px solid var(--border)`, hover: border color = status color
- Status indicator: colored dot + mono status text
- Repo name: Syne medium
- Meta: mono muted (added date, last scan)
- Action buttons: `[SCAN ▶]` in mono, ghost style

**Scan Feed Card** (active vs completed):
- Active: `aegis-active-scan` animated border glow + agent avatar with pulse rings
- Agent message in small mono text
- Timer: monospace countdown in green
- Completed: muted border, no glow, timestamp
- Status badge: mono uppercase, colored background

### 4.3 — Filter Bar
Inside the scan feed panel:
- Search input: mono font, `border: 1px solid var(--border)`
- Status/Severity selects: matching border style
- Results count: mono muted right-aligned

---

## Phase 5 — Scan Detail Page Redesign
**File**: `app/scans/[id]/page.tsx`
**Goal**: Two-panel layout. Left = pipeline. Right = live agent content.

### 5.1 — Page Layout
```
┌────────────────────────────────────────────────────────────────────┐
│  ← Back  |  [commit sha]  on  [branch]  ·  [status badge]  ·  PR  │
├──────────────────────┬─────────────────────────────────────────────┤
│  PIPELINE TIMELINE   │  ACTIVE CONTENT PANEL                       │
│  [35% width]         │  [65% width]                                │
│                      │                                             │
│  ○ FINDER            │  Depends on status:                         │
│  │                   │  · scanning/exploiting → terminal output    │
│  ● EXPLOITER ←active │  · patching → code diff appearing           │
│  │                   │  · verifying → test results                 │
│  ○ ENGINEER          │  · fixed → PR card + patch diff             │
│  │                   │  · failed → error details                   │
│  ○ VERIFIER          │                                             │
│                      │                                             │
└──────────────────────┴─────────────────────────────────────────────┘
```

### 5.2 — Pipeline Timeline (Left Panel)
Vertical pipeline matching each agent stage:
- Each stage: circle icon + agent name + status
- Active stage: pulse-ring animation + live timer + agent message
- Completed stages: filled check, elapsed time, muted
- Connecting lines: fill from top to active stage with gradient animation
- Agent colors: violet=finder, red=exploiter, amber=engineer, green=verifier

### 5.3 — Right Panel Content (Status-driven)

**When scanning/exploiting** (`ExploitTerminal`):
- `.aegis-terminal` container: `background: #050508`, CRT scanline effect
- Header: `AGENT EXPLOIT TERMINAL` label + live timer
- Content: monospace green text with typewriter animation
- Danger lines: `VULNERABLE` in red, exploit output highlighted

**When patching** (Code editor feel):
- Show original file name + line range
- Engineer "writing" animation — code appears line by line
- `agent_message` shown as monospace status text

**When fixed** (PR card):
- `.aegis-gradient-border` animated wrapper
- PR link prominent, large Syne headline
- `CodeDiff` below: before/after syntax-highlighted diff
- Test results: pass/fail indicators per test

**When failed** (Error display):
- Red bordered box with error details
- `error_message` in mono
- Retry option button

### 5.4 — CodeDiff Component Redesign
- Two-panel: "Before" (left, red tinted) and "After" (right, green tinted)
- Line numbers in muted mono
- Diff computed client-side using simple line comparison
- Changed lines: `background: rgba(255,43,74,0.08)` for removed, `rgba(0,232,122,0.08)` for added
- Header: filename + `–N lines` / `+N lines` counter

### 5.5 — ExploitTerminal Component Redesign
- True terminal aesthetic: `background: #050508`, no rounded corners
- CRT scanline: animated pseudo-element drifting top→bottom
- Header bar: 3 dots (red/amber/green) + `EXPLOIT TERMINAL` mono label
- Output: green text, `VULNERABLE` in red, `SUCCESS` in amber
- Copy button: top right corner
- Typewriter effect on initial load via character-by-character reveal

---

## Phase 6 — Component Library Polish
**Goal**: Make every reusable component match Design.md tokens precisely.

### 6.1 — VulnCard Redesign
- Remove Card wrapper — use raw div with Design.md `stack-cell` style
- Header: commit sha (mono muted) + branch (mono green) + timestamp (mono right)
- Vulnerability row: type in Syne semibold + severity badge (mono colored)
- Status badge: full-width strip at bottom with agent color
- Active scans: AgentAvatar + LiveTimer inline

### 6.2 — AgentAvatar Component
Already exists — verify/polish:
- `sm` size: 28px circle, `md`: 40px, `lg`: 56px
- Background: `var(--agent-{name}-dim)`, border: `1px solid var(--agent-{name})`
- Icon: lucide icon in agent color
- `showRing`: adds `pulse-ring` + `pulse-ring-2` pseudo-elements
- Label (optional): mono 10px uppercase below

### 6.3 — StatCard Component
Match Design.md `stat-cell` exactly:
- Large number: Syne 800, 52px
- Background symbol: mono 100px, opacity 0.02, absolute top-right
- Label: mono 11px muted uppercase
- `isActive` prop: adds pulsing colored dot before label

### 6.4 — StatusBadge (Global pattern)
Replace all inline badge patterns with a single consistent component:
- Container: `inline-flex; font-family: mono; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; padding: 2px 10px;`
- Colors per status — all using `var(--X-dim)` backgrounds + `var(--X)` text
- NO rounded full pills — 2px border-radius max

### 6.5 — LiveTimer Component
Already exists — ensure it:
- Uses Share Tech Mono font
- Shows in green color when active
- Format: `2m 34s` or `47s`

### 6.6 — AddRepoModal Redesign
- Replace dialog backdrop with Design.md card style
- Header: Syne bold title + `[×]` close (mono)
- Input: full border, no rounded, placeholder in muted mono
- CTA: `.aegis-btn-primary` style
- Progress steps if indexing: numbered steps in mono

---

## Phase 7 — Analytics Page
**File**: `app/analytics/page.tsx`
**Goal**: Intelligence dashboard with charts in Design.md style.

### 7.1 — Layout
Full-width bento grid:
```
┌──────────────┬──────────────┬──────────────────────────────────────┐
│ MTTR         │ Fix Rate     │ VULN TREND CHART (30 days)           │
│ 14.2h        │ 87%          │ [bar chart: found vs fixed per day]  │
├──────────────┴──────────────┤                                      │
│ TOP VULNERABILITY TYPES     ├──────────────────────────────────────┤
│ [horizontal bar list]       │ SEVERITY DISTRIBUTION (donut chart)  │
└─────────────────────────────┴──────────────────────────────────────┘
```

### 7.2 — Chart Styling (Recharts)
- Background: `var(--surface)` — no white backgrounds
- Grid lines: `var(--border)` at 50% opacity
- Axis text: mono 10px muted
- Bar colors: green=fixed, red=found, amber=pending
- Tooltip: Design.md card style, mono font

---

## Phase 8 — Auth & Repo Pages
**Files**: `app/auth/callback/page.tsx`, `app/repos/[id]/page.tsx`

### 8.1 — Auth Callback
Loading state during OAuth:
- Full screen, centered `AEGIS` logo in Syne
- Pulsing scan line across screen
- Status: `// Authenticating with GitHub...` in mono green

### 8.2 — Repo Detail Page (`/repos/[id]`)
If page exists:
- Header: repo name + status + actions
- Scorecard: SecurityScorecard component
- Recent scans list using VulnCard
- Schedule info from SchedulerControl

---

## Phase 9 — Responsive & Mobile Polish
**Goal**: All pages work on 320px → 1440px+.

### Breakpoints
| Breakpoint | Changes |
|---|---|
| `< 768px` | Nav: hamburger menu. Hero: single column. Agent grid: 1 col. Pipeline: vertical stack |
| `768px-1024px` | Agent grid: 2 col. Dashboard: single column stacked |
| `> 1024px` | Full desktop layout as designed |

### Mobile-specific adjustments
- ThreatBanner: reduce marquee items
- Hero metrics: `grid-cols-2` on mobile, `grid-cols-4` on desktop
- Pipeline visualization: scroll horizontally with fade edges on mobile
- Dashboard: repos stacked above scan feed
- Scan detail: tabs instead of side-by-side panels on mobile

---

## Phase 10 — Performance & Final Polish

### 10.1 — Animation Performance
- All animations use `transform` and `opacity` only (GPU-composited)
- `will-change: transform` on scan line and marquee
- `prefers-reduced-motion` media query: disable all decorative animations

### 10.2 — Dark/Light Mode Transitions
- `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` on body
- Verify every component uses CSS vars (no hardcoded colors)
- Test each page in both modes

### 10.3 — Loading States
Every data-fetching section has:
- Skeleton using `animate-pulse` with Design.md card dimensions
- Skeleton color: `var(--border)` on `var(--surface)`

### 10.4 — Empty States
Each empty state panel uses Design.md dashed border pattern:
- `border: 1px dashed var(--border)`
- Centered mono icon + Syne title + muted description
- Action CTA button in `.aegis-btn-outline` style

---

## Execution Order

| Phase | Priority | Estimated Work | Dependency |
|---|---|---|---|
| **1** — Design System (globals.css + tailwind) | 🔴 Critical | 1.5h | None |
| **2** — Global Shell (Nav, ThreatBanner, Footer) | 🔴 Critical | 2h | Phase 1 |
| **3** — Landing Page | 🔴 Critical | 3h | Phase 2 |
| **4** — Dashboard | 🔴 Critical | 2.5h | Phase 1, 6 |
| **5** — Scan Detail Page | 🟡 High | 3h | Phase 1, 6 |
| **6** — Component Library | 🔴 Critical | 2h | Phase 1 |
| **7** — Analytics | 🟡 High | 2h | Phase 1 |
| **8** — Auth/Repo Pages | 🟢 Medium | 1h | Phase 2 |
| **9** — Responsive Polish | 🟡 High | 2h | All above |
| **10** — Final Polish | 🟢 Medium | 1h | All above |

**Total: ~20 hours of focused implementation**

**Critical path**: Phase 1 → 2 → 6 → 3 → 4 → 5

---

## Key Design Decisions (Why, Not Just What)

1. **Sharp corners (4px)** over rounded cards: Security/technical tools feel precise and professional, not soft/consumer. Linear, Vercel, and all major dev tools use tighter radii.

2. **Share Tech Mono for ALL data labels**: Every status, timestamp, number, tag must be monospace. This is what separates a security tool from a generic SaaS — data looks like data.

3. **1px border grid layout** (gap: 1px, background: border-color): The Design.md layout trick for creating seamless multi-cell grids without double borders. Used for agent cards, stats row, security stack.

4. **Agent identity over generic colors**: Every part of the UI where an agent is referenced must use that agent's specific color. When the UI turns red, users feel the exploit. When it turns green, they feel relief.

5. **No hero illustrations or stock graphics**: The live activity feed and pipeline demo ARE the hero. Real product functionality, not marketing imagery.

6. **Glassmorphism only for nav**: `backdrop-filter: blur(12px)` is reserved for the navigation bar only. Overusing it makes things look cheap and AI-generated.

7. **Light mode = same palette, brighter background**: NOT a washed-out pale version of dark mode. Accent colors stay vibrant, text stays dark and readable, borders are visible.
