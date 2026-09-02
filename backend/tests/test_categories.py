"""Tests for category endpoints and the category seed."""

from sqlalchemy import select

from app.models import Category
from app.routers.categories import DEFAULT_CATEGORIES, seed_categories
from app.security.jwt import create_access_token
from app.security.password import hash_password
from app.models import User


def test_default_categories_after_consolidation():
    assert len(DEFAULT_CATEGORIES) == 7
    assert "No Ficción" in DEFAULT_CATEGORIES
    assert "Teatro" in DEFAULT_CATEGORIES
    # Consolidated categories are gone from the seed.
    assert "Ensayo" not in DEFAULT_CATEGORIES
    assert "Biografía" not in DEFAULT_CATEGORIES


async def test_seed_creates_all_default_categories(session):
    await seed_categories(session)
    names = set((await session.execute(select(Category.name))).scalars().all())
    assert names == set(DEFAULT_CATEGORIES)
    assert len(names) == len(DEFAULT_CATEGORIES)
    assert "No Ficción" in names
    assert "Ensayo" not in names
    assert "Biografía" not in names


async def test_seed_is_idempotent(session):
    await seed_categories(session)
    await seed_categories(session)
    count = (
        await session.execute(select(Category).where(Category.name.in_(DEFAULT_CATEGORIES)))
    ).scalars().all()
    assert len(count) == len(DEFAULT_CATEGORIES)


async def test_list_categories_requires_auth(client):
    response = await client.get("/api/categories")
    assert response.status_code == 401


async def test_list_categories(auth_headers, session, client):
    await seed_categories(session)
    response = await client.get("/api/categories", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(DEFAULT_CATEGORIES)
    assert {c["name"] for c in data} == set(DEFAULT_CATEGORIES)


async def test_create_category_admin_only(session, client):
    # cashier (non-admin) cannot create a category
    session.add(User(username="cashier", password_hash=hash_password("c"), role="cashier"))
    await session.commit()
    token = create_access_token("cashier", "cashier")
    response = await client.post(
        "/api/categories",
        json={"name": "Drama"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_create_category(auth_headers, session, client):
    response = await client.post(
        "/api/categories", json={"name": "Drama"}, headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Drama"
    names = (await session.execute(select(Category.name))).scalars().all()
    assert "Drama" in names
