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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── Model Settings ────────────────────────────────────────
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# ── Server Settings ───────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))

# ── Paths ─────────────────────────────────────────────────
REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "aegis_vector_db")

# ── Docker Sandbox Settings ───────────────────────────────
SANDBOX_IMAGE = "python:3.11-slim"
SANDBOX_TIMEOUT = 30          # seconds for exploit execution
SANDBOX_MEM_LIMIT = "256m"
SANDBOX_CPU_QUOTA = 50000     # 50% of one core
TEST_TIMEOUT = 60             # seconds for test suite execution

# ── Agent Settings ────────────────────────────────────────
MAX_PATCH_RETRIES = 3         # Max attempts for Agent B before escalating
HACKER_THINKING_BUDGET = 2000 # Extended thinking budget tokens for Agent A

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
os.makedirs(REPOS_DIR, exist_ok=True)
