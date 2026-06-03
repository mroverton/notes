# Secure Notes API

A small, well-structured backend service for learning the basics of API
development in Python: REST design, data persistence, authentication,
access control, testing, and documentation. It's deliberately minimal —
a solid base to build on later.

Users can register, log in, and create/read/update/delete their own notes.
Notes can be shared **read-only** with other users.

---

## System overview & architecture

A request flows through clear layers, each in its own module under [`app/`](app/):

```
HTTP request
   │
FastAPI route        (app/auth.py, app/notes.py)   ← validates input, returns status codes
   │
Auth dependency      (app/security.py)             ← "who are you?" decodes the JWT → User
   │
Authorization check  (app/notes.py helpers)        ← "can you touch THIS note?" owner vs shared
   │
SQLAlchemy ORM       (app/models.py)               ← Python objects ⇄ SQL
   │
PostgreSQL
```

| File | Responsibility |
|------|----------------|
| [`app/main.py`](app/main.py) | Creates the FastAPI app, wires routers, creates tables on startup |
| [`app/config.py`](app/config.py) | Loads settings from the environment |
| [`app/database.py`](app/database.py) | SQLAlchemy engine, session, `get_db` dependency |
| [`app/models.py`](app/models.py) | `User`, `Note`, `Share` tables |
| [`app/schemas.py`](app/schemas.py) | Request/response shapes (Pydantic) |
| [`app/security.py`](app/security.py) | Password hashing, JWT, current-user dependency |
| [`app/auth.py`](app/auth.py) | `/auth/register`, `/auth/login` |
| [`app/notes.py`](app/notes.py) | Notes CRUD + sharing, with access control |

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | – | Register a new user |
| POST | `/auth/login` | – | Log in, receive a JWT |
| POST | `/notes` | ✓ | Create a note |
| GET | `/notes` | ✓ | List notes you own or that are shared with you |
| GET | `/notes/{id}` | ✓ | Get a note (if owner or shared) |
| PUT | `/notes/{id}` | ✓ | Update a note (owner only) |
| DELETE | `/notes/{id}` | ✓ | Delete a note (owner only) |
| POST | `/notes/{id}/share` | ✓ | Share a note read-only with another user |

Interactive docs (Swagger UI) are generated automatically at
**http://localhost:8000/docs**.

---

## Tech choices

- **FastAPI** — modern, async-capable, and generates OpenAPI/Swagger docs and
  request validation for free, so the API documents itself.
- **PostgreSQL** — a robust relational database; our data (users, notes, shares)
  is naturally relational with clear foreign-key relationships.
- **SQLAlchemy 2.0 (ORM)** — work with Python objects instead of hand-written
  SQL, which is safer (parameterized queries prevent SQL injection) and clearer.
- **JWT (PyJWT)** — stateless token auth: the server doesn't store sessions, so
  it scales horizontally easily.
- **bcrypt** — the standard for password hashing; slow by design to resist
  brute force, with a random per-password salt embedded in each hash.
- **pytest + httpx** — concise tests that exercise the real app end-to-end.

---

## How to run

### 1. With Docker Compose (recommended)

```bash
cp .env.example .env        # then edit JWT_SECRET to something random
docker compose up --build
```

The API is now at http://localhost:8000 and the docs at
http://localhost:8000/docs. Postgres is also exposed on `localhost:5432`.

### 2. Locally (without Docker)

This repo uses **asdf** (versions) + **direnv** (per-project env). With both
installed, `cd` into the project and `direnv allow` — it creates a Python 3.14
virtualenv and installs `requirements.txt` automatically. Then point
`DATABASE_URL` at a running Postgres and:

```bash
uvicorn app.main:app --reload
```

---

## How to run the tests

The tests run against a **separate** database (`TEST_DATABASE_URL`) so they
never touch real data. The easiest path is to use the compose Postgres:

```bash
docker compose up -d db                              # start just Postgres
# create the test database once:
docker compose exec db createdb -U notes notes_test
pytest                                               # uses TEST_DATABASE_URL from .env
```

The suite covers registration/login, note CRUD, sharing being read-only, and —
most importantly — that **a user cannot access another user's note**.

---

## API usage examples

```bash
BASE=http://localhost:8000
HCTX='Content-Type: application/json'

# 1. Register
curl -X POST $BASE/auth/register -H "$HCTX" -d '{"username":"alice","password":"password123"}'
curl -X POST $BASE/auth/register -H "$HCTX" -d '{"username":"bob","password":"password123"}'

# 2. Log in (form-encoded — OAuth2 password flow). Save the token.
TALICE=$(curl -s -X POST $BASE/auth/login -d 'username=alice&password=password123' | jq -r '.access_token')
TBOB=$(curl -s -X POST $BASE/auth/login -d 'username=bob&password=password123' | jq -r '.access_token')

# 3. Create a note
curl -X POST $BASE/notes -H "Authorization: Bearer $TALICE" -H "$HCTX" -d '{"content":"buy milk"}'
curl -X POST $BASE/notes -H "Authorization: Bearer $TBOB" -H "$HCTX" -d '{"content":"buy cheeze"}'

# 4. List your notes
curl $BASE/notes -H "Authorization: Bearer $TALICE" |jq
curl $BASE/notes -H "Authorization: Bearer $TBOB" |jq

# 5. Get / update / delete a note (id 1)
curl $BASE/notes/1 -H "Authorization: Bearer $TALICE"
curl -X PUT $BASE/notes/1 -H "Authorization: Bearer $TALICE" -H "$HCTX" -d '{"content":"buy oat milk"}'
curl -X DELETE $BASE/notes/1 -H "Authorization: Bearer $TALICE"

# 6. Share note 1 with bob (read-only for bob)
curl -X POST $BASE/notes/1/share -H "Authorization: Bearer $TALICE" -H "$HCTX" -d '{"username":"bob"}'
```

---

## Security considerations

- **Passwords** are never stored in plaintext — only bcrypt hashes (salted).
- **Tokens** are signed JWTs; the signing secret lives in the environment, not
  in code. Tokens expire (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Access control**: every notes route resolves the authenticated user and
  checks ownership/sharing before acting. Shares are read-only.
- **No information leaks**: requesting a note you can't see returns `404`, not
  `403`, so the API doesn't reveal that the note exists. Login returns the same
  error for unknown-user and wrong-password.
- **SQL injection** is avoided by using the ORM's parameterized queries.
- **Secrets** come from the environment / a secrets manager — `.env` is
  gitignored and must never be committed.

---

## Assumptions, tradeoffs & future improvements

**Assumptions**
- Single-tenant, trusted clients over HTTPS (TLS terminates at a proxy).
- "Sharing" means read-only; there are no edit-collaborators or roles yet.

**Tradeoffs (kept simple on purpose)**
- Tables are created from the models on startup instead of using migrations —
  fine for learning, not for evolving a production schema (see `DESIGN.md`).
- JWTs can't be revoked before they expire; there are no refresh tokens.
- No rate limiting or pagination yet.

**Future improvements**
- Alembic migrations, refresh tokens + revocation, rate limiting, pagination,
  richer sharing permissions, structured logging/metrics, and CI. Each is a
  natural next exercise on top of this base.

See [`DESIGN.md`](DESIGN.md) for operational/production reasoning.
