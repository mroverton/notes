"""Shared pytest fixtures.

The strategy: point the app at a separate *test* database (TEST_DATABASE_URL),
create all tables before the suite runs, and drop them after. Each test talks to
the real FastAPI app through `TestClient`, so these are true end-to-end API tests.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a dedicated test database so tests never touch real data. Falls back to a
# local Postgres if TEST_DATABASE_URL isn't set in the environment.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://notes:notes_password@localhost:5432/notes_test",
)

# Build a test engine/session BEFORE importing the app, then override the app's
# `get_db` dependency to use it. This keeps test data isolated from dev/prod.
test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    """Create every table once before the suite, drop them all afterwards."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def make_user(client):
    """Factory fixture: register a user and return an auth header dict.

    Usage:  headers = make_user("alice")
    Then:   client.get("/notes", headers=headers)
    """
    def _make(username: str, password: str = "password123") -> dict[str, str]:
        client.post("/auth/register", json={"username": username, "password": password})
        # login uses form-encoded fields (OAuth2 password flow), not JSON.
        resp = client.post("/auth/login", data={"username": username, "password": password})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
