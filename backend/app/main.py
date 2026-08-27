import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.core.database import init_db
from backend.app.api.auth import router as auth_router
from backend.app.api.repos import router as repos_router
from backend.app.api.scans import router as scans_router
from backend.app.api.stats import router as stats_router
from backend.app.api.webhooks import router as webhooks_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegis.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Aegis 2.0 Backend...")
    init_db()
    yield
    logger.info("Shutting down Aegis 2.0 Backend.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous AI Security Remediation Platform",
    lifespan=lifespan,
)

# CORS configuration to seamlessly communicate with Vercel and localhost Next.js frontend
origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://aegis-ecru-eta.vercel.app",
    "https://aegis-frontend-zeta.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(repos_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")

# Also mount webhook router directly at /webhook and /webhooks for GitHub App default configs
app.include_router(webhooks_router, prefix="/webhook")
app.include_router(webhooks_router, prefix="/webhooks")


@app.get("/health")
def health_check():
    """Health check endpoint for Render / monitoring."""
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/")
def root():
    return {
        "message": "Aegis 2.0 API is live",
        "docs": "/docs",
        "health": "/health",
    }
