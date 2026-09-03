# AGENTS.md — Aegis

Entrypoint for AI agents working in this repository (Cursor and others). Model-agnostic: Grok, Composer, Claude, etc.

## Read first

1. **[`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md)** — canonical stage, as-built paths, deploy map, WIP, ship checklist.
2. **[`.cursor/rules/`](.cursor/rules/)** — always-on + scoped rules.
3. **[`RALPH_TASK.md`](RALPH_TASK.md)** + **[`.ralph/`](.ralph/)** — when looping / overnight autonomy.
4. **[`.agents/plugins/aegis-dev/rules/aegis-conventions.md`](.agents/plugins/aegis-dev/rules/aegis-conventions.md)** — security + agent contracts (when present).

Also: [`CLAUDE.md`](CLAUDE.md), [`GEMINI.md`](GEMINI.md).

## Stack layers (how you are customized)

| Layer | What | Persists across models? |
|-------|------|-------------------------|
| Project memory | `docs/PROJECT_MEMORY.md` | Yes (git) |
| Aegis rules | `aegis-core` / backend / frontend `.mdc` | Yes |
| Karpathy 4 | `.cursor/rules/karpathy-guidelines.mdc` | Yes |
| Engineering discipline 10 | `.cursor/rules/engineering-discipline.mdc` | Yes |
| Ralph loop | `RALPH_TASK.md`, `.ralph/`, scripts, `/ralph-loop` agent | Yes |
| Secrets | `.env` / Render / Vercel — values never in docs | Local / dashboards |

## Project in one paragraph

Aegis 2.0 finds vulns (Semgrep + Finder), pauses for approval/local sandbox verify, then Engineer → Reviewer → GitHub PR. Backend: `backend/app/`. Frontend: `aegis-frontend/`. Deploy: Render + Vercel.

## Hard rules

- Config via `backend/app/config.py` only in feature code.
- Never commit or document secret **values**; env **names** only.
- Do not relax Docker sandbox constraints or webhook signature verification.
- Prefer `docs/PROJECT_MEMORY.md` over stale architecture docs with wrong paths.
- Think → simple → surgical → verify (Karpathy / engineering-discipline).
- Keep changes minimal; update Stage snapshot in PROJECT_MEMORY when milestones land.

## Ralph loop (build until done)

**In Cursor Agent (works on Grok 4.5 now):**

- Ask: “Run one Ralph iteration” or invoke `/ralph-loop`
- Agent reads `RALPH_TASK.md` + `.ralph/*`, does next `[ ]`, verifies, updates progress

**Overnight CLI (needs `cursor-agent`):**

```bash
curl https://cursor.com/install -fsS | bash   # once
./scripts/ralph once -y
RALPH_MODEL=composer-2 ./scripts/ralph loop -n 20 -y
```

Default CLI model is `composer-2` (override with `RALPH_MODEL`). Switch models freely — state lives in files/git, not chat.

## Where to work

| Concern | Path |
|---------|------|
| API / webhooks | `backend/app/api/` |
| Agents | `backend/app/agents/` |
| Pipeline | `backend/app/pipeline/orchestrator.py` |
| RAG / Semgrep | `backend/app/rag/`, `backend/app/scanner/` |
| GitHub App | `backend/app/github/` |
| Sandbox CLI | `backend/runner/` |
| UI | `aegis-frontend/app/`, `lib/api.ts` |

## Local commands

```bash
./run-all.sh
./test-pipeline.sh
docker compose up -d
./scripts/ralph once -y
```

See PROJECT_MEMORY §6 for the full command set.
