# Phase 4 — Backend Infrastructure

> **Depends on:** Phase 1 complete
>
> **Estimated effort:** 3-4 days
>
> **Goal:** Production-harden the backend — event-driven SSE, API versioning, pagination, Alembic migrations, health checks.

---

## Task 4.1: Replace SSE DB Polling with Event Bus

**Files:** `routes/scans.py`, `orchestrator.py`

**Current problem:** SSE endpoint polls DB every 1 second per connected client. 20 users = 1,200 DB reads/minute.

**Steps:**
- [ ] Create `utils/event_bus.py`:
  ```python
  import asyncio
  from typing import Dict
  
  class ScanEventBus:
      def __init__(self):
          self._subscribers: Dict[int, list[asyncio.Queue]] = {}  # scan_id → [queues]
          self._global_subscribers: list[asyncio.Queue] = []
      
      def subscribe(self, scan_id: int = None) -> asyncio.Queue:
          queue = asyncio.Queue(maxsize=100)
          if scan_id:
              self._subscribers.setdefault(scan_id, []).append(queue)
          else:
              self._global_subscribers.append(queue)
          return queue
      
      def unsubscribe(self, queue: asyncio.Queue, scan_id: int = None):
          if scan_id and scan_id in self._subscribers:
              self._subscribers[scan_id] = [q for q in self._subscribers[scan_id] if q is not queue]
          self._global_subscribers = [q for q in self._global_subscribers if q is not queue]
      
      async def publish(self, scan_data: dict):
          scan_id = scan_data.get("id")
          # Notify scan-specific subscribers
          for queue in self._subscribers.get(scan_id, []):
              try:
                  queue.put_nowait(scan_data)
              except asyncio.QueueFull:
                  pass  # Drop oldest events for slow consumers
          # Notify global subscribers
          for queue in self._global_subscribers:
              try:
                  queue.put_nowait(scan_data)
              except asyncio.QueueFull:
                  pass
  
  event_bus = ScanEventBus()
  ```

- [ ] Update `orchestrator.py` `_broadcast()` to publish to the event bus:
  ```python
  def _broadcast(scan: Scan):
      import asyncio
      from utils.event_bus import event_bus
      data = {...}  # existing scan dict
      try:
          loop = asyncio.get_event_loop()
          loop.call_soon_threadsafe(asyncio.ensure_future, event_bus.publish(data))
      except RuntimeError:
          pass
  ```

- [ ] Rewrite `scan_event_generator()` in `routes/scans.py`:
  ```python
  async def scan_event_generator(repo_id: int = None):
      from utils.event_bus import event_bus
      queue = event_bus.subscribe()
      yield ": heartbeat\n\n"
      try:
          while True:
              try:
                  data = await asyncio.wait_for(queue.get(), timeout=30)
                  if repo_id and data.get("repo_id") != repo_id:
                      continue
                  yield f"data: {json.dumps(data)}\n\n"
              except asyncio.TimeoutError:
                  yield ": keepalive\n\n"  # Prevent connection timeout
      finally:
          event_bus.unsubscribe(queue)
  ```

**Verification:**
- SSE updates are instant (no 1-second delay)
- No DB queries from SSE endpoint
- Multiple frontend tabs all receive updates simultaneously

---

## Task 4.2: Add Alembic Database Migrations

**Files:** NEW `alembic.ini`, NEW `migrations/`, `database/db.py`

**Steps:**
- [ ] Install: `pip install alembic` (add to `requirements.txt`)
- [ ] Initialize: `alembic init migrations`
- [ ] Configure `alembic.ini`:
  ```ini
  sqlalchemy.url = sqlite:///./aegis.db
  ```
- [ ] Update `migrations/env.py` to import your models:
  ```python
  from database.db import Base
  from database.models import User, Repo, Scan  # Import all models
  target_metadata = Base.metadata
  ```
- [ ] Generate initial migration:
  ```bash
  alembic revision --autogenerate -m "initial_schema"
  ```
- [ ] Update `database/db.py` — remove `Base.metadata.create_all()`, add Alembic runner:
  ```python
  def init_db():
      """Run Alembic migrations to latest version."""
      from alembic.config import Config
      from alembic import command
      alembic_cfg = Config("alembic.ini")
      command.upgrade(alembic_cfg, "head")
  ```
- [ ] Add `migrations/` to git tracking (NOT in `.gitignore`)

**Verification:**
- Add a column to models → `alembic revision --autogenerate` creates migration
- `alembic upgrade head` applies it without data loss
- `alembic downgrade -1` reverts cleanly

---

## Task 4.3: Add API Versioning

**Files:** `main.py`, all route files

**Steps:**
- [ ] Rename all route prefixes: `/api/scans` → `/api/v1/scans`, etc.:
  ```python
  app.include_router(auth_router, prefix="/api/v1")     # was /api
  app.include_router(repos_router, prefix="/api/v1")
  app.include_router(scans_router, prefix="/api/v1")
  app.include_router(scheduler_router, prefix="/api/v1")
  app.include_router(intelligence_router, prefix="/api/v1")
  ```
- [ ] Update router prefixes in each route file to remove `/api` prefix (now provided by `main.py`)
- [ ] Update frontend `api.ts` to use `/api/v1/`:
  ```typescript
  const API_V1 = `${API_BASE}/api/v1`;
  ```
- [ ] Keep a v1 compatibility redirect for transition period

**Verification:**
- All endpoints work under `/api/v1/`
- Frontend still functions correctly
- Old `/api/` paths return 404

---

## Task 4.4: Add Rate Limiting

**Files:** `main.py`, `requirements.txt`

**Steps:**
- [ ] Install: `pip install slowapi`
- [ ] Add rate limiting to sensitive endpoints:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded
  
  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
  
  # In routes:
  @router.post("/trigger")
  @limiter.limit("5/minute")
  async def trigger_scan(request: Request, ...):
      ...
  
  @router.post("/auth/github")
  @limiter.limit("10/minute")
  async def github_oauth(request: Request, ...):
      ...
  ```

**Verification:**
- Trigger scan 6 times in 1 minute → 6th call returns 429 Too Many Requests
- Normal usage is not affected

---

## Task 4.5: Add Pagination to List Endpoints

**Files:** `routes/scans.py`, `routes/repos.py`

**Steps:**
- [ ] Add pagination to `GET /api/v1/scans`:
  ```python
  @router.get("/scans")
  async def list_scans(
      repo_id: int = None,
      page: int = Query(1, ge=1),
      per_page: int = Query(20, ge=1, le=100),
      status: str = None
  ):
      offset = (page - 1) * per_page
      query = db.query(Scan).order_by(Scan.created_at.desc())
      
      if repo_id:
          query = query.filter(Scan.repo_id == repo_id)
      if status:
          query = query.filter(Scan.status == status)
      
      total = query.count()
      scans = query.offset(offset).limit(per_page).all()
      
      return {
          "data": [_scan_to_dict(s) for s in scans],
          "pagination": {
              "page": page,
              "per_page": per_page,
              "total": total,
              "total_pages": math.ceil(total / per_page)
          }
      }
  ```
- [ ] Update frontend to handle paginated responses

**Verification:**
- With 50 scans, `?page=1&per_page=10` returns 10 items with `total_pages: 5`
- Frontend loads and displays correctly

---

## Task 4.6: Add Health Check & Readiness Endpoints

**Files:** `main.py`

**Steps:**
- [ ] Replace the basic `/health` with comprehensive checks:
  ```python
  @app.get("/health")
  async def health_check():
      checks = {}
      
      # Database
      try:
          db = SessionLocal()
          db.execute(text("SELECT 1"))
          checks["database"] = "healthy"
          db.close()
      except Exception as e:
          checks["database"] = f"unhealthy: {e}"
      
      # Docker
      try:
          import docker
          client = docker.from_env()
          client.ping()
          checks["docker"] = "healthy"
      except Exception:
          checks["docker"] = "unavailable"
      
      # Groq API
      checks["groq_api"] = "configured" if config.GROQ_API_KEY else "missing"
      checks["mistral_api"] = "configured" if config.MISTRAL_API_KEY else "missing"
      
      overall = "healthy" if all("unhealthy" not in v for v in checks.values()) else "degraded"
      return {"status": overall, "checks": checks, "version": "2.0.0"}
  
  @app.get("/ready")
  async def readiness():
      """Kubernetes readiness probe — fails if Docker unavailable."""
      try:
          import docker
          docker.from_env().ping()
          return {"ready": True}
      except Exception:
          raise HTTPException(503, "Docker unavailable")
  ```

**Verification:**
- `/health` returns status of all components
- `/ready` returns 503 when Docker is stopped

---

## Task 4.7: Add Structured Logging

**Files:** `config.py`, all Python files

**Steps:**
- [ ] Install: `pip install structlog`
- [ ] Create `utils/logging.py`:
  ```python
  import structlog
  import logging
  
  def setup_structured_logging():
      structlog.configure(
          processors=[
              structlog.contextvars.merge_contextvars,
              structlog.processors.add_log_level,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.dev.ConsoleRenderer()  # or JSONRenderer for production
          ],
          wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
      )
  ```
- [ ] Add scan_id correlation to pipeline logs:
  ```python
  import structlog
  log = structlog.get_logger()
  
  # At pipeline start:
  log = log.bind(scan_id=scan.id, repo=repo_full_name, commit=commit_sha[:8])
  log.info("pipeline.started")
  ```
- [ ] This can be done gradually — no need to replace every `logger.info()` at once

**Verification:**
- Pipeline logs show scan_id, repo, and commit on every line
- Logs are structured and easy to search

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 4.1 | Event-driven SSE | 🔴 Critical | `routes/scans.py`, `orchestrator.py`, NEW `utils/event_bus.py` |
| 4.2 | Alembic migrations | 🔴 Critical | NEW `alembic.ini`, `migrations/`, `database/db.py` |
| 4.3 | API versioning | 🟠 High | `main.py`, all routes, `api.ts` |
| 4.4 | Rate limiting | 🟠 High | `main.py` |
| 4.5 | Pagination | 🟠 High | `routes/scans.py`, `routes/repos.py` |
| 4.6 | Health checks | 🟡 Medium | `main.py` |
| 4.7 | Structured logging | 🟡 Medium | `config.py`, pipeline files |
