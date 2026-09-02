"""Integration tests for the per-seller earnings report (automatic splits)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import Book, Category, Sale, SaleItem, User
from app.schemas.sale import SaleItemCreate
from app.services.sale_service import create_sale

RANGE = "?start_date=2026-08-01&end_date=2026-08-31"


async def _category(session, name="Novela") -> int:
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
    session,
    *,
    title="Rayuela",
    observaciones=None,
    price="10.00",
    stock=100,
) -> Book:
    cid = await _category(session)
    book = Book(
        title=title,
        author="Julio Cortázar",
        editorial="Sudamericana",
        category_id=cid,
        price=price,
        stock=stock,
        observaciones=observaciones,
    )
    session.add(book)
    await session.commit()
    return book


async def _admin(session) -> User:
    user = (
        await session.execute(select(User).where(User.username == "admin"))
    ).scalar_one_or_none()
    if user is None:
        user = User(username="admin", password_hash="x", role="admin")
        session.add(user)
        await session.commit()
    return user


async def _seed_sale(session, book: Book, *, quantity=1, when=None) -> Sale:
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book.id, quantity=quantity)],
    )
    if when is not None:
        sale.date = when
    await session.commit()
    return sale


async def _seed_legacy_sale(session, book: Book, *, when=None, sale_number=999) -> Sale:
    """Insert a sale directly with NULL shares (as pre-split deployments did)."""
    sale = Sale(sale_number=sale_number, total=Decimal("10.00"))
    sale.items.append(
        SaleItem(
            book_id=book.id,
            quantity=1,
            unit_price=Decimal("10.00"),
            subtotal=Decimal("10.00"),
        )
    )
    if when is not None:
        sale.date = when
    session.add(sale)
    await session.commit()
    return sale


def _rows(data):
    return {row["seller"]: row for row in data["rows"]}


async def test_earnings_85_15_split(auth_headers, session, client):
    book = await _seed_book(session, title="Juli Book")  # blank → 85/15
    await _seed_sale(session, book, when=datetime(2026, 8, 10, 12, 0))

    response = await client.get(f"/api/reports/earnings{RANGE}", headers=auth_headers)
    assert response.status_code == 200
    rows = _rows(response.json())
    assert rows["Juli"]["sale_count"] == 1
    assert rows["Juli"]["revenue"] == "8.50"
    assert rows["Cande"]["sale_count"] == 1
    assert rows["Cande"]["revenue"] == "1.50"


async def test_earnings_cande_only_100_0(auth_headers, session, client):
    book = await _seed_book(session, title="Cande Book", observaciones="Cande")
    await _seed_sale(session, book, when=datetime(2026, 8, 10, 12, 0))

    response = await client.get(f"/api/reports/earnings{RANGE}", headers=auth_headers)
    assert response.status_code == 200
    rows = _rows(response.json())
    assert rows["Cande"]["sale_count"] == 1
    assert rows["Cande"]["revenue"] == "10.00"
    assert rows["Juli"]["sale_count"] == 0
    assert rows["Juli"]["revenue"] == "0.00"


async def test_earnings_shared_50_50(auth_headers, session, client):
    book = await _seed_book(session, title="Shared", observaciones="Juli y Cande")
    await _seed_sale(session, book, when=datetime(2026, 8, 10, 12, 0))

    response = await client.get(f"/api/reports/earnings{RANGE}", headers=auth_headers)
    assert response.status_code == 200
    rows = _rows(response.json())
    assert rows["Juli"]["sale_count"] == 1
    assert rows["Juli"]["revenue"] == "5.00"
    assert rows["Cande"]["sale_count"] == 1
    assert rows["Cande"]["revenue"] == "5.00"


async def test_earnings_shared_50_50_odd_cents_do_not_overcount(
    auth_headers, session, client
):
    # 50/50 of 33.33 would independently round to 16.67 + 16.67 = 33.34;
    # the remainder method must yield 16.67 + 16.66 = 33.33 exactly.
    book = await _seed_book(
        session, title="Odd", observaciones="Juli y Cande", price="33.33"
    )
    await _seed_sale(session, book, when=datetime(2026, 8, 10, 12, 0))

    response = await client.get(f"/api/reports/earnings{RANGE}", headers=auth_headers)
    assert response.status_code == 200
    rows = _rows(response.json())
    assert rows["Juli"]["revenue"] == "16.67"
    assert rows["Cande"]["revenue"] == "16.66"
    assert (
        Decimal(rows["Juli"]["revenue"]) + Decimal(rows["Cande"]["revenue"])
        == Decimal("33.33")
    )


async def test_earnings_legacy_null_shares_derived_from_book(
    auth_headers, session, client
):
    book = await _seed_book(session, title="Legacy Cande", observaciones="Cande")
    await _seed_legacy_sale(session, book, when=datetime(2026, 8, 10, 12, 0))

    response = await client.get(f"/api/reports/earnings{RANGE}", headers=auth_headers)
    assert response.status_code == 200
    rows = _rows(response.json())
    assert rows["Cande"]["sale_count"] == 1
    assert rows["Cande"]["revenue"] == "10.00"
    assert rows["Juli"]["sale_count"] == 0
    assert rows["Juli"]["revenue"] == "0.00"


async def test_earnings_accumulates_multiple_sales(auth_headers, session, client):
    juli_book = await _seed_book(session, title="Juli Book")
    cande_book = await _seed_book(
        session, title="Cande Book", observaciones="Cande"
    )
    await _seed_sale(session, juli_book, when=datetime(2026, 8, 10, 12, 0))
    await _seed_sale(session, cande_book, when=datetime(2026, 8, 11, 12, 0))

    response = await client.get(f"/api/reports/earnings{RANGE}", headers=auth_headers)
    rows = _rows(response.json())
    # Juli: 85% of 10 = 8.50; Cande: 15% of 10 + 100% of 10 = 11.50
    assert rows["Juli"]["revenue"] == "8.50"
    assert rows["Juli"]["sale_count"] == 1
    assert rows["Cande"]["revenue"] == "11.50"
    assert rows["Cande"]["sale_count"] == 2


async def test_earnings_date_range_filter(auth_headers, session, client):
    book = await _seed_book(session, title="Dated")
    await _seed_sale(session, book, when=datetime(2026, 8, 10, 12, 0))
    await _seed_sale(session, book, when=datetime(2026, 8, 20, 12, 0))

    response = await client.get(
        "/api/reports/earnings?start_date=2026-08-15&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2026-08-15"
    assert data["end_date"] == "2026-08-31"
    rows = _rows(data)
    # Only the 2026-08-20 sale is in range.
    assert rows["Juli"]["sale_count"] == 1
    assert rows["Juli"]["revenue"] == "8.50"


async def test_earnings_requires_auth(client):
    response = await client.get("/api/reports/earnings")
    assert response.status_code == 401
