import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis.db")

# Standardize postgres protocol for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def _build_engine(url: str):
    if "sqlite" in url:
        return create_engine(url, connect_args={"check_same_thread": False}, echo=False)
    else:
        try:
            eng = create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to PostgreSQL / Supabase database")
            return eng
        except Exception as e:
            if os.getenv("RENDER"):
                logger.error(f"FATAL: PostgreSQL connection failed on Render: {e}")
                raise RuntimeError("PostgreSQL database is REQUIRED in production (Render) to prevent ephemeral data wipe. Please configure DATABASE_URL.")
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database (sqlite:///./aegis.db).")
            return create_engine("sqlite:///./aegis.db", connect_args={"check_same_thread": False}, echo=False)

engine = _build_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



def get_db():
    """FastAPI dependency — yields a DB session, auto-closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database using Alembic migrations.
    Runs all pending migrations to bring DB to latest schema.
    """
    try:
        from alembic.config import Config
        from alembic import command
        
        # Enable pgvector extension if Postgres (must happen before creating tables)
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()

        alembic_cfg = Config("alembic.ini")
        # configparser uses % for interpolation. Escape any % in password as %%
        safe_url = DATABASE_URL.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", safe_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as e:
        logger.warning(f"Alembic migration auto-upgrade warning: {e}. Ensuring tables with metadata.create_all.")
        
        # Fallback for pgvector if Alembic fails
        if engine.dialect.name == "postgresql":
            try:
                with engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    conn.commit()
            except Exception as ext_err:
                logger.warning(f"Failed to create vector extension: {ext_err}")
                
        Base.metadata.create_all(bind=engine)

