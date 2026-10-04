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


def test_registration_with_face_scan_stores_embedding(client, db, monkeypatch):
    test_vector = [0.05] * 128
    monkeypatch.setattr(
        "app.security.router.extract_face_embedding",
        lambda img: test_vector,
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Face User 1",
            "email": "face1@example.com",
            "password": "valid-password-123",
            "face_image": "data:image/jpeg;base64,dGVzdA==",
        },
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text

    user = db.scalar(select(User).where(User.email == "face1@example.com"))
    assert user is not None
    assert user.face_embedding is not None
    assert len(user.face_embedding) == 128
    assert user.face_embedding[0] == 0.05


def test_registration_rejects_duplicate_face(client, monkeypatch):
    # Vector 1 and Vector 2 are very close (Euclidean distance ~ 0.226 < 0.60 threshold)
    vector1 = [0.10] * 128
    vector2 = [0.12] * 128

    monkeypatch.setattr(
        "app.security.router.extract_face_embedding",
        lambda img: vector1,
    )
    first = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Original Person",
            "email": "original@example.com",
            "password": "valid-password-123",
            "face_image": "data:image/jpeg;base64,Zmlyc3Q=",
        },
        headers=ORIGIN,
    )
    assert first.status_code == 201, first.text

    # Second registration with a different email/name but matching face biometrics
    monkeypatch.setattr(
        "app.security.router.extract_face_embedding",
        lambda img: vector2,
    )
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Duplicate Person",
            "email": "duplicate@example.com",
            "password": "valid-password-123",
            "face_image": "data:image/jpeg;base64,c2Vjb25k",
        },
        headers=ORIGIN,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_FACE"
    assert "face is already registered" in duplicate.json()["error"]["message"]


def test_registration_allows_distinct_faces(client, monkeypatch):
    # Vector 1 and Vector 3 are distinct (Euclidean distance ~ 9.05 >> 0.60)
    vector_distinct = [0.90] * 128

    monkeypatch.setattr(
        "app.security.router.extract_face_embedding",
        lambda img: vector_distinct,
    )
    distinct = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Different Person",
            "email": "distinct@example.com",
            "password": "valid-password-123",
            "face_image": "data:image/jpeg;base64,ZGlzdGluY3Q=",
        },
        headers=ORIGIN,
    )
    assert distinct.status_code == 201, distinct.text


def test_extract_face_embedding_validations():
    import pytest
    from app.core.errors import DomainError
    from app.security.face import extract_face_embedding

    with pytest.raises(DomainError) as exc_info:
        extract_face_embedding("")
    assert exc_info.value.code == "VALIDATION_ERROR"

    with pytest.raises(DomainError) as exc_info:
        extract_face_embedding("data:image/jpeg;base64,not-valid-base64!!!")
    assert exc_info.value.code == "VALIDATION_ERROR"


