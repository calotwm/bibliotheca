"""Excel catalog importer: layout detection, normalization, sheet->category map."""

from .normalizer import (
    DEFAULT_CATEGORIES,
    GENRE_CATEGORY_MAP,
    GENRE_FALLBACK_CATEGORY,
    SHEET_CATEGORY_ALIASES,
    SKIP_SHEETS,
    category_for_genre,
    category_for_sheet,
    has_genre_column,
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
    "GENRE_CATEGORY_MAP",
    "GENRE_FALLBACK_CATEGORY",
    "SHEET_CATEGORY_ALIASES",
    "SKIP_SHEETS",
    "EmptyWorkbookError",
    "ExcelImportError",
    "ParsedRow",
    "ParsedSheet",
    "ParsedWorkbook",
    "UnsupportedFileError",
    "category_for_genre",
    "category_for_sheet",
    "has_genre_column",
    "is_header_row",
    "normalize_header",
    "normalize_sheet_name",
    "parse_workbook",
    "strip_accents",
]