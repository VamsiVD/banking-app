"""Tests for the auth slice, against a real users table.

The point of these is persistence and the unique constraint. Registration used to
write into a dict that vanished on restart; a user who signed up yesterday could
not log in today.
"""

import pytest

from app import db
from app.errors import EmailAlreadyRegistered, InvalidCredentials
from app.repositories.user_repository import user_repository
from app.services import auth_service
from app.api_schemas.auth_schema import LoginRequest, RegisterRequest


def register(client, email="sam@example.com", password="correct-horse", name="Sam Reed"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )


def test_register_returns_a_profile_without_the_password(client):
    r = register(client)

    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "sam@example.com"
    assert body["full_name"] == "Sam Reed"
    assert "hashed_password" not in body
    assert "password" not in body


def test_a_registered_user_survives_into_a_fresh_session(client, db_session):
    """The whole reason for the users table.

    A new session is a new connection with an empty identity map — the closest a
    test gets to restarting the server.
    """
    register(client)

    with db.session_scope():
        user = user_repository.get_by_email("sam@example.com")

    assert user is not None
    assert user["full_name"] == "Sam Reed"


def test_login_verifies_a_hash_read_back_out_of_the_database(client, db_session):
    """bcrypt round trip through BYTEA.

    The hash is written as bytes and must come back as bytes: bcrypt.checkpw
    rejects a str, so a column type that mangled this would fail here.
    """
    register(client)

    r = client.post(
        "/auth/login", json={"email": "sam@example.com", "password": "correct-horse"}
    )

    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_with_the_wrong_password_is_401(client):
    register(client)

    r = client.post(
        "/auth/login", json={"email": "sam@example.com", "password": "not-the-one"}
    )

    assert r.status_code == 401


def test_login_for_an_unknown_email_is_401(client):
    r = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )

    assert r.status_code == 401


def test_registering_the_same_email_twice_is_refused(client):
    assert register(client).status_code == 201

    r = register(client, name="Someone Else")

    assert r.status_code == 409
    assert "already registered" in r.json()["error"]["message"]


def test_the_unique_constraint_catches_what_the_python_check_cannot(db_session):
    """register_user() checks for an existing email before inserting.

    Two simultaneous registrations can both pass that check — only one INSERT can
    win. Calling the repository directly skips the check, which is what a lost
    race looks like from the database's side.
    """
    payload = RegisterRequest(
        email="race@example.com", password="password123", full_name="First"
    )
    auth_service.register_user(payload)

    with pytest.raises(EmailAlreadyRegistered):
        user_repository.create("race@example.com", "Second", b"$2b$12$fakehashvalue")


def test_authenticate_user_raises_for_a_bad_password(client):
    register(client, email="ana@example.com")

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user(
            LoginRequest(email="ana@example.com", password="wrong-password")
        )
