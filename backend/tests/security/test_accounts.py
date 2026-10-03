"""Self-service visitor account registration and password login."""

from sqlalchemy import select

from app.persistence.models import AccessCredential, User

ORIGIN = {"Origin": "http://testclient"}


def test_visitor_can_register_and_sign_in(client, db):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "New Visitor",
            "email": "Visitor@Example.COM",
            "password": "correct horse battery staple",
        },
        headers=ORIGIN,
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["principal"]["role"] == "participant"
    assert "fd_session" in registered.cookies

    user = db.scalar(select(User).where(User.email == "visitor@example.com"))
    assert user is not None
    assert user.password_hash != "correct horse battery staple"
    credential = db.scalar(select(AccessCredential).where(AccessCredential.user_id == user.id))
    assert credential.label == "account-password"

    client.cookies.clear()
    signed_in = client.post(
        "/api/v1/auth/password-session",
        json={"email": "VISITOR@example.com", "password": "correct horse battery staple"},
        headers=ORIGIN,
    )
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["principal"]["id"] == registered.json()["principal"]["id"]


def test_registration_rejects_duplicate_email(client):
    body = {
        "display_name": "First",
        "email": "same@example.com",
        "password": "long-enough-password",
    }
    assert client.post("/api/v1/auth/register", json=body, headers=ORIGIN).status_code == 201
    duplicate = client.post(
        "/api/v1/auth/register",
        json={**body, "display_name": "Second", "email": "SAME@example.com"},
        headers=ORIGIN,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ACCOUNT_EXISTS"


def test_password_login_rejects_bad_credentials(client):
    response = client.post(
        "/api/v1/auth/password-session",
        json={"email": "missing@example.com", "password": "incorrect-password"},
        headers=ORIGIN,
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_REQUIRED"


def test_registration_validates_public_fields(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"display_name": "   ", "email": "invalid", "password": "short"},
        headers=ORIGIN,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_can_register_and_sign_in(client, db):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Admin User",
            "email": "admin@example.com",
            "password": "super-secure-admin-pass",
            "role": "admin",
        },
        headers=ORIGIN,
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["principal"]["role"] == "admin"
    assert "fd_session" in registered.cookies

    user = db.scalar(select(User).where(User.email == "admin@example.com"))
    assert user is not None
    assert user.role == "admin"

