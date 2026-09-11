import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from backend.app.config import settings

logger = logging.getLogger("aegis.database")

Base = declarative_base()


def get_engine():
    url = settings.normalized_database_url
    if "sqlite" in url:
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )
    
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.DEBUG,
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they don't exist and test connection with fallback."""
    global engine, SessionLocal
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
        logger.info("Database schemas initialized on primary database.")
    except Exception as e:
        logger.error(f"Failed to connect to primary database ({e}). Falling back to local SQLite.")
        engine = create_engine(
            "sqlite:///./aegis.db",
            connect_args={"check_same_thread": False},
        )
        SessionLocal.configure(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Local SQLite database initialized as fallback.")
