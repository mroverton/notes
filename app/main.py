"""Application entry point — assembles the FastAPI app.

Run it for development with:
    uvicorn app.main:app --reload

Then open http://localhost:8000/docs for interactive Swagger documentation,
which FastAPI generates automatically from the routes and schemas.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import router as auth_router
from app.database import Base, engine
from app.notes import router as notes_router

# Importing `app.models` registers the model classes on `Base.metadata` so that
# `create_all` below knows about every table. (Imported for its side effect.)
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs once on startup. For this teaching project we create tables directly
    # from the models. In a real system you'd use migrations (e.g. Alembic) so
    # schema changes are versioned and reviewable — see DESIGN.md.
    Base.metadata.create_all(bind=engine)
    yield
    # (Nothing to clean up on shutdown here.)


app = FastAPI(
    title="Secure Notes API",
    description="A small teaching API: create, share, and manage notes with auth.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(notes_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check — handy for load balancers and `docker compose` healthchecks."""
    return {"status": "ok"}
