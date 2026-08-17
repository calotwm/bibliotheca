"""Tests for PATCH /api/auth/me — self-service username/password changes."""

from sqlalchemy import select

from app.models import AuditLog, User
from app.security.jwt import create_access_token
from app.security.password import hash_password, verify_password


async def _seed_user(session, username="admin", password="admin", role="admin") -> User:
    user = User(username=username, password_hash=hash_password(password), role=role)
    session.add(user)
    await session.commit()
    return user


def _headers(username="admin", role="admin") -> dict:
    token = create_access_token(username, role)
    return {"Authorization": f"Bearer {token}"}


async def test_change_password_old_fails_new_works(client, session):
    user = await _seed_user(session)
    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "admin", "new_password": "nueva-segura"},
        headers=_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["username"] == "admin"
    assert data["role"] == "admin"

    await session.refresh(user)
    assert verify_password("admin", user.password_hash) is False
    assert verify_password("nueva-segura", user.password_hash) is True


async def test_wrong_current_password_400_nothing_changed(client, session):
    user = await _seed_user(session)
    old_hash = user.password_hash
    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "mal", "new_password": "nueva-segura"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Contraseña actual incorrecta"
    await session.refresh(user)
    assert user.password_hash == old_hash


async def test_change_username_success(client, session):
    user = await _seed_user(session)
    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "admin", "new_username": "nuevo-admin"},
        headers=_headers(),
    )
    assert response.status_code == 200
    assert response.json()["username"] == "nuevo-admin"
    await session.refresh(user)
    assert user.username == "nuevo-admin"


async def test_username_must_differ_from_current(client, session):
    await _seed_user(session)
    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "admin", "new_username": "admin"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El nuevo usuario debe ser distinto del actual"


async def test_username_uniqueness_conflict_400(client, session):
    await _seed_user(session, username="admin")
    other = User(
        username="otro", password_hash=hash_password("admin"), role="cashier"
    )
    session.add(other)
    await session.commit()

    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "admin", "new_username": "otro"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El usuario ya existe"


async def test_update_both_fields_in_one_call(client, session):
    user = await _seed_user(session)
    response = await client.patch(
        "/api/auth/me",
        json={
            "current_password": "admin",
            "new_username": "renombrado",
            "new_password": "otra-clave",
        },
        headers=_headers(),
    )
    assert response.status_code == 200
    await session.refresh(user)
    assert user.username == "renombrado"
    assert verify_password("otra-clave", user.password_hash) is True


async def test_update_requires_token(client):
    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "admin", "new_username": "nuevo"},
    )
    assert response.status_code == 401


async def test_update_without_changes_400(client, session):
    await _seed_user(session)
    response = await client.patch(
        "/api/auth/me",
        json={"current_password": "admin"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Indique un nuevo usuario o una nueva contraseña"


async def test_update_audit_row_written(client, session):
    user = await _seed_user(session)
    response = await client.patch(
        "/api/auth/me",
        json={
            "current_password": "admin",
            "new_username": "renombrado",
            "new_password": "otra-clave",
        },
        headers=_headers(),
    )
    assert response.status_code == 200
    row = (
        await session.execute(
            select(AuditLog).where(AuditLog.entity_type == "user")
        )
    ).scalar_one()
    assert row.entity_id == user.id
    assert row.action == "update_account"
    assert row.changes_json == {"username": True, "password": True}