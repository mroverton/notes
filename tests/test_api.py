"""Happy-path API tests, plus the required access-control check.

These are intentionally minimal — enough to show the testing approach and to
prove the core security guarantee. Each test uses unique usernames because the
tables persist for the whole test session (see conftest.py).
"""


def test_register_and_login_returns_token(client):
    """A new user can register and then log in to receive a JWT."""
    r = client.post("/auth/register", json={"username": "reg_user", "password": "password123"})
    assert r.status_code == 201
    assert r.json()["username"] == "reg_user"
    assert "password" not in r.json()  # never leak credentials back

    r = client.post("/auth/login", data={"username": "reg_user", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_create_and_get_own_note(client, make_user):
    """Owner can create a note and read it back."""
    headers = make_user("note_owner")

    r = client.post("/notes", json={"content": "my first note"}, headers=headers)
    assert r.status_code == 201
    note_id = r.json()["id"]

    r = client.get(f"/notes/{note_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["content"] == "my first note"

    # create a second note
    r = client.post("/notes", json={"content": "my second note"}, headers=headers)
    assert r.status_code == 201
    note_id2 = r.json()["id"]

    r = client.get(f"/notes/{note_id2}", headers=headers)
    assert r.status_code == 200
    assert r.json()["content"] == "my second note"

    # Update a note
    r = client.put(f"/notes/{note_id2}", json={"content": "my 2nd note"}, headers=headers)
    assert r.status_code == 200

    r = client.get(f"/notes/{note_id2}", headers=headers)
    assert r.status_code == 200
    assert r.json()["content"] == "my 2nd note"


def test_shared_note_is_readable_but_read_only(client, make_user):
    """A shared note can be read by the recipient, but updating it returns 403."""
    owner = make_user("share_owner")
    recipient = make_user("share_recipient")

    note_id = client.post(
        "/notes", json={"content": "shared content"}, headers=owner
    ).json()["id"]

    # Owner shares it with the recipient.
    r = client.post(
        f"/notes/{note_id}/share", json={"username": "share_recipient"}, headers=owner
    )
    assert r.status_code == 201

    # Recipient can READ it...
    r = client.get(f"/notes/{note_id}", headers=recipient)
    assert r.status_code == 200
    assert r.json()["content"] == "shared content"

    # ...but cannot WRITE it (shares are read-only).
    r = client.put(f"/notes/{note_id}", json={"content": "hacked"}, headers=recipient)
    assert r.status_code == 403

    # ...or delete it
    r = client.delete(f"/notes/{note_id}", headers=recipient)
    assert r.status_code == 404

def test_user_cannot_access_another_users_note(client, make_user):
    """REQUIRED: a user must not be able to read someone else's un-shared note.

    The note exists, but because it was never shared with user B, the API
    responds 404 (not 403) so it doesn't even reveal that the note exists.
    """
    alice = make_user("alice_private")
    bob = make_user("bob_intruder")

    note_id = client.post(
        "/notes", json={"content": "alice's secret"}, headers=alice
    ).json()["id"]

    # Bob tries to read Alice's note directly.
    r = client.get(f"/notes/{note_id}", headers=bob)
    assert r.status_code == 404

    # Bob also cannot delete it.
    r = client.delete(f"/notes/{note_id}", headers=bob)
    assert r.status_code == 404

    # And it never shows up in Bob's own list.
    r = client.get("/notes", headers=bob)
    assert all(n["id"] != note_id for n in r.json())


def test_unauthenticated_requests_are_rejected(client):
    """Without a token, protected routes return 401."""
    assert client.get("/notes").status_code == 401
    assert client.post("/notes", json={"content": "x"}).status_code == 401
