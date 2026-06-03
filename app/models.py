"""Database models — the shape of our data in Postgres.

Each class maps to one table. SQLAlchemy turns attribute access and queries on
these objects into SQL for us. The columns match the data model in NOTES.md.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    """Timezone-aware 'now' in UTC. Always store timestamps in UTC and convert
    for display; this avoids a whole class of timezone bugs."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # `unique=True` lets the database itself enforce that no two users share a
    # username — a guarantee application code alone can't make under concurrency.
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    # We never store the raw password — only a one-way bcrypt hash of it.
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Convenience: user.notes gives all notes this user owns.
    notes: Mapped[list["Note"]] = relationship(back_populates="owner")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # `onupdate` makes the database refresh this column on every UPDATE.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="notes")
    shares: Mapped[list["Share"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class Share(Base):
    """A row here means: note `note_id` is shared (read-only) with user
    `shared_with_user_id`. Read-only is enforced in the route layer, not here."""

    __tablename__ = "shares"
    # A note can only be shared with a given user once.
    __table_args__ = (UniqueConstraint("note_id", "shared_with_user_id", name="uq_note_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), index=True)
    shared_with_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    note: Mapped["Note"] = relationship(back_populates="shares")
