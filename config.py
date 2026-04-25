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
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── Token Encryption ──────────────────────────────────────
# Used to encrypt GitHub tokens before storing them in the database.
# Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Then paste it into your .env as FERNET_KEY=<key>
FERNET_KEY = os.getenv("FERNET_KEY", "")

# ── GitHub OAuth (for multi-user sign-in) ─────────────────
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Model Settings ────────────────────────────────────────
# Agent A (Finder/Hacker): Groq — ultra-fast inference for analysis & exploit gen
HACKER_MODEL  = os.getenv("HACKER_MODEL",  "llama-3.3-70b-versatile")
HACKER_PROVIDER = "groq"   # groq | mistral

# Agent B (Engineer): Devstral — frontier agentic coding model for quality patches
ENGINEER_MODEL       = os.getenv("ENGINEER_MODEL",       "devstral-small-2505")
ENGINEER_RETRY_MODEL = os.getenv("ENGINEER_RETRY_MODEL", "devstral-2512")  # larger model for retries
ENGINEER_PROVIDER = "mistral"

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

# Embedding model for ChromaDB.
# "default"  → ChromaDB's built-in all-MiniLM-L6-v2 (no extra deps, works out of the box)
# "bge"      → BAAI/bge-small-en-v1.5 via sentence-transformers (better for technical text)
# Falls back to "default" automatically if sentence-transformers is not installed.
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "bge")

# ── Notifications ─────────────────────────────────────────
# Optional Slack/Discord webhook URLs for scan event notifications.
# Leave empty to disable.
SLACK_WEBHOOK_URL   = os.getenv("SLACK_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Demo Mode ─────────────────────────────────────────────
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# ── File Types ────────────────────────────────────────────
# All source file extensions Aegis will scan and index.
CODE_EXTENSIONS = {
    # Web / scripting
    ".py", ".js", ".ts", ".jsx", ".tsx",
    # JVM
    ".java", ".kt", ".scala",
    # Systems
    ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    # Mobile
    ".swift",
    # Web backend
    ".rb", ".php",
    # Shell
    ".sh", ".bash",
}

# Map file extension → Semgrep language-specific ruleset.
# These are the official Semgrep Registry rulesets — each is curated for
# that language's most common vulnerability classes.
LANGUAGE_RULESETS: dict[str, str] = {
    ".py":   "p/python",
    ".js":   "p/javascript",
    ".ts":   "p/typescript",
    ".jsx":  "p/javascript",
    ".tsx":  "p/typescript",
    ".java": "p/java",
    ".kt":   "p/kotlin",
    ".go":   "p/golang",
    ".rs":   "p/rust",
    ".rb":   "p/ruby",
    ".php":  "p/php",
    ".c":    "p/c",
    ".cpp":  "p/cpp",
    ".swift":"p/swift",
}

# Fallback ruleset used when no language-specific one is available
DEFAULT_SEMGREP_RULESET = "p/security-audit"

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "vendor", "target"}

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
    # Set up structlog on top of the standard logging config
    from utils.logging import setup_structured_logging
    setup_structured_logging(level)


# Create repos directory on import
ANTIGRAVITY_SKILLS_DIR = os.getenv("ANTIGRAVITY_SKILLS_DIR", os.path.join(os.path.dirname(__file__), "antigravity_skills"))

# Create repos directory on import
os.makedirs(REPOS_DIR, exist_ok=True)
# Ensure skills directory exists (no-op if already exists)
os.makedirs(ANTIGRAVITY_SKILLS_DIR, exist_ok=True)
