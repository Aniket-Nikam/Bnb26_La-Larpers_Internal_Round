"""
Pytest configuration for security tests — P2.

Uses real PostgreSQL and Redis via environment variables.
Never uses SQLite. Never bypasses security middleware.
"""
import asyncio
import os
import secrets

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test profile before any imports of settings
os.environ.setdefault("APP_PROFILE", "test")
os.environ.setdefault("SESSION_DIGEST_KEY", "test_session_key_00000000000000000000000000000000000000000000")
os.environ.setdefault("CREDENTIAL_DIGEST_KEY", "test_cred_key_000000000000000000000000000000000000000000000")
os.environ.setdefault("SEED_ENCRYPTION_KEY", "test_seed_key_000000000000000000000000000000000000000000000")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("PUBLIC_ORIGIN", "http://testclient")
os.environ.setdefault("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://fairdrop:fairdrop@localhost:5432/fairdrop_test"))
os.environ.setdefault("REDIS_URL", os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1"))


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create test database engine and tables."""
    from backend.app.core.config import get_settings
    from backend.app.persistence.models import Base

    settings = get_settings()
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables after session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture()
async def db(db_engine):
    """Per-test database session with automatic rollback."""
    async_session = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        # Override the get_db dependency
        from backend.app import persistence
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def client(db):
    """HTTP test client using the real app with test DB session."""
    from backend.app.main import app
    from backend.app.persistence.database import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testclient") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def test_user(db):
    """Create a test participant user with credential."""
    from backend.app.security.provisioning import provision_user_with_credential

    raw_code = "test-participant-code-" + secrets.token_hex(8)
    user, credential = await provision_user_with_credential(
        db=db,
        display_name="Test Participant",
        role="participant",
        raw_code=raw_code,
        label="test",
    )
    await db.commit()
    return {"user": user, "credential": credential, "raw_code": raw_code}


@pytest_asyncio.fixture()
async def test_organizer(db):
    """Create a test organizer user with credential."""
    from backend.app.security.provisioning import provision_user_with_credential

    raw_code = "test-organizer-code-" + secrets.token_hex(8)
    user, credential = await provision_user_with_credential(
        db=db,
        display_name="Test Organizer",
        role="organizer",
        raw_code=raw_code,
        label="test-org",
    )
    await db.commit()
    return {"user": user, "credential": credential, "raw_code": raw_code}


@pytest_asyncio.fixture()
async def authenticated_client(client, test_user):
    """Client with a valid session cookie already set."""
    resp = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return {
        "client": client,
        "csrf_token": data["csrf_token"],
        "principal": data["principal"],
        "session": data,
    }
