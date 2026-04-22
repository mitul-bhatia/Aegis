"""
Aegis — Centralized Configuration

All settings are loaded once from environment variables.
Import this module instead of calling os.getenv() everywhere.
"""

import os
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# ── API Keys ──────────────────────────────────────────────
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── GitHub OAuth (for multi-user sign-in) ─────────────────
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Model Settings ────────────────────────────────────────
# Agent A (Hacker): Codestral — fast, cheap, code-focused, minimal guardrails
HACKER_MODEL = os.getenv("HACKER_MODEL", "codestral-2508")

# Agent B (Engineer): Devstral 2 — frontier agentic coding model
ENGINEER_MODEL = os.getenv("ENGINEER_MODEL", "devstral-2512")

# ── Server Settings ───────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))

# ── Paths ─────────────────────────────────────────────────
REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "aegis_vector_db")

# ── Scanner Settings ───────────────────────────────────────
# Optional absolute path to Semgrep binary. If unset, Aegis auto-detects.
SEMGREP_BIN = os.getenv("SEMGREP_BIN", "").strip()
SEMGREP_DOCKER_IMAGE = os.getenv("SEMGREP_DOCKER_IMAGE", "returntocorp/semgrep:latest")
SEMGREP_TIMEOUT = int(os.getenv("SEMGREP_TIMEOUT", "180"))

# ── Docker Sandbox Settings ───────────────────────────────
SANDBOX_IMAGE = "python:3.11-slim"
SANDBOX_TIMEOUT = 30          # seconds for exploit execution
SANDBOX_MEM_LIMIT = "256m"
SANDBOX_CPU_QUOTA = 50000     # 50% of one core
TEST_TIMEOUT = 60             # seconds for test suite execution

# ── Agent Settings ────────────────────────────────────────
MAX_PATCH_RETRIES = 3         # Max attempts for Agent B before escalating
HACKER_MAX_TOKENS = 4000      # Max output tokens for exploit generation
ENGINEER_MAX_TOKENS = 3000    # Max output tokens for patch generation

# ── RAG Settings ──────────────────────────────────────────
RAG_TOP_K = 5                 # Number of related files to retrieve
RAG_DISTANCE_THRESHOLD = 1.5  # Max distance for relevant results

# ── File Types ────────────────────────────────────────────
CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

# ── Logging ───────────────────────────────────────────────
LOG_FORMAT = "[%(asctime)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(level=logging.INFO):
    """Configure logging for the entire application."""
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )


# Create repos directory on import
ANTIGRAVITY_SKILLS_DIR = os.getenv("ANTIGRAVITY_SKILLS_DIR", "/Users/mitulbhatia/Downloads/antigravity-awesome-skills-main")

# Create repos directory on import
os.makedirs(REPOS_DIR, exist_ok=True)
# Ensure skills directory exists (no-op if already exists)
os.makedirs(ANTIGRAVITY_SKILLS_DIR, exist_ok=True)
