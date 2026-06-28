"""
Database engine and session management (SQLAlchemy 2.0 style).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import contextmanager
from typing import Generator

from src.config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a transactional DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_transaction() -> Generator[Session, None, None]:
    """
    Explicit transactional context manager for service-layer use.
    Guarantees atomic commit/rollback for compound journal operations
    (see Part A9.3 — never partially commit).
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
