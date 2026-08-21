"""Tests for editorial bulk update: math, scoping, transactionality, auth.

Coverage (REQ-BULK-1/2, REQ-AUTH-5): stock add/set, price set/percent (+/-),
category scoping, preview diff without writes, all-or-nothing apply, cashier
403 on every bulk endpoint.
"""

from decimal import Decimal

from sqlalchemy import select

from app.models import AuditLog, Book, Category, User
from app.security.jwt import create_access_token
from app.security.password import hash_password

BULK_ENDPOINTS = [
    "/api/editorial-bulk-update/preview",
    "/api/editorial-bulk-update/apply",
    "/api/books/bulk-update",
]


async def _category_id(session, name="Novela") -> int:
    existing = (
        await session.execute(select(Category).where(Category.name == name))
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


async def _seed_book(
    session, *, title, editorial="Sudamericana", price="10000.00", stock=5, category="Novela", **overrides
) -> int:
    cid = await _category_id(session, category)
    book = Book(
        title=title,
        author=overrides.get("author", "Autor, Ejemplo"),
        editorial=editorial,
        category_id=cid,
        price=price,
        stock=stock,
    )
    session.add(book)
    await session.commit()
    return book.id


async def _cashier_headers(session):
    user = User(username="cashier", password_hash=hash_password("cashier"), role="cashier")
    session.add(user)
    await session.commit()
    token = create_access_token("cashier", "cashier")
    return {"Authorization": f"Bearer {token}"}


async def _books_by_title(session):
    return {
        b.title: b for b in (await session.execute(select(Book))).scalars().all()
    }


async def test_price_percent_adds_and_rounds(auth_headers, session, client):
    await _seed_book(session, title="A", price="199.99")
    await _seed_book(session, title="B", price="20000.00")
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "price_percent", "amount": "5"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["affected"] == 2
    books = await _books_by_title(session)
    assert books["A"].price == Decimal("209.99")   # 199.99 * 1.05 = 209.9895 -> ROUND_HALF_UP
    assert books["B"].price == Decimal("21000.00")


async def test_price_percent_discount(auth_headers, session, client):
    await _seed_book(session, title="A", price="10000.00")
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "price_percent", "amount": "-10"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    books = await _books_by_title(session)
    assert books["A"].price == Decimal("9000.00")


async def test_price_set(auth_headers, session, client):
    await _seed_book(session, title="A", price="10000.00")
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "price_set", "amount": "15000.50"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    books = await _books_by_title(session)
    assert books["A"].price == Decimal("15000.50")


async def test_stock_add(auth_headers, session, client):
    await _seed_book(session, title="A", stock=3)
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "stock_add", "amount": "7"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    books = await _books_by_title(session)
    assert books["A"].stock == 10


async def test_stock_set(auth_headers, session, client):
    await _seed_book(session, title="A", stock=3)
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "stock_set", "amount": "12"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    books = await _books_by_title(session)
    assert books["A"].stock == 12


async def test_bulk_scoped_by_category(auth_headers, session, client):
    await _seed_book(session, title="N", category="Novela", stock=1)
    poesia_id = await _category_id(session, "Poesía")
    await _seed_book(session, title="P", category="Poesía", stock=1)
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "category_id": poesia_id, "action": "stock_add", "amount": "5"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["affected"] == 1
    books = await _books_by_title(session)
    assert books["N"].stock == 1
    assert books["P"].stock == 6


async def test_bulk_preview_reports_diff_without_writing(auth_headers, session, client):
    await _seed_book(session, title="A", price="10000.00", stock=5)
    response = await client.post(
        "/api/editorial-bulk-update/preview",
        json={"editorial": "Sudamericana", "action": "price_percent", "amount": "10"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["affected"] == 1
    row = data["rows"][0]
    assert row["field"] == "price"
    assert row["old_value"] == "10000.00"
    assert row["new_value"] == "11000.00"
    # Preview must not write anything.
    books = await _books_by_title(session)
    assert books["A"].price == Decimal("10000.00")


async def test_bulk_apply_rolls_back_on_negative_result(auth_headers, session, client):
    await _seed_book(session, title="A", stock=5)
    await _seed_book(session, title="B", stock=3)
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "stock_set", "amount": "-1"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    books = await _books_by_title(session)
    assert books["A"].stock == 5
    assert books["B"].stock == 3


async def test_bulk_stock_amount_must_be_whole(auth_headers, session, client):
    await _seed_book(session, title="A", stock=5)
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "stock_add", "amount": "1.5"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    books = await _books_by_title(session)
    assert books["A"].stock == 5


async def test_books_bulk_update_direct_endpoint(auth_headers, session, client):
    await _seed_book(session, title="A", price="10000.00", stock=5)
    response = await client.post(
        "/api/books/bulk-update",
        json={"editorial": "Sudamericana", "action": "price_percent", "amount": "5"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["affected"] == 1
    books = await _books_by_title(session)
    assert books["A"].price == Decimal("10500.00")


async def test_bulk_audit_logged(auth_headers, session, client):
    await _seed_book(session, title="A", stock=5)
    await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "Sudamericana", "action": "stock_add", "amount": "3"},
        headers=auth_headers,
    )
    logs = (
        await session.execute(
            select(AuditLog).where(AuditLog.action == "bulk_update")
        )
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].changes_json["affected"] == 1
    assert logs[0].changes_json["action"] == "stock_add"


async def test_bulk_author_only_partial_match(auth_headers, session, client):
    await _seed_book(
        session,
        title="Borges",
        author="Borges, Jorge Luis",
        editorial="Emece",
        stock=5,
    )
    await _seed_book(
        session,
        title="Bolaño",
        author="Bolaño, Roberto",
        editorial="Anagrama",
        stock=5,
    )
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"author": "borges", "action": "stock_add", "amount": "5"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["affected"] == 1
    assert response.json()["author"] == "borges"
    books = await _books_by_title(session)
    assert books["Borges"].stock == 10
    assert books["Bolaño"].stock == 5


async def test_bulk_author_scoped_by_category(auth_headers, session, client):
    await _seed_book(
        session,
        title="Borges-N",
        author="Borges, Jorge Luis",
        category="Novela",
        stock=1,
    )
    poesia_id = await _category_id(session, "Poesía")
    await _seed_book(
        session,
        title="Borges-P",
        author="Borges, Jorge Luis",
        category="Poesía",
        stock=1,
    )
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={
            "author": "borges",
            "category_id": poesia_id,
            "action": "stock_add",
            "amount": "5",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["affected"] == 1
    books = await _books_by_title(session)
    assert books["Borges-N"].stock == 1
    assert books["Borges-P"].stock == 6


async def test_bulk_author_works_across_all_endpoints(auth_headers, session, client):
    cases = [
        ("Borges", "Borges, Jorge Luis"),
        ("Bolaño", "Bolaño, Roberto"),
        ("Cortázar", "Cortázar, Julio"),
    ]
    for endpoint, (query, full_name) in zip(BULK_ENDPOINTS, cases):
        await _seed_book(
            session,
            title=query,
            author=full_name,
            editorial="Emece",
            stock=5,
        )
        response = await client.post(
            endpoint,
            json={"author": query.lower(), "action": "stock_add", "amount": "1"},
            headers=auth_headers,
        )
        assert response.status_code == 200, endpoint
        assert response.json()["affected"] == 1, endpoint
        assert response.json()["author"] == query.lower(), endpoint


async def test_bulk_both_editorial_and_author_rejected(auth_headers, session, client):
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={
            "editorial": "Sudamericana",
            "author": "Borges",
            "action": "stock_add",
            "amount": "1",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "no ambos" in str(response.json())


async def test_bulk_neither_editorial_nor_author_rejected(
    auth_headers, session, client
):
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"action": "stock_add", "amount": "1"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = str(response.json())
    assert "Proporcione editorial o autor." in body
    assert "no ambos" not in body


async def test_bulk_audit_includes_author(auth_headers, session, client):
    await _seed_book(
        session,
        title="Borges",
        author="Borges, Jorge Luis",
        editorial="Emece",
        stock=5,
    )
    await client.post(
        "/api/editorial-bulk-update/apply",
        json={"author": "Borges", "action": "stock_add", "amount": "3"},
        headers=auth_headers,
    )
    logs = (
        await session.execute(
            select(AuditLog).where(AuditLog.action == "bulk_update")
        )
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].changes_json["author"] == "Borges"


async def test_bulk_requires_auth(client):
    response = await client.post(
        "/api/editorial-bulk-update/apply",
        json={"editorial": "X", "action": "price_percent", "amount": "5"},
    )
    assert response.status_code == 401


async def test_bulk_forbidden_for_cashier(auth_headers, session, client):
    headers = await _cashier_headers(session)
    payload = {"editorial": "X", "action": "stock_add", "amount": "1"}
    for endpoint in BULK_ENDPOINTS:
        response = await client.post(endpoint, json=payload, headers=headers)
        assert response.status_code == 403, endpoint