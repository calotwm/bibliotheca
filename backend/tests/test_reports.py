"""Integration tests for reports and dashboard endpoints (REQ-REP-1)."""

from datetime import datetime

from sqlalchemy import select

from app.models import Book, Category, Sale, User
from app.schemas.sale import SaleItemCreate
from app.services.sale_service import create_sale


async def _category(session, name: str) -> int:
    category = (
        await session.execute(select(Category).where(Category.name == name))
    ).scalar_one_or_none()
    if category is None:
        category = Category(name=name)
        session.add(category)
        await session.commit()
        return category.id
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
) -> Book:
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


async def _seed_sale(session, book: Book, quantity=1, when=None) -> Sale:
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book.id, quantity=quantity)],
    )
    if when is not None:
        sale.date = when
    await session.commit()
    return sale


async def test_sales_report_empty(auth_headers, client):
    response = await client.get("/api/reports/sales", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_sales"] == 0
    assert data["total_revenue"] == "0.00"
    assert data["by_day"] == []
    assert data["group_by"] is None
    assert data["groups"] == []


async def test_sales_report_totals_and_by_day(auth_headers, session, client):
    book = await _seed_book(session, price="10.00", stock=20)
    await _seed_sale(session, book, quantity=2, when=datetime(2026, 8, 10, 12, 0))
    await _seed_sale(session, book, quantity=1, when=datetime(2026, 8, 10, 15, 0))
    await _seed_sale(session, book, quantity=1, when=datetime(2026, 8, 11, 9, 0))

    response = await client.get("/api/reports/sales", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_sales"] == 3
    assert data["total_revenue"] == "40.00"
    assert data["by_day"] == [
        {"date": "2026-08-10", "sales": 2, "revenue": "30.00"},
        {"date": "2026-08-11", "sales": 1, "revenue": "10.00"},
    ]


async def test_sales_report_date_range(auth_headers, session, client):
    book = await _seed_book(session, stock=20)
    await _seed_sale(session, book, when=datetime(2026, 8, 5, 10, 0))
    await _seed_sale(session, book, when=datetime(2026, 8, 10, 10, 0))
    await _seed_sale(session, book, when=datetime(2026, 8, 20, 10, 0))

    response = await client.get(
        "/api/reports/sales?start_date=2026-08-08&end_date=2026-08-15",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2026-08-08"
    assert data["end_date"] == "2026-08-15"
    assert data["total_sales"] == 1
    assert data["total_revenue"] == "10.00"
    assert data["by_day"] == [{"date": "2026-08-10", "sales": 1, "revenue": "10.00"}]


async def test_sales_report_group_by_category(auth_headers, session, client):
    novela = await _seed_book(
        session, title="Rayuela", category="Novela", price="10.00", stock=20
    )
    poesia = await _seed_book(
        session, title="Odas", author="Pablo Neruda", category="Poesía",
        price="20.00", stock=20,
    )
    await _seed_sale(session, novela, quantity=2, when=datetime(2026, 8, 10, 10, 0))
    await _seed_sale(session, poesia, quantity=1, when=datetime(2026, 8, 10, 11, 0))

    response = await client.get(
        "/api/reports/sales?group_by=category", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["group_by"] == "category"
    assert data["total_revenue"] == "40.00"
    groups = {group["key"]: group for group in data["groups"]}
    assert groups["Novela"]["sales"] == 1
    assert groups["Novela"]["units"] == 2
    assert groups["Novela"]["revenue"] == "20.00"
    assert groups["Poesía"]["sales"] == 1
    assert groups["Poesía"]["units"] == 1
    assert groups["Poesía"]["revenue"] == "20.00"


async def test_sales_report_group_by_editorial(auth_headers, session, client):
    sudamericana = await _seed_book(
        session, title="Rayuela", editorial="Sudamericana", price="10.00", stock=20
    )
    planeta = await _seed_book(
        session, title="Odas", author="Pablo Neruda", editorial="Planeta",
        price="20.00", stock=20,
    )
    await _seed_sale(session, sudamericana, quantity=3, when=datetime(2026, 8, 10, 10, 0))
    await _seed_sale(session, planeta, quantity=1, when=datetime(2026, 8, 10, 11, 0))

    response = await client.get(
        "/api/reports/sales?group_by=editorial", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    groups = {group["key"]: group for group in data["groups"]}
    assert groups["Sudamericana"]["units"] == 3
    assert groups["Sudamericana"]["revenue"] == "30.00"
    assert groups["Planeta"]["units"] == 1
    assert groups["Planeta"]["revenue"] == "20.00"


async def test_sales_report_invalid_group_by_400(auth_headers, client):
    response = await client.get(
        "/api/reports/sales?group_by=unknown", headers=auth_headers
    )
    assert response.status_code == 400


async def test_sales_report_requires_auth(client):
    response = await client.get("/api/reports/sales")
    assert response.status_code == 401


async def test_inventory_status_counts_and_value(auth_headers, session, client):
    await _seed_book(session, title="Out", stock=0, price="1.00")
    await _seed_book(session, title="Single", stock=3, price="10.00")
    await _seed_book(session, title="In", stock=10, price="5.00")

    response = await client.get("/api/reports/inventory", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_books"] == 3
    assert data["total_units"] == 13
    assert data["stock_value"] == "80.00"
    assert data["threshold"] == 5
    assert data["category_id"] is None
    # Binary states only: a single unit is In Stock, no low-stock bucket.
    assert data["status_counts"] == {"In Stock": 2, "Out": 1}


async def test_inventory_category_filter(auth_headers, session, client):
    novela = await _seed_book(session, title="Rayuela", category="Novela", stock=0)
    await _seed_book(session, title="Odas", author="Pablo Neruda",
                     category="Poesía", stock=7)
    cid = await _category(session, "Novela")

    response = await client.get(
        f"/api/reports/inventory?category_id={cid}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_books"] == 1
    assert data["total_units"] == 0
    assert data["category_id"] == cid
    assert data["status_counts"] == {"In Stock": 0, "Out": 1}


async def test_inventory_requires_auth(client):
    response = await client.get("/api/reports/inventory")
    assert response.status_code == 401


async def test_category_report_revenue_and_units(auth_headers, session, client):
    novela = await _seed_book(
        session, title="Rayuela", category="Novela", price="10.00", stock=20
    )
    poesia = await _seed_book(
        session, title="Odas", author="Pablo Neruda", category="Poesía",
        price="20.00", stock=20,
    )
    await _seed_sale(session, novela, quantity=2)
    await _seed_sale(session, poesia, quantity=1)

    response = await client.get("/api/reports/category", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    by_name = {item["category"]: item for item in data}
    assert by_name["Novela"]["units"] == 2
    assert by_name["Novela"]["revenue"] == "20.00"
    assert by_name["Novela"]["sales"] == 1
    assert by_name["Poesía"]["units"] == 1
    assert by_name["Poesía"]["revenue"] == "20.00"


async def test_category_report_includes_empty_categories(auth_headers, session, client):
    await _seed_book(session, title="Rayuela", category="Novela", price="10.00", stock=5)
    await _category(session, "Poesía")

    response = await client.get("/api/reports/category", headers=auth_headers)
    data = response.json()
    by_name = {item["category"]: item for item in data}
    assert by_name["Poesía"]["units"] == 0
    assert by_name["Poesía"]["revenue"] == "0.00"
    assert by_name["Poesía"]["sales"] == 0


async def test_category_report_requires_auth(client):
    response = await client.get("/api/reports/category")
    assert response.status_code == 401


async def test_editorial_report_revenue_and_units(auth_headers, session, client):
    s1 = await _seed_book(session, title="A", editorial="E1", price="10.00", stock=20)
    s2 = await _seed_book(session, title="B", author="Pablo Neruda",
                          editorial="E2", price="5.00", stock=20)
    await _seed_sale(session, s1, quantity=3)
    await _seed_sale(session, s2, quantity=1)

    response = await client.get("/api/reports/editorial", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    by_ed = {item["editorial"]: item for item in data}
    assert by_ed["E1"]["units"] == 3
    assert by_ed["E1"]["revenue"] == "30.00"
    assert by_ed["E2"]["units"] == 1
    assert by_ed["E2"]["revenue"] == "5.00"


async def test_editorial_report_includes_empty_editorials(auth_headers, session, client):
    await _seed_book(session, title="A", editorial="E1", price="10.00", stock=5)
    await _seed_book(session, title="B", author="Pablo Neruda", editorial="E2",
                     price="10.00", stock=5)

    response = await client.get("/api/reports/editorial", headers=auth_headers)
    data = response.json()
    by_ed = {item["editorial"]: item for item in data}
    assert by_ed["E2"]["units"] == 0
    assert by_ed["E2"]["revenue"] == "0.00"


async def test_editorial_report_requires_auth(client):
    response = await client.get("/api/reports/editorial")
    assert response.status_code == 401


async def test_dashboard_shape(auth_headers, session, client):
    book = await _seed_book(session, price="10.00", stock=8)
    await _seed_sale(session, book, quantity=1)

    response = await client.get("/api/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_books"] == 1
    assert data["total_units"] == 7
    assert data["stock_value"] == "70.00"
    assert data["today_sales"] == {"count": 1, "revenue": "10.00"}
    assert data["out_of_stock_count"] == 0
    assert len(data["low_stock"]) == 0
    assert len(data["recent_sales"]) == 1
    assert data["recent_sales"][0]["sale_number"] == 1
    assert data["recent_sales"][0]["item_count"] == 1


async def test_dashboard_low_stock_list_and_out_of_stock(auth_headers, session, client):
    await _seed_book(session, title="Out", stock=0)
    await _seed_book(session, title="Low1", stock=2)
    await _seed_book(session, title="Low2", stock=5)
    await _seed_book(session, title="Fine", stock=10)

    response = await client.get("/api/dashboard", headers=auth_headers)
    data = response.json()
    assert data["out_of_stock_count"] == 1
    # The former low-stock list now surfaces only out-of-stock books; any book
    # with stock 1..N must be excluded.
    titles = [item["title"] for item in data["low_stock"]]
    assert titles == ["Out"]
    assert all(item["stock_status"] == "Out" for item in data["low_stock"])
    assert data["low_stock"][0]["stock"] == 0


async def test_dashboard_recent_sales_limited_to_10(auth_headers, session, client):
    book = await _seed_book(session, stock=100)
    for _ in range(12):
        await _seed_sale(session, book, quantity=1)

    response = await client.get("/api/dashboard", headers=auth_headers)
    data = response.json()
    assert len(data["recent_sales"]) == 10
    assert data["today_sales"]["count"] == 12


async def test_dashboard_requires_auth(client):
    response = await client.get("/api/dashboard")
    assert response.status_code == 401