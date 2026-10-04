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


def test_registration_stores_face_embedding(client, db, monkeypatch):
    embedding = [0.05] * 128
    monkeypatch.setattr("app.security.router.extract_face_embedding", lambda _image: embedding)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Verified Visitor",
            "email": "verified@example.com",
            "password": "correct horse battery staple",
            "face_image": "data:image/jpeg;base64,dGVzdA==",
        },
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    user = db.scalar(select(User).where(User.email == "verified@example.com"))
    assert user.face_embedding == embedding


def test_registration_rejects_duplicate_face(client, monkeypatch):
    first = [0.10] * 128
    second = [0.12] * 128
    monkeypatch.setattr("app.security.router.extract_face_embedding", lambda _image: first)
    payload = {
        "display_name": "Original Visitor",
        "email": "original-face@example.com",
        "password": "correct horse battery staple",
        "face_image": "data:image/jpeg;base64,Zmlyc3Q=",
    }
    assert client.post("/api/v1/auth/register", json=payload, headers=ORIGIN).status_code == 201
    monkeypatch.setattr("app.security.router.extract_face_embedding", lambda _image: second)
    duplicate = client.post(
        "/api/v1/auth/register",
        json={**payload, "display_name": "Second Visitor", "email": "second-face@example.com"},
        headers=ORIGIN,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_FACE"
