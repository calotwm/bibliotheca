"""Tests for Buenos Aires timezone boundaries (UTC-3, no DST).

Seeded datetime values are naive and interpreted as UTC throughout the suite:
``datetime(2026, 8, 29, 3, 30)`` is 03:30 UTC, i.e. 00:30 on 2026-08-29 in
Buenos Aires; ``datetime(2026, 8, 29, 2, 59)`` is 23:59 on the previous day.
"""

from datetime import date, datetime, timezone

from sqlalchemy import select

from app.core.timezone import (
    TZ_NAME,
    UTC,
    ba_local_date,
    ba_today,
    day_bounds_utc,
)
from app.models import Book, Category, Sale, User
from app.schemas.sale import SaleItemCreate
from app.services.sale_service import create_sale


def test_buenos_aires_uses_fixed_utc_minus_three():
    assert TZ_NAME == "America/Argentina/Buenos_Aires"
    assert str(UTC) == "UTC"


def test_day_bounds_utc_for_buenos_aires_day():
    start, end = day_bounds_utc(date(2026, 8, 29))
    assert start == datetime(2026, 8, 29, 3, 0, tzinfo=UTC)
    assert end == datetime(2026, 8, 30, 2, 59, 59, 999999, tzinfo=UTC)


def test_ba_local_date_conversion():
    assert ba_local_date(datetime(2026, 8, 29, 3, 30)) == date(2026, 8, 29)
    assert ba_local_date(datetime(2026, 8, 29, 2, 59)) == date(2026, 8, 28)
    # Aware UTC values convert the same way (PostgreSQL returns aware datetimes).
    assert ba_local_date(datetime(2026, 8, 29, 3, 30, tzinfo=UTC)) == date(2026, 8, 29)


def test_ba_today_returns_a_date():
    assert isinstance(ba_today(), date)


async def _category(session, name="Novela") -> int:
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


async def _seed_book(session, *, stock=10, price="10.00") -> int:
    cid = await _category(session)
    book = Book(
        title="Rayuela",
        author="Julio Cortázar",
        editorial="Sudamericana",
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


async def _seed_sale(session, book_id, *, when: datetime, quantity=1) -> Sale:
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book_id, quantity=quantity)],
        seller="Cande",
    )
    sale.date = when
    await session.commit()
    return sale


async def test_by_day_groups_stored_instants_by_buenos_aires_day(
    auth_headers, session, client
):
    book_id = await _seed_book(session, stock=20)
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 3, 30))
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 2, 59))

    response = await client.get(
        "/api/reports/sales?start_date=2026-08-25&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_sales"] == 2
    assert data["by_day"] == [
        {"date": "2026-08-28", "sales": 1, "revenue": "10.00"},
        {"date": "2026-08-29", "sales": 1, "revenue": "10.00"},
    ]


async def test_range_uses_buenos_aires_days(auth_headers, session, client):
    book_id = await _seed_book(session, stock=20)
    early = await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 2, 59))
    late = await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 3, 30))

    on_day_29 = await client.get(
        "/api/reports/sales?start_date=2026-08-29&end_date=2026-08-29",
        headers=auth_headers,
    )
    assert on_day_29.status_code == 200
    assert on_day_29.json()["total_sales"] == 1
    assert on_day_29.json()["by_day"] == [
        {"date": "2026-08-29", "sales": 1, "revenue": "10.00"}
    ]

    on_day_28 = await client.get(
        "/api/reports/sales?start_date=2026-08-28&end_date=2026-08-28",
        headers=auth_headers,
    )
    assert on_day_28.status_code == 200
    assert on_day_28.json()["total_sales"] == 1
    assert on_day_28.json()["by_day"] == [
        {"date": "2026-08-28", "sales": 1, "revenue": "10.00"}
    ]

    assert early.id != late.id


async def test_sales_list_range_uses_buenos_aires_days(
    auth_headers, session, client
):
    book_id = await _seed_book(session, stock=20)
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 2, 59))
    await _seed_sale(session, book_id, when=datetime(2026, 8, 29, 3, 30))

    day_29 = await client.get(
        "/api/sales?start_date=2026-08-29&end_date=2026-08-29", headers=auth_headers
    )
    assert day_29.status_code == 200
    assert len(day_29.json()) == 1

    day_28 = await client.get(
        "/api/sales?start_date=2026-08-28&end_date=2026-08-28", headers=auth_headers
    )
    assert day_28.status_code == 200
    assert len(day_28.json()) == 1


async def test_dashboard_today_uses_buenos_aires_day(auth_headers, session, client):
    book_id = await _seed_book(session, stock=20)
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book_id, quantity=1)],
        seller="Cande",
    )
    # Overwrite with the current absolute instant as UTC (naive = UTC).
    sale.date = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()

    response = await client.get("/api/dashboard", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["today_sales"]["count"] == 1

    stored = (
        await session.execute(select(Sale).where(Sale.id == sale.id))
    ).scalar_one()
    assert ba_local_date(stored.date) == ba_today()