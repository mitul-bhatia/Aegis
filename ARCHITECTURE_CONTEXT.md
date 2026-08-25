# 1. Executive Summary

Aegis is an autonomous AI-driven application security platform. It acts as an automated security engineer that continuously monitors GitHub repositories, identifies vulnerabilities using static analysis (Semgrep), verifies their exploitability using a secure Docker sandbox, generates a patch, validates the fix, and automatically opens a Pull Request on GitHub. The system is built around a multi-agent orchestration loop (LangGraph) backed by a Python FastAPI backend and an asynchronous Redis worker queue.

# 2. System Purpose

The system exists to fully automate the vulnerability remediation lifecycle. Instead of merely alerting developers to a security flaw (like Dependabot or traditional SAST tools), Aegis aims to prove the vulnerability is real (reducing false positives via an Exploiter agent) and write the code to fix it (via an Engineer agent).

# 3. Repository Structure

- `main.py`: FastAPI application entry point.
- `orchestrator.py`: Invokes the LangGraph pipeline and manages agent state transitions.
- `worker.py`: Background Redis Queue (RQ) worker that executes the pipeline asynchronously.
- `config.py`: Centralized environment configuration.
- `pipeline/`: Defines the LangGraph nodes and execution graph.
- `agents/`: Contains the logic and prompts for the LLM agents (Finder, Exploiter, Engineer, Reviewer, PR Creator).
- `rag/`: ChromaDB vector database indexer and search logic for providing codebase context to agents.
- `scanner/`: Wrappers for static analysis tools (Semgrep).
- `sandbox/` & `sandbox-service/`: Ephemeral Docker environment management for safely testing exploits.
- `github_integration/`: GitHub App authentication (JWT/Installation tokens), webhooks, and PR creation.
- `database/`: SQLAlchemy ORM models and connection logic (Supabase PostgreSQL).
- `routes/`: API endpoints for the frontend (FastAPI routers).
- `scheduler_module/`: Intelligent ping-loop scheduler for continuous repository monitoring.
- `aegis-frontend/`: Next.js 14 frontend dashboard for managing scans and viewing vulnerabilities.

# 4. Architecture Overview

Aegis follows an event-driven, asynchronous architecture:
1. **Trigger:** A webhook from GitHub (e.g., a push event) or a scheduled cron job hits the FastAPI backend.
2. **Queueing:** The backend creates a `Scan` record in the database and enqueues a job to the Redis worker queue.
3. **Orchestration:** The `worker.py` picks up the job and starts the LangGraph state machine (`orchestrator.py`).
4. **Agent Loop:** The state machine cycles through a deterministic set of phases (Pre-process -> Finder -> Exploiter -> Engineer -> Verifier -> PR Creator).
5. **Reporting:** Results are written to the Supabase database and pushed to GitHub as a Pull Request.

# 5. Component Map

- **API Layer (FastAPI):** Handles webhooks and UI requests.
- **Worker Layer (RQ/Redis):** Decouples heavy LLM operations from the web thread.
- **Orchestrator (LangGraph):** The brain of the system, managing the state dictionary (`AegisState`) passed between agents.
- **LLM Agents (Groq):** Powered by fast open-source models via the Groq API.
- **RAG Engine (ChromaDB + SentenceTransformers):** Ingests the target repository so agents can search for related code files.
- **Execution Sandbox (Docker):** A heavily restricted, ephemeral container where the Exploiter agent runs untrusted exploit code.

# 6. Request / Execution Flows

**End-to-End Scan Flow:**
1. User clicks "Scan" in Frontend → `routes/scans.py` handles the POST request.
2. `worker.py` dequeues the task and calls `run_aegis_pipeline()` in `orchestrator.py`.
3. `pre_process_node`: Clones the repo to the worker's disk (`github_integration/diff_fetcher.py`), indexes the codebase into ChromaDB (`rag/indexer.py`), and runs Semgrep (`scanner/semgrep_runner.py`).
4. `finder_node`: LLM analyzes Semgrep findings and uses RAG to understand the surrounding context.
5. `exploiter_node`: LLM writes a Python exploit script. The script is sent to the Sandbox. If the exploit fails, it may retry.
6. `engineer_node`: LLM writes a patch for the vulnerable files.
7. `verifier_node`: The exploit is run *again* against the patched code. If it still works (patch failed), the `reviewer_node` diagnoses the failure and loops back to the Engineer.
8. `pr_creator_node`: If the patch is verified, a Pull Request is opened on GitHub.

# 7. Data Flow

The core data structure is the `AegisState` dictionary defined in `pipeline/nodes.py`. 
State transitions:
- Raw repository files → RAG Index (ChromaDB)
- Semgrep Output + RAG Context → Finder Agent → `vulnerabilities` list in State.
- `vulnerabilities` → Exploiter Agent → `exploit_code` and `exploit_success` flag in State.
- `vulnerabilities` → Engineer Agent → `patch` in State.

# 8. APIs and Interfaces

- **Internal API:** FastAPI routes under `routes/` (e.g., `/api/v1/repos`, `/api/v1/scans`) consumed by the Next.js frontend.
- **GitHub API:** Consumed via `PyGithub` for cloning, fetching diffs, and creating PRs. Authentication is done via short-lived GitHub App Installation Tokens (`github_integration/app_auth.py`).
- **Groq API:** Consumed via the official `groq` Python client for all agentic generation.
- **Sandbox API:** The worker communicates with the sandbox via HTTP or direct Docker socket commands.

# 9. Data Storage

- **Primary DB (Supabase PostgreSQL):** Stores `User`, `Repository`, `Scan`, and `Vulnerability` models (`database/models.py`).
- **Vector DB (ChromaDB):** Stores chunked AST/code representations. Runs entirely locally on the worker node's ephemeral disk (`aegis_vector_db/`). It is rebuilt dynamically on each scan.
- **Cache/Queue (Redis):** Stores job references, active scan statuses, and Celery/RQ metadata.

# 10. External Services

- **GitHub:** Source code hosting, webhook provider, and PR destination.
- **Render:** Cloud hosting platform (Web Service, Background Worker, Redis instance).
- **Supabase:** Managed PostgreSQL database.
- **Groq:** Fast LLM inference provider (Llama-3/Mixtral models).

# 11. Configuration and Environment

Environment variables are strictly parsed in `config.py`.
Critical variables:
- `DATABASE_URL`: Supabase connection string.
- `REDIS_URL`: Redis queue connection string.
- `GROQ_API_KEY`: For agent inference.
- `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `WEBHOOK_SECRET`: For GitHub App integration.
- `RENDER`: Boolean flag to enable production safety checks (e.g., enforcing PostgreSQL).

# 12. Dependency Map

- `fastapi`, `uvicorn`: Web framework.
- `rq`, `redis`: Background job queue.
- `langgraph`, `langchain`: Agent state machine orchestration.
- `groq`: LLM client.
- `chromadb`, `sentence-transformers`: Local RAG engine.
- `PyGithub`: GitHub API wrapper.
- `sqlalchemy`, `psycopg2-binary`: Database ORM.

# 13. Deployment Architecture

Deployed on **Render** using multiple services defined in `render.yaml`:
- **Web Service:** Runs the FastAPI backend.
- **Worker Service:** Runs `worker.py` (consumes from Redis).
- **Redis:** Managed internal instance.
The Frontend (Next.js) is deployed separately on **Vercel**.

# 14. Authentication and Security

- **User Auth:** Currently implicit or handled via frontend mechanisms mapping to GitHub OAuth.
- **App Auth:** Aegis authenticates to GitHub as a GitHub App using JWTs. This allows it to request short-lived installation access tokens (`app_auth.py`), completely avoiding static Personal Access Tokens (PATs).
- **Sandbox Security:** The exploiter agent's code is executed in an isolated Docker container (`Dockerfile.sandbox`) with no network access to the internal backend database, preventing the AI from attacking the host system.

# 15. Concurrency / Async / Background Processing

The FastAPI endpoints are lightweight and immediately return `202 Accepted` after pushing a job to Redis. The `worker.py` runs a continuous polling loop, executing the heavy LangGraph nodes synchronously (or via `asyncio` where appropriate within the graph execution) in the background.

# 16. Error Handling and Resilience

- **Database:** `database/db.py` enforces a strict check preventing deployment on Render without a valid PostgreSQL URL to prevent catastrophic data loss from ephemeral SQLite wipes.
- **Git Operations:** `diff_fetcher.py` forces `GIT_TERMINAL_PROMPT=0` and a hard `timeout=60` to ensure background workers do not hang indefinitely on authentication failures.
- **Agent Loops:** LangGraph implements `max_retries` for nodes (e.g., the Exploiter retrying if a payload fails, or the Engineer retrying if the Reviewer rejects the patch).

# 17. Testing Architecture

- A `tests/` directory exists for standard Pytest unit tests, though the system heavily relies on live end-to-end testing against dummy repositories (e.g., `mitu1046/aegis-test-repo`) during development.

# 18. Important File-by-File Map

- `pipeline/nodes.py`: The most critical file. Defines exactly what happens in every stage of the pipeline.
- `agents/engineer.py`: Contains the intricate system prompt instructing the LLM on how to generate safe, syntactically correct Python patches based on the vulnerability context.
- `github_integration/diff_fetcher.py`: Handles downloading the repository to the worker's local disk securely without hanging.
- `scheduler_module/intelligent_scheduler.py`: A daemon thread that periodically queries the database for active installations and triggers scans.

# 19. Critical Code Paths

**The Orchestrator Loop (`orchestrator.py` & `pipeline/nodes.py`):**
```python
workflow = StateGraph(AegisState)
workflow.add_node("pre_process", pre_process_node)
workflow.add_node("finder", finder_node)
workflow.add_node("exploiter", exploiter_node)
workflow.add_node("engineer", engineer_node)
workflow.add_node("verifier", verifier_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("pr_creator", pr_creator_node)

# Conditional Edges for looping
workflow.add_conditional_edges("exploiter", check_exploit_success, {"engineer": "engineer", "exploiter": "exploiter"})
workflow.add_conditional_edges("verifier", check_verification, {"pr_creator": "pr_creator", "reviewer": "reviewer"})
```
This graph defines the exact lifecycle. Any architectural change to the pipeline flow MUST happen here.

# 20. Architectural Decisions Already Present

1. **Local ChromaDB over Managed Cloud Vector DB:** Chosen to reduce latency, cost, and complexity. Since context only matters for the duration of a single scan, ephemeral local storage is sufficient and ideal.
2. **LangGraph over raw LangChain/AutoGen:** Chosen for deterministic state management. LangGraph forces the agents into a strict finite state machine, preventing infinite loops and chaotic LLM hallucinations.
3. **RQ/Redis over Celery:** Chosen for simplicity and ease of integration on Render's free tier, avoiding the heavy overhead of RabbitMQ/Celery brokers.

# 21. Technical Debt

- **Sandbox Complexity:** Depending on how the sandbox is hosted (DinD vs remote service), scaling workers requires careful orchestration of the Docker daemon.
- **RAG Model Fallback:** If `sentence-transformers` is unavailable or causes OOM on small instances, ChromaDB falls back to default ONNX embeddings, which can spike memory usage during cold starts.

# 22. Architectural Risks

- **Memory Constraints:** Running LLM inference (via API), ChromaDB indexing, and Semgrep concurrently on a 512MB RAM Render worker can lead to OS OOM-kills.
- **Rate Limits:** Aggressive RAG chunking and agent retries can quickly exhaust Groq API rate limits (tokens per minute).

# 23. Assumptions You Had To Infer

- I assume the Sandbox environment requires Docker-in-Docker (DinD) or a sidecar container to run the `Dockerfile.sandbox` securely in a cloud environment like Render.
- I assume the `mitu1046/mitu1046` and similar repositories are public or that the GitHub App has been granted strict read/write access to them.

# 24. Unknowns / Missing Information

- How the Sandbox is strictly isolated on Render (as Render natively runs containers, spawning sibling containers requires specific privileged setups).

# 25. Architectural Change Constraints

- **No State Mutations Outside the Graph:** All data passed between agents must go through the `AegisState` typed dictionary. Global variables cannot be used due to the distributed nature of the Redis workers.
- **Stateless Workers:** Any new files created during a scan (cloned repos, RAG indexes) must be treated as highly ephemeral. The worker container can reboot at any time.

# 26. Questions A Senior Architect Should Ask Before Changing This System

- Are we hitting Groq API rate limits during complex Engineer/Reviewer loops? Should we implement exponential backoff in the LLM wrapper?
- Is the Redis worker queue persisting jobs across deployments, or are active scans silently failing when Render deploys a new version?
- Can the Exploiter agent accidentally cause a Denial of Service against the target API if it hallucinates a recursive loop in its exploit script?

# 27. Architectural Mental Model

**Scan Trigger via GitHub Push:**
GitHub Webhook
→ FastAPI Backend (`routes/github.py`)
→ Supabase (Create `Scan` record)
→ Redis (Enqueue Task)
→ Return 202 OK to GitHub

**Background Scan Execution:**
Redis Queue
→ `worker.py` (Dequeues Task)
→ `orchestrator.py` (Starts LangGraph)
→ `pre_process_node` (git clone, Semgrep, ChromaDB Index)
→ `finder_node` (Groq API + ChromaDB query)
→ `exploiter_node` (Groq API + Docker Sandbox execution)
→ `engineer_node` (Groq API)
→ `verifier_node` (Docker Sandbox execution against patched code)
→ `pr_creator_node` (PyGithub API to open Pull Request)
→ Supabase (Update `Scan` status to Completed)
