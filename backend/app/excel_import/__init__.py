"""Excel catalog importer: layout detection, normalization, sheet->category map."""

from .normalizer import (
    DEFAULT_CATEGORIES,
    SHEET_CATEGORY_ALIASES,
    category_for_sheet,
    is_header_row,
    normalize_header,
    normalize_sheet_name,
    strip_accents,
)
from .parser import (
    EmptyWorkbookError,
    ExcelImportError,
    ParsedRow,
    ParsedSheet,
    ParsedWorkbook,
    UnsupportedFileError,
    parse_workbook,
)

__all__ = [
    "DEFAULT_CATEGORIES",
    "SHEET_CATEGORY_ALIASES",
    "EmptyWorkbookError",
    "ExcelImportError",
    "ParsedRow",
    "ParsedSheet",
    "ParsedWorkbook",
    "UnsupportedFileError",
    "category_for_sheet",
    "is_header_row",
    "normalize_header",
    "normalize_sheet_name",
    "parse_workbook",
    "strip_accents",
]