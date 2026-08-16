"""Pytest fixtures for the Bibliotheca backend test suite."""

import os
from pathlib import Path

# Required env vars must be set BEFORE importing modules that build engines
# (config fails fast on missing required values).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./bibliotheca.db")
os.environ.setdefault("BUSINESS_NAME", "Librería El Estante")
os.environ.setdefault("BUSINESS_CUIT", "30-12345678-9")
os.environ.setdefault("BUSINESS_ADDRESS", "Av. Corrientes 1234, CABA")
os.environ.setdefault("BUSINESS_CONDITION", "Responsable Inscripto")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.models import Base, User
from app.security.jwt import create_access_token
from app.security.limiter import limiter
from app.security.password import hash_password

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# The shared app used by tests must not depend on whether a frontend build
# happens to exist on disk: SPA mounting is covered by test_spa_mount.py with
# an explicitly controlled dist dir.
SPA_DIST_MISSING = Path("__no_spa_dist_built__")


@pytest.fixture
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    # slowapi uses in-memory storage; reset between tests to avoid order
    # dependence in rate-limit assertions.
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
async def auth_headers(session):
    """Seed an admin user and return a Bearer Authorization header."""
    user = User(username="admin", password_hash=hash_password("admin"), role="admin")
    session.add(user)
    await session.commit()
    token = create_access_token("admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(engine, session_factory):
    app = create_app(spa_dist=SPA_DIST_MISSING)

    async def _override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
