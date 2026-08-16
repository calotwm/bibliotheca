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

from app.excel_import import (
    EmptyWorkbookError,
    UnsupportedFileError,
    parse_workbook,
)

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