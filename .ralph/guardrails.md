# Ralph Guardrails (Signs)

> Lessons learned from failures. Each agent iteration MUST read this file.
> When you hit a failure mode, add a sign so future iterations don't repeat it.

## Aegis-specific signs

- Never relax sandbox constraints (`cap_drop ALL`, `network: none`, non-root).
- Never bypass GitHub webhook signature verification.
- Never commit secret values; env names only (see `docs/PROJECT_MEMORY.md`).
- Prefer `backend/app/` paths; ignore stale docs mentioning root `main.py` / `github_integration/` / ChromaDB as primary RAG.
- Config via `backend/app/config.py` (`settings`) only in feature code.
- Agent contract changes must update backend + frontend TS in the same change.

## Accumulated signs

- **Never add hardcoded webhook secret fallbacks** — use env-only `GITHUB_WEBHOOK_SECRET`; tests set `test_secret_123` via pipeline scripts.
- **Pipeline scripts on port 8081**: use `free_port` + trap cleanup; otherwise adversarial suite races and flakes.
- **E2E tests**: seed a user + pass `Authorization: Bearer {id}` after removing dev auth fallbacks.
- **Docker sandbox blackbox tests**: skip when `docker info` fails; keep static `aegis_cli.py` isolation-flag test always on.
