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
    else:
        try:
            eng = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=settings.DEBUG,
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL database.")
            return eng
        except Exception as e:
            if settings.RENDER:
                logger.error(f"PostgreSQL connection failed in production on Render: {e}")
                raise RuntimeError("PostgreSQL database is REQUIRED in production.")
            logger.warning(
                f"PostgreSQL connection failed ({e}). Falling back to local SQLite: sqlite:///./aegis.db"
            )
            return create_engine(
                "sqlite:///./aegis.db",
                connect_args={"check_same_thread": False},
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
    """Create tables if they don't exist and test connection."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas initialized.")
