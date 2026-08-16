"""Integration tests for auth endpoints and app wiring."""

from sqlalchemy import func, select

from app.main import bootstrap_admin
from app.models import User
from app.security.jwt import create_access_token
from app.security.password import hash_password


async def _seed_user(session, username="admin", password="admin", role="admin") -> User:
    user = User(username=username, password_hash=hash_password(password), role=role)
    session.add(user)
    await session.commit()
    return user


async def test_login_success(client, session):
    await _seed_user(session)
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["access_token"]


async def test_login_wrong_password(client, session):
    await _seed_user(session)
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await client.post(
        "/api/auth/login", json={"username": "ghost", "password": "x"}
    )
    assert response.status_code == 401


async def test_login_wrong_method(client):
    response = await client.get("/api/auth/login")
    assert response.status_code == 405


async def test_me_requires_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_with_token(client, session):
    await _seed_user(session)
    token = create_access_token("admin", "admin")
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"username": "admin", "role": "admin"}


async def test_admin_bootstrap_creates_admin(session):
    await bootstrap_admin(session)
    user = (
        await session.execute(select(User).where(User.username == "admin"))
    ).scalar_one()
    assert user.role == "admin"
    assert user.is_active is True


async def test_admin_bootstrap_idempotent(session):
    await bootstrap_admin(session)
    await bootstrap_admin(session)
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    assert count == 1


async def test_cors_disallowed_origin_no_header(client):
    response = await client.get(
        "/health", headers={"Origin": "http://evil.example.com"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_login_rate_limited_429(client, session):
    await _seed_user(session)
    response = None
    for _ in range(6):
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrong"}
        )
    assert response.status_code == 429
    assert "retry-after" in response.headers
