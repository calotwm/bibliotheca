"""Tests for REPLACE-mode import: deactivation of absent books + sales safety.

When a catalog Excel is imported it overwrites the catalog state: books present
in the file are upserted (and re-activated); books absent from the file are
deactivated (``is_active = False``). This must never touch sales history.
"""

import io
from datetime import datetime

from openpyxl import Workbook
from sqlalchemy import select

from app.models import Book, Category, Sale, SaleItem, User
from app.routers.categories import seed_categories
from app.schemas.sale import SaleItemCreate
from app.services.sale_service import create_sale


def _xlsx_bytes(sheets: dict[str, list[tuple]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(title=name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def _category_id(session, name="Novela") -> int:
    return (
        await session.execute(select(Category).where(Category.name == name))
    ).scalar_one().id


async def _seed_book(
    session,
    *,
    title,
    author="Cortázar, Julio",
    editorial="Sudamericana",
    price="10.00",
    stock=5,
    observaciones=None,
) -> int:
    cid = await _category_id(session)
    book = Book(
        title=title,
        author=author,
        editorial=editorial,
        category_id=cid,
        price=price,
        stock=stock,
        observaciones=observaciones,
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


async def _preview(client, headers, sheets):
    response = await client.post(
        "/api/import/preview",
        headers=headers,
        files={
            "file": (
                "catalog.xlsx",
                _xlsx_bytes(sheets),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


async def _apply(client, headers, preview):
    return await client.post(
        "/api/import/apply",
        json={
            "token": preview["token"],
            "filename": preview["filename"],
            "sheets": preview["sheets"],
            "deactivated": preview["deactivated"],
        },
        headers=headers,
    )


SINGLE_ROW = [
    ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
    ("Presente", "Cortázar, Julio", "Sudamericana", 10000, 1),
]


async def test_preview_computes_deactivated_count(auth_headers, session, client):
    await seed_categories(session)
    await _seed_book(session, title="Presente")
    await _seed_book(session, title="Ausente A", editorial="EdA")
    await _seed_book(session, title="Ausente B", editorial="EdB")

    preview = await _preview(client, auth_headers, {"NOVELAS": SINGLE_ROW})
    assert preview["deactivated"] == 2


async def test_apply_deactivates_absent_books(auth_headers, session, client):
    await seed_categories(session)
    present_id = await _seed_book(session, title="Presente", stock=5)
    absent_id = await _seed_book(session, title="Ausente", editorial="EdA", stock=5)

    preview = await _preview(client, auth_headers, {"NOVELAS": SINGLE_ROW})
    response = await _apply(client, auth_headers, preview)
    assert response.status_code == 200
    assert response.json()["deactivated"] == 1

    session.expire_all()
    present = (await session.execute(select(Book).where(Book.id == present_id))).scalar_one()
    absent = (await session.execute(select(Book).where(Book.id == absent_id))).scalar_one()
    assert present.is_active is True
    assert absent.is_active is False


async def test_apply_reactivates_present_books(auth_headers, session, client):
    await seed_categories(session)
    cid = await _category_id(session)
    book = Book(
        title="Reactivar",
        author="Autor A",
        editorial="EdA",
        category_id=cid,
        price="10.00",
        stock=5,
        is_active=False,
    )
    session.add(book)
    await session.commit()
    book_id = book.id

    file = [
        ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
        ("Reactivar", "Autor A", "EdA", 10000, 2),
    ]
    preview = await _preview(client, auth_headers, {"NOVELAS": file})
    response = await _apply(client, auth_headers, preview)
    assert response.status_code == 200

    session.expire_all()
    refreshed = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
    assert refreshed.is_active is True
    assert refreshed.stock == 2


async def test_apply_token_mismatch_on_deactivated_shift(auth_headers, session, client):
    # The deactivated count is part of the reviewed payload: a stale preview
    # whose deactivated count no longer matches is rejected.
    await seed_categories(session)
    await _seed_book(session, title="Presente")
    await _seed_book(session, title="Ausente", editorial="EdA")

    preview = await _preview(client, auth_headers, {"NOVELAS": SINGLE_ROW})
    assert preview["deactivated"] == 1
    response = await client.post(
        "/api/import/apply",
        json={
            "token": preview["token"],
            "filename": preview["filename"],
            "sheets": preview["sheets"],
            "deactivated": 0,  # stale: actual count is 1
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


async def test_sales_of_deactivated_book_still_in_reports(auth_headers, session, client):
    await seed_categories(session)
    book_id = await _seed_book(session, title="Vendible", stock=10)
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book_id, quantity=1)],
    )
    sale.date = datetime(2026, 8, 10, 12, 0)
    await session.commit()
    sale_id = sale.id

    # Import a file that does NOT include "Vendible" -> it gets deactivated.
    preview = await _preview(client, auth_headers, {"NOVELAS": SINGLE_ROW})
    response = await _apply(client, auth_headers, preview)
    assert response.status_code == 200

    session.expire_all()
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
    assert book.is_active is False

    # The sale is still visible in the sales-detail report.
    detail = await client.get("/api/reports/sales-detail", headers=auth_headers)
    assert detail.status_code == 200
    assert any(row["sale_id"] == sale_id for row in detail.json())

    # And it still contributes to the per-seller earnings report.
    earnings = await client.get(
        "/api/reports/earnings?start_date=2000-01-01&end_date=2999-12-31",
        headers=auth_headers,
    )
    assert earnings.status_code == 200
    rows = {row["seller"]: row for row in earnings.json()["rows"]}
    assert rows["Juli"]["sale_count"] == 1
    assert rows["Juli"]["revenue"] == "8.50"
    assert rows["Cande"]["revenue"] == "1.50"


async def test_import_never_touches_sale_rows(auth_headers, session, client):
    await seed_categories(session)
    book_id = await _seed_book(session, title="Vendible", stock=10)
    sale = await create_sale(
        session,
        cashier=await _admin(session),
        items=[SaleItemCreate(book_id=book_id, quantity=2)],
        observaciones="Juli y Cande",
    )
    sale.date = datetime(2026, 8, 10, 12, 0)
    await session.commit()
    sale_id = sale.id
    original_total = str(sale.total)
    original_juli = str(sale.juli_share)
    original_cande = str(sale.cande_share)
    original_observaciones = sale.observaciones

    preview = await _preview(client, auth_headers, {"NOVELAS": SINGLE_ROW})
    response = await _apply(client, auth_headers, preview)
    assert response.status_code == 200

    # Sales data is untouched by the import.
    session.expire_all()
    refreshed = (await session.execute(select(Sale).where(Sale.id == sale_id))).scalar_one()
    assert str(refreshed.total) == original_total
    assert str(refreshed.juli_share) == original_juli
    assert str(refreshed.cande_share) == original_cande
    assert refreshed.observaciones == original_observaciones

    items = (
        await session.execute(select(SaleItem).where(SaleItem.sale_id == sale_id))
    ).scalars().all()
    assert len(items) == 1
    assert items[0].book_id == book_id
    assert items[0].quantity == 2
