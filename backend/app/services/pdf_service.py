"""Per-sale PDF invoice generation (non-fiscal) via fpdf2 (REQ-PDF-1/2).

Layout: business header (name/CUIT/address/condition from settings), invoice
number + date + cashier, line items, subtotal/total, optional customer data,
and a non-fiscal disclaimer. Spanish labels because the invoice is user-facing.

The PDF is regenerable from the ``Sale`` rows (REQ-PDF-2); ``persist_invoice``
writes the bytes to a storage directory and returns the path, which the caller
stores on ``sale.invoice_pdf_path``.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

from ..config import get_settings
from ..models import Sale

# ``backend/storage/invoices`` — gitignored, never committed.
INVOICE_STORAGE_DIR = (
    Path(__file__).resolve().parents[2] / "storage" / "invoices"
)

MARGIN = 10
PAGE_WIDTH = 210
USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN

_COLS = {
    "detail": 100,
    "qty": 20,
    "price": 35,
    "subtotal": 35,
}


def _latin1(text: object) -> str:
    """Force text into latin-1 (the fpdf2 core-font encoding).

    Characters outside latin-1 (unusual glyphs in titles/customer data) are
    replaced so PDF generation never fails on an unrepresentable character.
    """
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _format_ars(amount: object) -> str:
    """Format an amount as Argentine peso: ``$ 24.000,00``."""
    s = f"{Decimal(amount):,.2f}"
    return "$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _truncate(text: str, max_len: int) -> str:
    text = _latin1(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def invoice_filename(sale_number: int) -> str:
    """Return the on-disk/inline filename for a sale's invoice."""
    return f"factura-{sale_number}.pdf"


def _draw_row(pdf: FPDF, cells: list[tuple[str, float, str]], border=0) -> None:
    pdf.set_x(MARGIN)
    for text, width, align in cells:
        pdf.cell(width, 7, text, border=border, new_x="RIGHT", align=align)
    pdf.ln()


def _draw_total_line(pdf: FPDF, label: str, value: str, *, bold: bool = False) -> None:
    pdf.set_font("helvetica", "B" if bold else "", 11)
    pdf.cell(
        USABLE_WIDTH,
        7,
        _latin1(f"{label}:  {value}"),
        new_x="LMARGIN",
        new_y="NEXT",
        align="R",
    )


def build_invoice_pdf(sale: Sale) -> bytes:
    """Render the sale as a non-fiscal PDF and return the raw bytes."""
    settings = get_settings()

    pdf = FPDF(format="A4")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    # --- Business header --------------------------------------------------
    business_name = _latin1(settings.business_name.strip() or "Librería")
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(USABLE_WIDTH, 10, business_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    if settings.business_condition:
        pdf.cell(
            USABLE_WIDTH, 6, _latin1(settings.business_condition),
            new_x="LMARGIN", new_y="NEXT",
        )
    if settings.business_cuit:
        pdf.cell(
            USABLE_WIDTH, 6, f"CUIT: {_latin1(settings.business_cuit)}",
            new_x="LMARGIN", new_y="NEXT",
        )
    if settings.business_address:
        pdf.cell(
            USABLE_WIDTH, 6, _latin1(settings.business_address),
            new_x="LMARGIN", new_y="NEXT",
        )
    pdf.ln(4)

    # --- Title and invoice meta -------------------------------------------
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(USABLE_WIDTH, 8, "FACTURA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(USABLE_WIDTH, 6, "Documento no fiscal", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.cell(USABLE_WIDTH, 6, f"N° de factura: {sale.sale_number}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(USABLE_WIDTH, 6, f"Fecha: {sale.date.strftime('%d/%m/%Y %H:%M')}",
             new_x="LMARGIN", new_y="NEXT")
    if sale.user is not None and sale.user.username:
        pdf.cell(USABLE_WIDTH, 6, f"Atendió: {_latin1(sale.user.username)}",
                 new_x="LMARGIN", new_y="NEXT")
    if sale.customer_name:
        pdf.cell(USABLE_WIDTH, 6, f"Cliente: {_latin1(sale.customer_name)}",
                 new_x="LMARGIN", new_y="NEXT")
    if sale.customer_cuit:
        pdf.cell(USABLE_WIDTH, 6, f"CUIT cliente: {_latin1(sale.customer_cuit)}",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Line items table --------------------------------------------------
    pdf.set_font("helvetica", "B", 10)
    _draw_row(
        pdf,
        [
            ("Detalle", _COLS["detail"], "L"),
            ("Cant.", _COLS["qty"], "C"),
            ("Precio unit.", _COLS["price"], "R"),
            ("Subtotal", _COLS["subtotal"], "R"),
        ],
        border="B",
    )
    pdf.set_font("helvetica", "", 10)
    for item in sale.items:
        title = item.book.title if item.book is not None else ""
        _draw_row(
            pdf,
            [
                (_truncate(title, 50), _COLS["detail"], "L"),
                (str(item.quantity), _COLS["qty"], "C"),
                (_format_ars(item.unit_price), _COLS["price"], "R"),
                (_format_ars(item.subtotal), _COLS["subtotal"], "R"),
            ],
        )
    pdf.ln(4)

    # --- Totals (no tax line unless one is configured) ---------------------
    _draw_total_line(pdf, "Subtotal", _format_ars(sale.total))
    _draw_total_line(pdf, "TOTAL", _format_ars(sale.total), bold=True)
    pdf.ln(6)

    # --- Footer disclaimer -------------------------------------------------
    pdf.set_font("helvetica", "I", 9)
    pdf.cell(
        USABLE_WIDTH, 6, "Documento no fiscal",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    return bytes(pdf.output())


def persist_invoice(sale_number: int, pdf_bytes: bytes) -> Path:
    """Write invoice bytes to the storage directory; return the file path."""
    directory = INVOICE_STORAGE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / invoice_filename(sale_number)
    path.write_bytes(pdf_bytes)
    return path
