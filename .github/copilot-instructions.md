# Aegis Copilot Instructions

## Project Purpose
Aegis is an autonomous white-hat remediation pipeline for GitHub push events.
It detects vulnerabilities, validates exploitability in a sandbox, generates fixes, verifies them, and can open a PR.

## Architecture Map
- FastAPI entrypoint: main.py
- Pipeline coordinator: orchestrator.py
- GitHub webhook parsing and signature checks: github_integration/webhook.py
- GitHub diff and PR operations: github_integration/diff_fetcher.py, github_integration/pr_creator.py
- Scanner: scanner/semgrep_runner.py
- RAG: rag/indexer.py, rag/retriever.py
- Sandbox: sandbox/docker_runner.py
- Agents: agents/hacker.py, agents/engineer.py, agents/reviewer.py
- Global config and env loading: config.py

## Required Development Conventions
- Read environment settings from config.py, not direct os.getenv calls in feature code.
- Keep pipeline flow centralized in orchestrator.py.
- Log significant phase transitions and failure reasons.
- Preserve security-first behavior: verify before patching, patch before PR, fail closed when unsure.
- Prefer minimal, targeted changes over broad refactors.

## Import Conventions
- Local GitHub integration package is github_integration.
- PyGithub client import is from github import Github.
- Do not rename imports in a way that reintroduces module shadowing.

## Local Run Commands
- Install deps: /Users/mitulbhatia/Desktop/Aegis/.venv/bin/python -m pip install -r requirements.txt
- Start app: /Users/mitulbhatia/Desktop/Aegis/.venv/bin/python main.py
- Health check: curl -s http://127.0.0.1:8000/health

## Testing
- Run focused tests with the project venv python and pytest, for example:
  - /Users/mitulbhatia/Desktop/Aegis/.venv/bin/python -m pytest tests/test_phase2.py
- When modifying pipeline behavior, update or add tests under tests/.

## Docs Sync
When behavior changes in core flow, update docs/Phases.md and docs/context.md accordingly.
