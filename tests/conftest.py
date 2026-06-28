"""
tests/conftest.py

Integration tests require the real PostgreSQL instance (triggers, advisory
locks, and partitioning are Postgres-specific and cannot be faithfully
simulated with SQLite). When run outside `docker compose --profile test run
tests` (e.g. no DATABASE_URL reachable), these fixtures skip dependent tests
rather than failing the whole suite.
"""
import os
import pathlib

# Fall back to .env.test for local `pytest` runs when no real .env exists
# (docker-compose always provides a real .env via env_file:).
if "DATABASE_URL" not in os.environ:
    env_test_path = pathlib.Path(__file__).resolve().parent.parent / ".env.test"
    if env_test_path.exists():
        for line in env_test_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.config.database import Base
import src.models  # noqa: registers all tables on Base.metadata


@pytest.fixture(scope="session")
def db_engine():
    try:
        engine = create_engine(settings.database_url, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable for integration tests: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine, future=True)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def unique_idempotency_key():
    return f"test-{uuid.uuid4().hex}"
