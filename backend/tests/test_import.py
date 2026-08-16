"""Tests for Excel import: parser layout detection, preview, apply, auth.

Parser fixtures faithfully reproduce the real ``Catálogo Agosto '26.xlsx``
layouts: header sheets (``PRECIO``/``PRECIOS`` variance) and the no-header
6-column OPORTUNIDADES sheet (REQ-IMP-1/2).
"""

import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.excel_import import (
    EmptyWorkbookError,
    UnsupportedFileError,
    parse_workbook,
)
from app.models import Book, Category, User
from app.routers.categories import seed_categories
from app.security.jwt import create_access_token
from app.security.password import hash_password

REAL_CATALOG = Path(r"C:\Users\camil\Downloads\Catálogo Agosto '26.xlsx")

HEADER_WITH_PRECIOS = [
    ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
    ("Rayuela", "Cortázar, Julio", "Sudamericana", 29500, 3),
    (1984, "Orwell, George", "La Pollera", 24000, 1),
]

HEADER_WITH_PRECIO = [
    ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIO", "STOCK"),
    ("El extranjero", "Camus, Albert", "DeBolsillo", 18000, 2),
]

OPORTUNIDADES = [
    ("Ejercicios de ocupación. Afectos, vida y trabajo", "AA.VV. ", "Ensayo", "VenteVeo", 1, 15000),
    ("La política cultural de las emociones", "Ahmed, Sara", "Ensayo", "VenteVeo", 1, 15000),
]

BAD_ROWS = [
    ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
    ("Bueno", "Autor A", "Ed X", 10000, 1),
    ("Sin precio", "Autor B", "Ed Y", None, 1),
    ("Precio inválido", "Autor C", "Ed Z", "abc", 1),
    ("Stock inválido", "Autor D", "Ed W", 5000, "tres"),
]


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


def _parse(sheets: dict[str, list[tuple]], **kwargs):
    return parse_workbook(_xlsx_bytes(sheets), filename="catalog.xlsx", **kwargs)


def test_header_layout_detected_precios_variant():
    parsed = _parse({"NO FICCIÓN": HEADER_WITH_PRECIOS})
    sheet = parsed.sheets[0]
    assert sheet.has_header is True
    assert sheet.category == "No Ficción"
    assert len(sheet.rows) == 2
    first, second = sheet.rows
    assert first.title == "Rayuela"
    assert first.author == "Cortázar, Julio"
    assert first.price == Decimal("29500.00")
    assert first.stock == 3
    assert first.row_number == 2
    assert first.error is None


def test_header_layout_detected_precio_singular_variant():
    parsed = _parse({"NOVELAS": HEADER_WITH_PRECIO})
    sheet = parsed.sheets[0]
    assert sheet.has_header is True
    assert sheet.category == "Novela"
    assert sheet.rows[0].price == Decimal("18000.00")


def test_numeric_title_cell_converted_to_string():
    parsed = _parse({"NOVELAS": HEADER_WITH_PRECIOS})
    assert parsed.sheets[0].rows[1].title == "1984"


def test_oportunidades_layout_detected_without_header():
    parsed = _parse({"Oportunidades": OPORTUNIDADES})
    sheet = parsed.sheets[0]
    assert sheet.has_header is False
    assert sheet.category == "OPORTUNIDADES"
    assert len(sheet.rows) == 2
    first = sheet.rows[0]
    assert first.row_number == 1
    assert first.genre == "Ensayo"
    assert first.editorial == "VenteVeo"
    assert first.price == Decimal("15000.00")
    assert first.stock == 1
    assert first.author == "AA.VV."
    assert first.error is None


def test_bad_rows_flagged_without_aborting():
    parsed = _parse({"CUENTOS": BAD_ROWS})
    sheet = parsed.sheets[0]
    assert sheet.has_header is True
    assert len(sheet.rows) == 4
    ok = [row for row in sheet.rows if row.error is None]
    bad = [row for row in sheet.rows if row.error is not None]
    assert len(ok) == 1
    assert ok[0].title == "Bueno"
    assert len(bad) == 3
    messages = [row.error for row in bad]
    assert any("Missing price" in m for m in messages)
    assert any("Invalid price 'abc'" in m for m in messages)
    assert any("Invalid stock 'tres'" in m for m in messages)


def test_empty_rows_skipped():
    sheets = {
        "NOVELAS": [
            ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
            ("Uno", "Autor", "Ed", 1000, 1),
            (None, None, None, None, None),
            ("Dos", "Autor", "Ed", 2000, 2),
        ]
    }
    parsed = _parse(sheets)
    rows = parsed.sheets[0].rows
    assert [r.title for r in rows] == ["Uno", "Dos"]
    assert [r.row_number for r in rows] == [2, 4]


def test_unsupported_extension_raises():
    with pytest.raises(UnsupportedFileError):
        parse_workbook(b"not really xlsx", filename="catalog.csv")


def test_not_a_zip_raises():
    with pytest.raises(UnsupportedFileError):
        parse_workbook(b"plain text bytes", filename="catalog.xlsx")


def test_empty_workbook_raises():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>',
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>',
        )
    with pytest.raises(EmptyWorkbookError):
        parse_workbook(buffer.getvalue(), filename="empty.xlsx")


def test_mixed_oportunidades_layout_within_one_sheet():
    sheets = {
        "Oportunidades": [
            ("Ejercicios de ocupación. Afectos, vida y trabajo", "AA.VV. ", "Ensayo", "VenteVeo", 1, 15000),
            ("Autobiografía de una mujer emancipada", "Kollontai, Aleksandra", "Sube la marea", 7300, 0),
        ]
    }
    parsed = _parse(sheets)
    sheet = parsed.sheets[0]
    assert sheet.has_header is False
    first, second = sheet.rows
    assert first.genre == "Ensayo"
    assert first.editorial == "VenteVeo"
    assert first.price == Decimal("15000.00")
    assert first.stock == 1
    assert second.genre is None
    assert second.editorial == "Sube la marea"
    assert second.price == Decimal("7300.00")
    assert second.stock == 0
    assert first.error is None
    assert second.error is None


def test_ars_formatted_price_parsed():
    sheets = {
        "POESÍA": [
            ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIO", "STOCK"),
            ("Todas cuerdas", "Romina Freschi", "Hekht", "$22.000,00", 1),
        ]
    }
    parsed = _parse(sheets)
    row = parsed.sheets[0].rows[0]
    assert row.price == Decimal("22000.00")
    assert row.error is None


def test_date_value_in_title_flagged():
    from datetime import datetime

    sheets = {
        "POESÍA": [
            ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIO", "STOCK"),
            (datetime(2026, 11, 25), "Jimena Coppolino", "La mariposa y la iguana", "$24.000,00", 1),
        ]
    }
    parsed = _parse(sheets)
    row = parsed.sheets[0].rows[0]
    assert row.error is not None
    assert "Unexpected date value in title" in row.error


@pytest.mark.skipif(
    not REAL_CATALOG.exists(),
    reason="Real catalog file not present on this machine",
)
def test_real_catalog_file_layouts():
    parsed = parse_workbook(REAL_CATALOG, available_categories=None)
    assert len(parsed.sheets) == 6
    by_name = {sheet.name: sheet for sheet in parsed.sheets}
    assert by_name["NOVELAS"].has_header is True
    assert by_name["NOVELAS"].category == "Novela"
    assert by_name["NO FICCIÓN"].has_header is True
    assert by_name["NO FICCIÓN"].category == "No Ficción"
    assert by_name["POESÍA"].category == "Poesía"
    assert by_name["Oportunidades"].has_header is False
    assert by_name["Oportunidades"].category == "OPORTUNIDADES"
    # Every OPORTUNIDADES row parses despite the mixed 6-col / 5-col layouts.
    assert len(by_name["Oportunidades"].rows) == 18
    assert all(row.error is None for row in by_name["Oportunidades"].rows)
    assert by_name["Oportunidades"].rows[0].genre == "Ensayo"
    assert by_name["Oportunidades"].rows[9].genre is None
    total_valid = sum(
        1 for sheet in parsed.sheets for row in sheet.rows if row.error is None
    )
    total_rows = sum(len(sheet.rows) for sheet in parsed.sheets)
    assert total_valid >= 640
    assert total_rows - total_valid < 5


# --------------------------------------------------------------------------
# Endpoint tests: /api/import/preview and /api/import/apply (REQ-IMP-3/4)
# --------------------------------------------------------------------------

APPLY_FILE = [
    ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
    ("Rayuela", "Cortázar, Julio", "Sudamericana", 29500, 3),   # update (exists)
    ("1984", "Orwell, George", "La Pollera", 24000, 1),          # insert
    ("1984", "Orwell, George", "La Pollera", 24000, 1),          # in-file duplicate -> skip
]


async def _seed_categories(session):
    await seed_categories(session)


async def _category_id(session, name):
    return (
        await session.execute(select(Category).where(Category.name == name))
    ).scalar_one().id


async def _seed_book(session, *, title, author="Cortázar, Julio", editorial="Sudamericana", price="29500.00", stock=5, category="Novela"):
    cid = await _category_id(session, category)
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


async def _cashier_headers(session):
    user = User(username="cashier", password_hash=hash_password("cashier"), role="cashier")
    session.add(user)
    await session.commit()
    token = create_access_token("cashier", "cashier")
    return {"Authorization": f"Bearer {token}"}


async def _preview(client, headers, sheets):
    data = _xlsx_bytes(sheets)
    response = await client.post(
        "/api/import/preview",
        headers=headers,
        files={"file": ("catalog.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    return response


async def test_preview_reports_counts_without_writing(auth_headers, session, client):
    await _seed_categories(session)
    await _seed_book(session, title="Rayuela")
    response = await _preview(client, auth_headers, {"NOVELAS": APPLY_FILE})
    assert response.status_code == 200
    data = response.json()
    assert data["totals"]["inserts"] == 1
    assert data["totals"]["updates"] == 1
    assert data["totals"]["skips"] == 1
    assert data["totals"]["errors"] == 0
    assert data["summaries"][0]["category"] == "Novela"
    assert data["token"]
    # Preview must not write: the new book is still absent.
    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].title == "Rayuela"


async def test_preview_requires_auth(client):
    response = await _preview(client, {}, {"NOVELAS": HEADER_WITH_PRECIO})
    assert response.status_code == 401


async def test_preview_forbidden_for_cashier(auth_headers, session, client):
    await _seed_categories(session)
    headers = await _cashier_headers(session)
    response = await _preview(client, headers, {"NOVELAS": HEADER_WITH_PRECIO})
    assert response.status_code == 403


async def test_preview_rejects_non_xlsx(auth_headers, client):
    response = await client.post(
        "/api/import/preview",
        headers=auth_headers,
        files={"file": ("notes.csv", b"a,b,c\n1,2,3", "text/csv")},
    )
    assert response.status_code == 400


async def test_apply_inserts_updates_and_skips(auth_headers, session, client):
    await _seed_categories(session)
    await _seed_book(session, title="Rayuela", stock=5)
    preview = await _preview(client, auth_headers, {"NOVELAS": APPLY_FILE})
    payload = {"token": preview.json()["token"], "filename": "catalog.xlsx", "sheets": preview.json()["sheets"]}

    response = await client.post("/api/import/apply", json=payload, headers=auth_headers)
    assert response.status_code == 200
    totals = response.json()["totals"]
    assert totals["inserts"] == 1
    assert totals["updates"] == 1
    assert totals["skips"] == 1

    books = (await session.execute(select(Book))).scalars().all()
    by_title = {b.title: b for b in books}
    assert set(by_title) == {"Rayuela", "1984"}
    assert by_title["Rayuela"].stock == 3          # updated from the file
    assert by_title["Rayuela"].price == Decimal("29500.00")
    assert by_title["1984"].stock == 1
    assert by_title["1984"].source_sheet == "NOVELAS"


async def test_apply_rolls_back_everything_on_bad_row(auth_headers, session, client):
    await _seed_categories(session)
    await _seed_book(session, title="Rayuela", stock=5)
    preview = await _preview(client, auth_headers, {"NOVELAS": APPLY_FILE})
    sheets = preview.json()["sheets"]
    sheets.append(
        {
            "sheet": "FANTASÍA",
            "category": "NoExiste",
            "rows": [
                {"row_number": 2, "title": "Cien años", "author": "García Márquez, Gabriel", "editorial": "Sudamericana", "genre": None, "price": "12000.00", "stock": 2, "is_new": True}
            ],
        }
    )
    payload = {"token": preview.json()["token"], "sheets": sheets}

    response = await client.post("/api/import/apply", json=payload, headers=auth_headers)
    assert response.status_code == 400

    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].title == "Rayuela"
    assert books[0].stock == 5  # untouched: valid sheet row was rolled back too


async def test_apply_token_mismatch_rejected(auth_headers, session, client):
    await _seed_categories(session)
    preview = await _preview(client, auth_headers, {"NOVELAS": HEADER_WITH_PRECIO})
    payload = {"token": "deadbeef", "sheets": preview.json()["sheets"]}
    response = await client.post("/api/import/apply", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert (await session.execute(select(Book))).scalars().all() == []


async def test_bad_row_reported_in_preview_and_not_applied(auth_headers, session, client):
    await _seed_categories(session)
    bad_file = [
        ("TÍTULO", "AUTOR", "EDITORIAL", "PRECIOS", "STOCK"),
        ("Bueno", "Autor A", "Ed X", 10000, 1),
        ("Sin precio", "Autor B", "Ed Y", None, 1),
    ]
    preview = await _preview(client, auth_headers, {"NOVELAS": bad_file})
    data = preview.json()
    assert data["totals"]["errors"] == 1
    assert data["errors"][0]["sheet"] == "NOVELAS"
    assert data["errors"][0]["row_number"] == 3
    assert "Missing price" in data["errors"][0]["message"]
    # Only the valid row is offered for apply.
    assert len(data["sheets"][0]["rows"]) == 1

    response = await client.post(
        "/api/import/apply",
        json={"token": data["token"], "sheets": data["sheets"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    titles = {b.title for b in (await session.execute(select(Book))).scalars().all()}
    assert titles == {"Bueno"}


async def test_apply_forbidden_for_cashier(auth_headers, session, client):
    await _seed_categories(session)
    headers = await _cashier_headers(session)
    response = await client.post(
        "/api/import/apply", json={"token": "x", "sheets": []}, headers=headers
    )
    assert response.status_code == 403


async def test_manual_add_uses_same_validation(auth_headers, session, client):
    await _seed_categories(session)
    cid = await _category_id(session, "Novela")
    # Negative price is rejected exactly like an import row would be.
    negative = await client.post(
        "/api/books",
        json={"title": "Negativo", "author": "A", "editorial": "E", "category_id": cid, "price": "-5.00", "stock": 1},
        headers=auth_headers,
    )
    assert negative.status_code == 422
    # Duplicate natural key updates instead of inserting (REQ-CAT-1).
    await _seed_book(session, title="Rayuela", stock=5, price="29500.00")
    duplicate = await client.post(
        "/api/books",
        json={"title": "Rayuela", "author": "Cortázar, Julio", "editorial": "Sudamericana", "category_id": cid, "price": "31000.00", "stock": 9},
        headers=auth_headers,
    )
    assert duplicate.status_code == 200
    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].price == Decimal("31000.00")
    assert books[0].stock == 9