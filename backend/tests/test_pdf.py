"""Tests for per-sale PDF invoice generation (REQ-PDF-1/2)."""

import re
import zlib
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import Book, Category, Sale, SaleItem, User
from app.services import pdf_service


def _decode_pdf_string(raw: bytes) -> str:
    text = raw.decode("latin-1")
    out: list[str] = []
    i = 0
    escapes = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
        "(": "(",
        ")": ")",
        "\\": "\\",
    }
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt in escapes:
                out.append(escapes[nxt])
                i += 2
                continue
            if nxt.isdigit() and i + 3 < len(text):
                out.append(chr(int(text[i + 1 : i + 4], 8)))
                i += 4
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(char)
        i += 1
    return "".join(out)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract the text fpdf2 wrote to the (possibly compressed) content streams."""
    texts: list[str] = []
    for stream in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        data = stream.group(1)
        try:
            data = zlib.decompress(data)
        except zlib.error:
            pass
        for match in re.finditer(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", data):
            texts.append(_decode_pdf_string(match.group(1)))
    return "\n".join(texts)


def _make_sale() -> Sale:
    book = Book(
        title="Rayuela", author="Julio Cortázar", editorial="Sudamericana"
    )
    item = SaleItem(
        quantity=2,
        unit_price=Decimal("12.50"),
        subtotal=Decimal("25.00"),
        book=book,
    )
    cashier = User(username="admin", role="admin")
    return Sale(
        sale_number=1,
        total=Decimal("25.00"),
        customer_name="Ana García",
        customer_cuit="20-12345678-9",
        items=[item],
        user=cashier,
        date=datetime(2026, 8, 16, 10, 30),
    )


def test_build_invoice_pdf_returns_nonempty_pdf():
    pdf_bytes = pdf_service.build_invoice_pdf(_make_sale())
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 200


def test_build_invoice_pdf_contains_expected_fields():
    pdf_bytes = pdf_service.build_invoice_pdf(_make_sale())
    text = _extract_pdf_text(pdf_bytes)
    assert "FACTURA" in text
    assert "Documento no fiscal" in text
    assert "N° de factura: 1" in text
    assert "TOTAL" in text
    assert "Rayuela" in text
    assert "Ana García" in text
    # Accented business header from env renders correctly (latin-1 core font).
    assert "Librería El Estante" in text


def test_invoice_filename():
    assert pdf_service.invoice_filename(42) == "factura-42.pdf"


async def _category_id(session) -> int:
    category = Category(name="Novela")
    session.add(category)
    await session.commit()
    return category.id


async def _seed_book(session, *, stock=5, price="10.00", title="Rayuela") -> int:
    cid = await _category_id(session)
    book = Book(
        title=title,
        author="Julio Cortázar",
        editorial="Sudamericana",
        category_id=cid,
        price=price,
        stock=stock,
    )
    session.add(book)
    await session.commit()
    return book.id


async def test_invoice_endpoint_returns_pdf(auth_headers, session, client):
    book_id = await _seed_book(session, stock=5, price="12.50")
    created = await client.post(
        "/api/sales",
        json={
            "items": [{"book_id": book_id, "quantity": 2}],
            "seller": "Cande",
            "customer_name": "Ana García",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    sale_id = created.json()["id"]

    response = await client.get(
        f"/api/sales/{sale_id}/invoice.pdf", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert "inline" in disposition
    assert "factura-" in disposition
    assert disposition.rstrip('"').endswith(".pdf")
    assert response.content.startswith(b"%PDF")

    sale = (
        await session.execute(select(Sale).where(Sale.id == sale_id))
    ).scalar_one()
    assert sale.invoice_pdf_path is not None
    assert sale.invoice_pdf_path.endswith("factura-1.pdf")


async def test_invoice_endpoint_reprint_regenerates(auth_headers, session, client):
    book_id = await _seed_book(session)
    created = await client.post(
        "/api/sales", json={"items": [{"book_id": book_id, "quantity": 1}], "seller": "Cande"},
        headers=auth_headers,
    )
    sale_id = created.json()["id"]
    first = await client.get(f"/api/sales/{sale_id}/invoice.pdf", headers=auth_headers)
    second = await client.get(f"/api/sales/{sale_id}/invoice.pdf", headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content.startswith(b"%PDF")
    assert second.content.startswith(b"%PDF")


async def test_invoice_missing_sale_404(auth_headers, client):
    response = await client.get("/api/sales/9999/invoice.pdf", headers=auth_headers)
    assert response.status_code == 404


async def test_invoice_requires_auth(client):
    response = await client.get("/api/sales/1/invoice.pdf")
    assert response.status_code == 401