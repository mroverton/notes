"""Database setup: the SQLAlchemy engine, session factory, and base class.

This is the only place that knows *how* to talk to Postgres. The rest of the
app asks for a `Session` via the `get_db` dependency and works with Python
objects (the models in `models.py`) instead of writing raw SQL.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# The engine manages a pool of connections to Postgres. Create it once and reuse.
# `pool_pre_ping` checks a connection is still alive before handing it out, which
# avoids errors after the database restarts or a connection times out.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A factory that produces new Session objects. A Session is your "unit of work":
# you make changes, then commit() them as one transaction (or rollback() on error).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models. SQLAlchemy collects table definitions from
    every subclass into `Base.metadata`, which `main.py` uses to create tables."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session for one request.

    FastAPI calls this for each request that needs the DB, injects the `db`
    session into the route, and the `finally` block guarantees the session is
    closed afterwards (returning its connection to the pool).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
