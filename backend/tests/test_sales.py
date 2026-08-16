"""Integration tests for sales POS endpoints and concurrency (REQ-POS)."""

import asyncio
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import build_engine, get_session
from app.main import app
from app.models import AuditLog, Base, Book, Category, Sale, SaleItem, User
from app.security.jwt import create_access_token
from app.security.password import hash_password


async def _category_id(session, name="Novela") -> int:
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


async def _seed_book(session, *, stock=5, price="10.00", title="Rayuela", **overrides) -> int:
    cid = await _category_id(session)
    book = Book(
        title=title,
        author=overrides.get("author", "Julio Cortázar"),
        editorial=overrides.get("editorial", "Sudamericana"),
        category_id=cid,
        price=price,
        stock=stock,
    )
    session.add(book)
    await session.commit()
    return book.id


def _sale_payload(book_id: int, quantity: int = 1, **overrides) -> dict:
    payload = {"items": [{"book_id": book_id, "quantity": quantity}]}
    payload.update(overrides)
    return payload


async def test_create_sale_success(auth_headers, session, client):
    book_id = await _seed_book(session, stock=5, price="12.50")
    response = await client.post(
        "/api/sales", json=_sale_payload(book_id, 2), headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sale_number"] == 1
    assert data["total"] == "25.00"
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["book_id"] == book_id
    assert item["quantity"] == 2
    assert item["unit_price"] == "12.50"
    assert item["subtotal"] == "25.00"

    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
    assert book.stock == 3


async def test_create_sale_requires_auth(client):
    response = await client.post("/api/sales", json=_sale_payload(1))
    assert response.status_code == 401


async def test_oversell_rejected_stock_unchanged(auth_headers, session, client):
    book_id = await _seed_book(session, stock=1, price="8.00")
    response = await client.post(
        "/api/sales", json=_sale_payload(book_id, 2), headers=auth_headers
    )
    assert response.status_code == 409

    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
    assert book.stock == 1
    sales = (await session.execute(select(Sale))).scalars().all()
    assert len(sales) == 0


async def test_oversell_within_one_sale_rolls_back_all(auth_headers, session, client):
    cid = await _category_id(session)
    # seed both books under the same category
    ok = Book(
        title="OK", author="A", editorial="E1", category_id=cid, price="5.00", stock=3
    )
    low = Book(
        title="Low", author="A", editorial="E2", category_id=cid, price="5.00", stock=1
    )
    session.add_all([ok, low])
    await session.commit()
    response = await client.post(
        "/api/sales",
        json={"items": [{"book_id": ok.id, "quantity": 2}, {"book_id": low.id, "quantity": 2}]},
        headers=auth_headers,
    )
    assert response.status_code == 409

    books = (await session.execute(select(Book))).scalars().all()
    stocks = {b.title: b.stock for b in books}
    assert stocks == {"OK": 3, "Low": 1}
    assert len((await session.execute(select(Sale))).scalars().all()) == 0


async def test_sale_unknown_book_404(auth_headers, client):
    response = await client.post("/api/sales", json=_sale_payload(9999), headers=auth_headers)
    assert response.status_code == 404


async def test_sale_empty_items_422(auth_headers, client):
    response = await client.post(
        "/api/sales", json={"items": []}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_sale_zero_quantity_422(auth_headers, session, client):
    book_id = await _seed_book(session)
    response = await client.post(
        "/api/sales", json=_sale_payload(book_id, 0), headers=auth_headers
    )
    assert response.status_code == 422


async def test_price_snapshot_preserved_after_price_change(auth_headers, session, client):
    book_id = await _seed_book(session, stock=5, price="10.00")
    created = await client.post(
        "/api/sales", json=_sale_payload(book_id, 1), headers=auth_headers
    )
    sale_id = created.json()["id"]

    await client.put(f"/api/books/{book_id}", json={"price": "99.00"}, headers=auth_headers)

    detail = await client.get(f"/api/sales/{sale_id}", headers=auth_headers)
    assert detail.status_code == 200
    item = detail.json()["items"][0]
    assert item["unit_price"] == "10.00"
    assert item["subtotal"] == "10.00"
    assert detail.json()["total"] == "10.00"


async def test_invoice_numbers_sequential(auth_headers, session, client):
    book_id = await _seed_book(session, stock=10)
    first = await client.post("/api/sales", json=_sale_payload(book_id), headers=auth_headers)
    second = await client.post("/api/sales", json=_sale_payload(book_id), headers=auth_headers)
    assert first.json()["sale_number"] == 1
    assert second.json()["sale_number"] == 2


async def test_sale_detail_not_found(auth_headers, client):
    response = await client.get("/api/sales/9999", headers=auth_headers)
    assert response.status_code == 404


async def test_sales_list_pagination(auth_headers, session, client):
    book_id = await _seed_book(session, stock=10)
    for _ in range(3):
        await client.post("/api/sales", json=_sale_payload(book_id), headers=auth_headers)

    page1 = await client.get("/api/sales?page=1&page_size=2", headers=auth_headers)
    page2 = await client.get("/api/sales?page=2&page_size=2", headers=auth_headers)
    assert len(page1.json()) == 2
    assert len(page2.json()) == 1
    assert all(item["item_count"] == 1 for item in page1.json())


async def test_sales_list_date_range(auth_headers, session, client):
    book_id = await _seed_book(session, stock=10)
    await client.post("/api/sales", json=_sale_payload(book_id), headers=auth_headers)

    hit = await client.get(
        "/api/sales?start_date=2000-01-01&end_date=2999-12-31", headers=auth_headers
    )
    assert len(hit.json()) == 1

    miss = await client.get(
        "/api/sales?start_date=2000-01-01&end_date=2000-01-02", headers=auth_headers
    )
    assert len(miss.json()) == 0


async def test_audit_logged_on_sale_create(auth_headers, session, client):
    book_id = await _seed_book(session)
    await client.post("/api/sales", json=_sale_payload(book_id), headers=auth_headers)
    logs = (
        await session.execute(select(AuditLog).where(AuditLog.entity_type == "sale"))
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "create"
    assert logs[0].changes_json["sale_number"] == 1


@pytest.fixture
async def concurrent_env(tmp_path):
    """File-based SQLite engine (BEGIN IMMEDIATE + real pool) for race tests."""
    db_path = tmp_path / "concurrency.db"
    engine = build_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_concurrent(engine_factory, *, stock, price="10.00"):
    async with engine_factory() as session:
        user = User(username="admin", password_hash=hash_password("admin"), role="admin")
        session.add(user)
        category = Category(name="Novela")
        session.add(category)
        await session.flush()
        book = Book(
            title="Race Book",
            author="A",
            editorial="E",
            category_id=category.id,
            price=price,
            stock=stock,
        )
        session.add(book)
        await session.commit()
        book_id = book.id
    headers = {"Authorization": f"Bearer {create_access_token('admin', 'admin')}"}
    return book_id, headers


async def test_concurrent_last_stock_exactly_one_succeeds(concurrent_env):
    client, factory = concurrent_env
    book_id, headers = await _seed_concurrent(factory, stock=1)

    async def _post():
        return await client.post(
            "/api/sales", json=_sale_payload(book_id, 1), headers=headers
        )

    results = await asyncio.gather(_post(), _post())
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409]

    async with factory() as session:
        book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
        assert book.stock == 0
        assert len((await session.execute(select(Sale))).scalars().all()) == 1


async def test_concurrent_distinct_invoice_numbers(concurrent_env):
    client, factory = concurrent_env
    book_id, headers = await _seed_concurrent(factory, stock=10)

    async def _post():
        return await client.post(
            "/api/sales", json=_sale_payload(book_id, 1), headers=headers
        )

    results = await asyncio.gather(_post(), _post())
    assert all(r.status_code == 201 for r in results)
    numbers = sorted(r.json()["sale_number"] for r in results)
    assert numbers == [1, 2]

    async with factory() as session:
        book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
        assert book.stock == 8
        items = (await session.execute(select(SaleItem))).scalars().all()
        assert len(items) == 2