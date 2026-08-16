"""Integration tests for book catalog endpoints."""

from decimal import Decimal

from sqlalchemy import select

from app.models import AuditLog, Book, Category, User
from app.security.jwt import create_access_token
from app.security.password import hash_password


async def _category_id(session, name="Novela") -> int:
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


def _book_payload(category_id: int, **overrides) -> dict:
    payload = {
        "title": "Rayuela",
        "author": "Julio Cortázar",
        "editorial": "Sudamericana",
        "category_id": category_id,
        "price": "12.50",
        "stock": 3,
    }
    payload.update(overrides)
    return payload


async def test_create_book(auth_headers, session, client):
    cid = await _category_id(session)
    response = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Rayuela"
    assert data["stock_status"] == "Low"
    assert data["category_name"] == "Novela"


async def test_create_book_requires_auth(client):
    response = await client.post(
        "/api/books", json=_book_payload(1)
    )
    assert response.status_code == 401


async def test_get_book(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]
    response = await client.get(f"/api/books/{book_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == book_id


async def test_get_book_not_found(auth_headers, client):
    response = await client.get("/api/books/9999", headers=auth_headers)
    assert response.status_code == 404


async def test_update_book(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]
    response = await client.put(
        f"/api/books/{book_id}",
        json={"stock": 10, "price": "15.00"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["stock"] == 10
    assert response.json()["stock_status"] == "In Stock"


async def test_update_book_not_found(auth_headers, client):
    response = await client.put(
        "/api/books/9999", json={"stock": 5}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_natural_key_upsert_same_key(auth_headers, session, client):
    cid = await _category_id(session)
    first = await client.post(
        "/api/books", json=_book_payload(cid, price="10.00"), headers=auth_headers
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/books", json=_book_payload(cid, price="20.00"), headers=auth_headers
    )
    assert second.status_code == 200
    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].price == Decimal("20.00")


async def test_natural_key_upsert_case_insensitive(auth_headers, session, client):
    cid = await _category_id(session)
    await client.post(
        "/api/books", json=_book_payload(cid, title="Rayuela"), headers=auth_headers
    )
    second = await client.post(
        "/api/books",
        json=_book_payload(cid, title="  rayuela  ", price="20.00"),
        headers=auth_headers,
    )
    assert second.status_code == 200
    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].price == Decimal("20.00")


async def test_list_books_filters(auth_headers, session, client):
    novela = await _category_id(session, "Novela")
    poesia = await _category_id(session, "Poesía")
    await client.post(
        "/api/books", json=_book_payload(novela, title="Rayuela", stock=0), headers=auth_headers
    )
    await client.post(
        "/api/books",
        json=_book_payload(poesia, title="Ficciones", author="Borges", stock=10),
        headers=auth_headers,
    )

    by_category = await client.get(
        f"/api/books?category_id={novela}", headers=auth_headers
    )
    assert len(by_category.json()) == 1
    assert by_category.json()[0]["title"] == "Rayuela"

    by_search = await client.get("/api/books?q=bor", headers=auth_headers)
    assert len(by_search.json()) == 1
    assert by_search.json()[0]["title"] == "Ficciones"

    by_status = await client.get("/api/books?stock_status=Out", headers=auth_headers)
    assert len(by_status.json()) == 1
    assert by_status.json()[0]["title"] == "Rayuela"


async def test_soft_delete_hides_from_list(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]

    deleted = await client.delete(f"/api/books/{book_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listing = await client.get("/api/books", headers=auth_headers)
    assert all(b["id"] != book_id for b in listing.json())

    # row is preserved (soft-delete), only is_active flipped
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
    assert book.is_active is False


async def test_soft_delete_requires_admin(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]

    session.add(User(username="cashier", password_hash=hash_password("c"), role="cashier"))
    await session.commit()
    cashier_token = create_access_token("cashier", "cashier")

    response = await client.delete(
        f"/api/books/{book_id}",
        headers={"Authorization": f"Bearer {cashier_token}"},
    )
    assert response.status_code == 403


async def test_negative_price_rejected(auth_headers, session, client):
    cid = await _category_id(session)
    response = await client.post(
        "/api/books", json=_book_payload(cid, price="-1.00"), headers=auth_headers
    )
    assert response.status_code == 422


async def test_negative_stock_rejected(auth_headers, session, client):
    cid = await _category_id(session)
    response = await client.post(
        "/api/books", json=_book_payload(cid, stock=-1), headers=auth_headers
    )
    assert response.status_code == 422


async def test_audit_logged_on_book_create(auth_headers, session, client):
    cid = await _category_id(session)
    await client.post("/api/books", json=_book_payload(cid), headers=auth_headers)
    logs = (await session.execute(select(AuditLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].entity_type == "book"
    assert logs[0].action == "create"


async def test_audit_logged_on_book_update(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]
    await client.put(f"/api/books/{book_id}", json={"stock": 7}, headers=auth_headers)
    logs = (
        await session.execute(select(AuditLog).where(AuditLog.action == "update"))
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].changes_json["stock"] == {"old": "3", "new": "7"}
