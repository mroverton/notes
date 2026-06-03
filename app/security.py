"""Security helpers: password hashing, JWT tokens, and the current-user dependency.

This module answers two questions:
  1. Authentication — "who are you?" (verify a password, issue/decode a token)
  2. Identity injection — turn the token on a request into a `User` object

Authorization — "are you allowed to touch THIS note?" — lives in `notes.py`,
because it depends on the specific resource being accessed.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

# Tells FastAPI tokens arrive as `Authorization: Bearer <token>`, and points the
# Swagger UI "Authorize" button at the login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# bcrypt operates on bytes and ignores anything past the first 72 bytes of the
# password, so we truncate explicitly to keep behavior predictable.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    """Turn a plaintext password into a bcrypt hash for storage.

    bcrypt generates a random salt and embeds it in the returned hash string, so
    the same password hashes to a different value each time — that's expected.
    """
    pw = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a stored hash (constant-time compare)."""
    pw = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(pw, hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    """Create a signed JWT whose `sub` (subject) claim is the user's id and
    which expires after the configured number of minutes."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# Raised whenever a token is missing, malformed, expired, or its user is gone.
_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: decode the bearer token and load the matching user.

    Any route that depends on this is automatically protected — no valid token,
    no access. The returned `User` is the authenticated caller.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _credentials_error

    user = db.get(User, user_id)
    if user is None:
        raise _credentials_error
    return user
