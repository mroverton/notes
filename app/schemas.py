"""API schemas — the shape of data going in and out over HTTP (JSON).

These Pydantic models are separate from the database models on purpose:
- Request schemas define + validate what clients are allowed to send.
- Response schemas define exactly what we expose (e.g. we never return
  `password_hash`).

FastAPI uses these for automatic validation and for the OpenAPI/Swagger docs.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Auth ---------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    # `from_attributes=True` lets Pydantic read values off an ORM object
    # (a `User` model), not just a dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Notes --------------------------------------------------------------

class NoteCreate(BaseModel):
    content: str = Field(min_length=1)


class NoteUpdate(BaseModel):
    content: str = Field(min_length=1)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    content: str
    created_at: datetime
    updated_at: datetime


# --- Sharing ------------------------------------------------------------

class ShareCreate(BaseModel):
    # Share by username — the caller doesn't need to know the other user's id.
    username: str


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    shared_with_user_id: int
    created_at: datetime
