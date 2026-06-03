"""Notes routes: create, read, update, delete, and share notes.

This is where *authorization* lives — deciding whether the authenticated caller
is allowed to act on a specific note. The rules (from NOTES.md):
  - You can read notes you own OR notes shared with you.
  - You can only update/delete/share notes you OWN.
  - Shares are read-only for the recipient.

Every route here depends on `get_current_user`, so an invalid/missing token is
rejected with 401 before any of this code runs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Note, Share, User
from app.schemas import NoteCreate, NoteOut, NoteUpdate, ShareCreate, ShareOut
from app.security import get_current_user

router = APIRouter(prefix="/notes", tags=["notes"])


def _get_note_readable_by(db: Session, note_id: int, user: User) -> Note:
    """Return the note if `user` may READ it (owner or shared), else 404.

    We deliberately return 404 (not 403) when a note exists but the caller has
    no access: revealing "this exists but you can't see it" leaks information.
    Centralizing this rule in one helper keeps the policy consistent.
    """
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if note.owner_id == user.id:
        return note

    shared = db.scalar(
        select(Share).where(Share.note_id == note_id, Share.shared_with_user_id == user.id)
    )
    if shared is not None:
        return note

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


def _get_note_owned_by(db: Session, note_id: int, user: User) -> Note:
    """Return the note if `user` OWNS it, else 404. Used for write operations."""
    note = db.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Note:
    note = Note(owner_id=user.id, content=payload.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[NoteOut])
def list_notes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Note]:
    """List notes the caller owns OR that have been shared with them."""
    stmt = (
        select(Note)
        .outerjoin(Share, Share.note_id == Note.id)
        .where(or_(Note.owner_id == user.id, Share.shared_with_user_id == user.id))
        .distinct()
        .order_by(Note.created_at)
    )
    return list(db.scalars(stmt).all())


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Note:
    return _get_note_readable_by(db, note_id, user)


@router.put("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Note:
    """Update a note's content. Owner only — a recipient of a share gets 403."""
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if note.owner_id != user.id:
        # The note may have been shared with this user, but shares are read-only.
        # We distinguish read-allowed-but-write-denied (403) from not-found (404).
        shared = db.scalar(
            select(Share).where(Share.note_id == note_id, Share.shared_with_user_id == user.id)
        )
        if shared is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Shared notes are read-only"
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    note.content = payload.content
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    note = _get_note_owned_by(db, note_id, user)
    db.delete(note)
    db.commit()


@router.post("/{note_id}/share", response_model=ShareOut, status_code=status.HTTP_201_CREATED)
def share_note(
    note_id: int,
    payload: ShareCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Share:
    """Share a note (read-only) with another user, by username. Owner only."""
    note = _get_note_owned_by(db, note_id, user)

    recipient = db.scalar(select(User).where(User.username == payload.username))
    if recipient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if recipient.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share a note with yourself"
        )

    # Idempotent-ish: if it's already shared with this user, just return it.
    existing = db.scalar(
        select(Share).where(Share.note_id == note.id, Share.shared_with_user_id == recipient.id)
    )
    if existing is not None:
        return existing

    share = Share(note_id=note.id, shared_with_user_id=recipient.id)
    db.add(share)
    db.commit()
    db.refresh(share)
    return share
