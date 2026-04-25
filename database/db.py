"""
Aegis — Database Connection & Session Management

SQLite + SQLAlchemy for the hackathon.
Swap to PostgreSQL later by changing SQLALCHEMY_DATABASE_URL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./aegis.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
    echo=False,
)

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
    from alembic.config import Config
    from alembic import command
    
    # Load Alembic configuration and run migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
