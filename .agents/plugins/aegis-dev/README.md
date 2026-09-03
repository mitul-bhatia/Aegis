# aegis-dev — Antigravity CLI plugin

Built for Aegis 2.0 (autonomous vuln-remediation platform), matched to
the actual stack in your `docs/ARCHITECTURE.md` and `docs/tasks/PRD.md`.

## Install

Project-specific (recommended — this plugin is Aegis-specific, not
general-purpose):
```bash
mkdir -p /path/to/aegis/.agents/plugins
cp -r aegis-dev /path/to/aegis/.agents/plugins/
```

Or globally, if you want it available outside this repo too:
```bash
cp -r aegis-dev ~/.gemini/config/plugins/
```

Restart `agy` in the project directory. It should auto-discover the
plugin; confirm with `/agents` (you should see the 5 subagents listed)
and `/mcp` (you should see github, postgres, redis, semgrep, context7,
playwright).

## Before first use — set these env vars

```bash
export GITHUB_TOKEN=ghp_...          # fine-grained PAT, repo+PR scope, your dev/test repo only
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aegis
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
```

These are your **dev-loop credentials** for driving the CLI — separate
from `GITHUB_APP_ID` / `GITHUB_APP_PRIVATE_KEY` / `GROQ_API_KEY` in
Aegis's own `.env`, which the app uses at runtime. Don't reuse the App
private key here.

The redis MCP entry runs via `docker run mcp/redis` — needs Docker
running locally. If you'd rather not pull that image, delete the
`redis` block from `mcp_config.json`; nothing else depends on it.

## What's NOT in here, on purpose

- **No filesystem MCP.** `agy` already has native file read/write —
  adding a redundant MCP for that just burns tokens on tool-call
  overhead for zero new capability.
- **No cloud (Render/Vercel/AWS) MCP.** Your deployment surface is small
  enough that a misconfigured cloud MCP is more risk than it's worth
  right now. Add one later if deploy debugging becomes a real time sink.
- **No agent that "writes the whole app."** Each subagent is scoped to
  one real module boundary from your architecture doc, on purpose — a
  subagent with an unbounded scope is exactly how you get more of the
  "shittily built" problem, just faster.

## Using it

`/agents` to see the list, or just describe the work — the main agent
should delegate to the right one based on the `description` fields
(e.g. "the sandbox is leaking network access" routes to
`sandbox-security-auditor`; "PR creation is silently failing" routes to
`github-app-specialist`).

The `aegis-conventions` rule is inherited by all five, so none of them
should independently rediscover (or accidentally violate) your security
constraints and output contracts each time.
