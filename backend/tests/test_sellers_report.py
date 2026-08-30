"""Tests for the per-seller report with the shared-sale 50/50 split.

Shared sales ("Cande y Julieta") count once per seller and their revenue is
split in half between both sellers. Sales without a seller are ignored.
"""

from datetime import date, datetime

from sqlalchemy import select

from app.core.timezone import ba_today
from app.models import Book, Category, Sale, SaleItem, User
from app.schemas.sale import SaleItemCreate
from app.services.sale_service import create_sale


async def _seed_book(session, *, price="10.00", stock=100) -> int:
    category = Category(name="Novela")
    session.add(category)
    await session.commit()
    book = Book(
        title="Rayuela",
        author="Julio Cortázar",
        editorial="Sudamericana",
        category_id=category.id,
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
    session, book_id, *, seller="Cande", quantity=1, when=None
) -> Sale:
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book_id, quantity=quantity)],
        seller=seller,
    )
    if when is not None:
        sale.date = when
    await session.commit()
    return sale


async def test_sellers_individual_sale_full_revenue(auth_headers, session, client):
    book_id = await _seed_book(session, price="10.00")
    await _seed_sale(session, book_id, seller="Cande", quantity=2)

    response = await client.get(
        "/api/reports/sellers?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    by_seller = {item["seller"]: item for item in data["sellers"]}
    assert by_seller["Cande"]["sale_count"] == 1
    assert by_seller["Cande"]["total_revenue"] == "20.00"
    assert by_seller["Cande"]["shared_sale_count"] == 0
    assert by_seller["Cande"]["shared_revenue"] == "0.00"


async def test_sellers_shared_sale_is_split_50_50(auth_headers, session, client):
    book_id = await _seed_book(session, price="40.00")
    await _seed_sale(session, book_id, seller="Cande y Julieta", quantity=2)

    response = await client.get(
        "/api/reports/sellers?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    by_seller = {item["seller"]: item for item in data["sellers"]}

    can = by_seller["Cande"]
    jul = by_seller["Julieta"]
    for entry in (can, jul):
        assert entry["sale_count"] == 1
        assert entry["shared_sale_count"] == 1
        assert entry["total_revenue"] == "40.00"
        assert entry["shared_revenue"] == "40.00"


async def test_sellers_combined_individual_and_shared(auth_headers, session, client):
    book_id = await _seed_book(session, price="10.00")
    await _seed_sale(session, book_id, seller="Cande", quantity=5)  # 50 own
    await _seed_sale(session, book_id, seller="Julieta", quantity=3)  # 30 own
    await _seed_sale(session, book_id, seller="Cande y Julieta", quantity=6)  # 60 shared

    response = await client.get(
        "/api/reports/sellers?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    by_seller = {item["seller"]: item for item in response.json()["sellers"]}

    assert by_seller["Cande"]["sale_count"] == 2
    assert by_seller["Cande"]["total_revenue"] == "80.00"
    assert by_seller["Cande"]["shared_sale_count"] == 1
    assert by_seller["Cande"]["shared_revenue"] == "30.00"

    assert by_seller["Julieta"]["sale_count"] == 2
    assert by_seller["Julieta"]["total_revenue"] == "60.00"
    assert by_seller["Julieta"]["shared_sale_count"] == 1
    assert by_seller["Julieta"]["shared_revenue"] == "30.00"


async def test_sellers_ignores_sales_without_seller(auth_headers, session, client):
    book_id = await _seed_book(session, price="10.00")
    await _seed_sale(session, book_id, seller="Cande")
    sale = Sale(sale_number=999, total=0, seller=None)
    sale.items.append(
        SaleItem(
            book_id=book_id, quantity=1, unit_price=0, subtotal=0
        )
    )
    session.add(sale)
    await session.commit()

    response = await client.get(
        "/api/reports/sellers?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    sellers = {item["seller"]: item for item in data["sellers"]}
    assert list(sellers.keys()) == ["Cande"]
    assert sellers["Cande"]["sale_count"] == 1


async def test_sellers_date_range_filters(auth_headers, session, client):
    book_id = await _seed_book(session, price="10.00")
    await _seed_sale(session, book_id, seller="Cande", when=datetime(2026, 8, 10, 12, 0))
    await _seed_sale(session, book_id, seller="Cande", when=datetime(2026, 8, 20, 12, 0))

    response = await client.get(
        "/api/reports/sellers?start_date=2026-08-15&end_date=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2026-08-15"
    assert data["end_date"] == "2026-08-31"
    assert [item["seller"] for item in data["sellers"]] == ["Cande"]
    assert data["sellers"][0]["sale_count"] == 1
    assert data["sellers"][0]["total_revenue"] == "10.00"


async def test_sellers_defaults_to_current_month(auth_headers, session, client):
    book_id = await _seed_book(session, price="10.00")
    await _seed_sale(session, book_id, seller="Cande")
    await _seed_sale(session, book_id, seller="Julieta", when=datetime(2000, 1, 1, 12, 0))

    response = await client.get("/api/reports/sellers", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    expected_start = ba_today().replace(day=1)
    assert data["start_date"] == expected_start.isoformat()
    assert data["end_date"] == ba_today().isoformat()
    sellers = {item["seller"]: item for item in data["sellers"]}
    assert sellers["Cande"]["sale_count"] == 1
    assert sellers["Cande"]["total_revenue"] == "10.00"


async def test_sellers_requires_auth(client):
    response = await client.get("/api/reports/sellers")
    assert response.status_code == 401