"""Tests for the per-item sales detail report (REQ-REP detail view)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import Book, Category, Sale, SaleItem, User
from app.schemas.sale import SaleItemCreate
from app.services.sale_service import create_sale


async def _category(session, name: str) -> int:
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


async def _seed_book(
    session,
    *,
    title="Rayuela",
    author="Julio Cortázar",
    editorial="Sudamericana",
    category="Novela",
    price="10.00",
    stock=10,
) -> int:
    cid = await _category(session, category)
    book = Book(
        title=title,
        author=author,
        editorial=editorial,
        category_id=cid,
        price=price,
        stock=stock,
    )
    session.add(book)
    await session.commit()
    return book.id


async def _admin(session) -> User:
    user = (
        await session.execute(select(User).where(User.username == "admin"))
    ).scalar_one_or_none()
    if user is None:
        user = User(username="admin", password_hash="x", role="admin")
        session.add(user)
        await session.commit()
    return user


async def _seed_sale(
    session,
    book_id,
    *,
    quantity=1,
    when=None,
    payment_method=None,
) -> Sale:
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book_id, quantity=quantity)],
        payment_method=payment_method,
    )
    if when is not None:
        sale.date = when
    await session.commit()
    return sale


async def _seed_legacy_sale_without_shares(session, book_id) -> Sale:
    """Insert a sale row directly (as pre-share deployments would have)."""
    sale = Sale(sale_number=1, total=Decimal("10.00"))
    sale.items.append(
        SaleItem(
            book_id=book_id,
            quantity=1,
            unit_price=Decimal("10.00"),
            subtotal=Decimal("10.00"),
        )
    )
    session.add(sale)
    await session.commit()
    return sale


async def test_sales_detail_returns_expected_columns_and_orders_by_date(
    auth_headers, session, client
):
    book_id = await _seed_book(session, stock=10)
    old = await _seed_sale(
        session,
        book_id,
        quantity=2,
        when=datetime(2026, 8, 10, 12, 0),
        payment_method="Efectivo",
    )
    recent = await _seed_sale(
        session, book_id, when=datetime(2026, 8, 15, 12, 0)
    )
    assert old.id != recent.id

    response = await client.get("/api/reports/sales-detail", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()

    # One row per sold line (the older sale is a single line with quantity 2).
    assert len(rows) == 2
    assert rows[0]["sale_id"] == recent.id
    assert rows[1]["sale_id"] == old.id

    row = rows[0]
    assert row["sale_number"] == recent.sale_number
    assert row["title"] == "Rayuela"
    assert row["author"] == "Julio Cortázar"
    assert row["editorial"] == "Sudamericana"
    assert row["category"] == "Novela"
    assert row["unit_price"] == "10.00"
    assert row["quantity"] == 1
    assert row["subtotal"] == "10.00"
    assert row["payment_method"] is None
    assert row["date"] == "2026-08-15"
    # Current stock after the 3 sold units (10 - 3).
    assert row["stock"] == 7

    old_row = rows[1]
    assert old_row["quantity"] == 2
    assert old_row["subtotal"] == "20.00"
    assert old_row["payment_method"] == "Efectivo"
    assert old_row["date"] == "2026-08-10"


async def test_sales_detail_older_sale_rows_share_the_same_stock(
    auth_headers, session, client
):
    book_id = await _seed_book(session, stock=10)
    await _seed_sale(session, book_id, quantity=2, when=datetime(2026, 8, 10, 12, 0))

    response = await client.get("/api/reports/sales-detail", headers=auth_headers)
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["quantity"] == 2
    assert rows[0]["stock"] == 8


async def test_sales_detail_legacy_sale_surfaces_none_fields(
    auth_headers, session, client
):
    book_id = await _seed_book(session)
    sale = await _seed_legacy_sale_without_shares(session, book_id)

    response = await client.get("/api/reports/sales-detail", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sale_id"] == sale.id
    assert rows[0]["payment_method"] is None
    assert rows[0]["observaciones"] is None


async def test_sales_detail_datetime_is_ba_local_consistent(
    auth_headers, session, client
):
    book_id = await _seed_book(session, stock=10)
    # Stored instant 2026-08-29 00:30 UTC == 2026-08-28 21:30 Buenos Aires.
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 0, 30))

    response = await client.get("/api/reports/sales-detail", headers=auth_headers)
    assert response.status_code == 200
    row = response.json()[0]
    # `date` and `sale_datetime` derive from the SAME BA-local instant.
    assert row["date"] == "2026-08-28"
    assert row["sale_datetime"] == "2026-08-28T21:30:00"
    assert row["sale_datetime"].startswith(row["date"])


async def test_sales_detail_date_range_uses_buenos_aires_days(
    auth_headers, session, client
):
    book_id = await _seed_book(session)
    # 02:59 UTC = 23:59 on 2026-08-28 in Buenos Aires.
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 2, 59))
    # 03:30 UTC = 00:30 on 2026-08-29 in Buenos Aires.
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 3, 30))

    day_29 = await client.get(
        "/api/reports/sales-detail?start_date=2026-08-29&end_date=2026-08-29",
        headers=auth_headers,
    )
    assert day_29.status_code == 200
    assert len(day_29.json()) == 1
    assert day_29.json()[0]["date"] == "2026-08-29"

    day_28 = await client.get(
        "/api/reports/sales-detail?start_date=2026-08-28&end_date=2026-08-28",
        headers=auth_headers,
    )
    assert day_28.status_code == 200
    assert len(day_28.json()) == 1
    assert day_28.json()[0]["date"] == "2026-08-28"


async def test_sales_detail_requires_auth(client):
    response = await client.get("/api/reports/sales-detail")
    assert response.status_code == 401