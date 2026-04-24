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
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")  # env var: GROQ_API_KEY
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── GitHub OAuth (for multi-user sign-in) ─────────────────
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Model Settings ────────────────────────────────────────
# Agent A (Finder/Hacker): Groq — ultra-fast inference for analysis & exploit gen
HACKER_MODEL  = os.getenv("HACKER_MODEL",  "llama-3.3-70b-versatile")
HACKER_PROVIDER = "groq"   # groq | mistral

# Agent B (Engineer): Devstral 2 — frontier agentic coding model for quality patches
ENGINEER_MODEL    = os.getenv("ENGINEER_MODEL",    "devstral-small-2505")
ENGINEER_PROVIDER = "mistral"  # mistral | groq

# ── Server Settings ───────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))

# ── Paths ─────────────────────────────────────────────────
REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "aegis_vector_db")

# ── Scanner Settings ───────────────────────────────────────
# Optional absolute path to Semgrep binary. If unset, Aegis auto-detects.
SEMGREP_BIN = os.getenv("SEMGREP_BIN", "").strip()
SEMGREP_DOCKER_IMAGE = os.getenv("SEMGREP_DOCKER_IMAGE", "semgrep/semgrep:latest")
SEMGREP_TIMEOUT = int(os.getenv("SEMGREP_TIMEOUT", "180"))

# ── Docker Sandbox Settings ───────────────────────────────
SANDBOX_IMAGE = "aegis-sandbox:latest"  # Our custom secure sandbox image
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))   # seconds for exploit execution
SANDBOX_MEM_LIMIT = "256m"
SANDBOX_CPU_QUOTA = 50000     # 50% of one core
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "45"))         # seconds for test suite execution (was 60)

# ── Agent Settings ────────────────────────────────────────
MAX_PATCH_RETRIES = 3         # Max attempts for Agent B before escalating
HACKER_MAX_TOKENS = 4000      # Max output tokens for exploit generation
ENGINEER_MAX_TOKENS = 3000    # Max output tokens for patch generation

# ── LLM Timeouts (ms) ─────────────────────────────────────
HACKER_TIMEOUT_MS  = int(os.getenv("HACKER_TIMEOUT_MS",  "45000"))  # 45s for Finder/Hacker
ENGINEER_TIMEOUT_MS = int(os.getenv("ENGINEER_TIMEOUT_MS", "90000"))  # 90s for Engineer (large output)

# ── RAG Settings ──────────────────────────────────────────
RAG_TOP_K = 5                 # Number of related files to retrieve
RAG_DISTANCE_THRESHOLD = 1.5  # Max distance for relevant results

# ── Demo Mode ─────────────────────────────────────────────
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

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
ANTIGRAVITY_SKILLS_DIR = os.getenv("ANTIGRAVITY_SKILLS_DIR", os.path.join(os.path.dirname(__file__), "antigravity_skills"))

# Create repos directory on import
os.makedirs(REPOS_DIR, exist_ok=True)
# Ensure skills directory exists (no-op if already exists)
os.makedirs(ANTIGRAVITY_SKILLS_DIR, exist_ok=True)
