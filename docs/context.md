# Aegis Build Walkthrough

I have completely implemented the Aegis Security System according to the `implementation_plan.md` and `docs/Phases.md`! All 9 phases of the project have been built out.

Here is a summary of what has been accomplished:

### ✅ Phase 0: Foundation
- Created the full directory structure (`agents/`, `rag/`, `sandbox/`, `github/`, `scanner/`, `tests/`).
- Set up a robust `config.py` to centrally manage environment variables and settings.
- Wrote the `requirements.txt`, `.env.example`, and `.gitignore`.
- Created an intentionally vulnerable `test_repo/app.py` with SQL injection bugs to be used for testing.

### ✅ Phase 1: GitHub Webhooks
- `github/webhook.py`: Created secure webhook signature verification and payload extraction.
- `main.py`: Created the FastAPI entry point that receives pushes from GitHub.

### ✅ Phase 2: Diff & Scanner
- `github/diff_fetcher.py`: Implemented logic to clone/pull repos and extract git diffs via the GitHub API.
- `scanner/semgrep_runner.py`: Integrated local Semgrep execution to scan changed files and format results for the LLM.

### ✅ Phase 3: RAG Memory
- `rag/indexer.py`: Built an AST parser that walks through Python files, extracts metadata (functions, classes, imports, flags for SQL/auth/HTTP), and indexes everything into a local ChromaDB instance.
- `rag/retriever.py`: Created semantic search to find relevant context when a commit is pushed.

### ✅ Phase 4: Agent A (The Hacker)
- `agents/hacker.py`: Set up the first AI agent using Anthropic's `claude-sonnet-4-20250514`. Enabled extended "thinking" budget so it can reason deeply about the diff, Semgrep findings, and RAG context before outputting a raw, executable Python exploit script.

### ✅ Phase 5: Docker Sandbox
- `sandbox/docker_runner.py`: Built the isolation layer. Exploits and unit tests are run inside restricted, rootless Docker containers with network access disabled (`network_mode="none"`), memory limits, and timeouts to safely execute AI-generated scripts without risking the host machine.

### ✅ Phase 6: Agent B (The Engineer)
- `agents/engineer.py`: Set up the second AI agent. It takes the vulnerable code and the proven exploit output, and writes a minimal security patch (e.g., using parameterized SQL queries) without altering existing function signatures.

### ✅ Phase 7: Agent C (The Reviewer)
- `agents/reviewer.py`: Implemented the automated verification and retry loop. It applies Agent B's patch, runs the repo's unit tests, and re-runs the exploit. If the tests fail or the exploit still works, it feeds the error logs back to Agent B for a retry (up to a configured maximum).

### ✅ Phase 8: GitHub PR Creator
- `github/pr_creator.py`: Built the final step of the pipeline. Creates a new branch, commits the verified patch, and opens a Pull Request on GitHub containing the proof of vulnerability (exploit output) and the fix.

### ✅ Phase 9: Orchestrator
- `orchestrator.py`: Wrote `run_aegis_pipeline`, which wires all the components together sequentially.
- `main.py`: Uncommented the background task execution so that when the FastAPI server receives a webhook, it triggers the full, autonomous Aegis pipeline.

---

> [!TIP]
> **To start testing the system yourself:**
> 1. Make sure you run `cp .env.example .env` and fill out your keys.
> 2. Ensure Docker Desktop is running locally.
> 3. Run individual phase tests using commands like `python tests/test_phase2.py` or `python tests/test_phase4.py`.
> 4. To start the full server: `python main.py`
