"""Authentication routes: register a user and log in for a token.

These are the only endpoints that don't require a token (you need them to *get*
a token in the first place).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new user. Returns 409 if the username is already taken."""
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)  # reload so id/created_at (set by the DB) are populated
    return user


@router.post("/login", response_model=Token)
def login(
    # OAuth2PasswordRequestForm reads `username` and `password` from form fields,
    # which is what the Swagger UI "Authorize" dialog sends.
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Verify credentials and return a JWT access token."""
    user = db.scalar(select(User).where(User.username == form.username))

    # Note: we give the same 401 whether the username is wrong or the password
    # is wrong, so an attacker can't probe which usernames exist.
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.id))
