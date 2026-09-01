"""Excel header and sheet-name normalization for the catalog importer.

Display strings keep their original case; matching uses the normalized form
(strip whitespace, fold case, strip accents).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

# Header-row keywords. Row 1 counts as a header when its first cell looks like
# "TÍTULO" and a later cell looks like a known column (REQ-IMP-1).
TITULO_KEYWORDS = frozenset({"titulo", "título"})
COLUMN_KEYWORDS = frozenset(
    {"autor", "editorial", "precio", "precios", "stock", "genero", "género"}
)

# Exact category names seeded at startup (REQ-CAT-2). Shared with the
# categories router so the importer and the seed stay in sync. Ensayo, Teatro
# and Biografía are appended before OPORTUNIDADES so the existing ordering is
# preserved.
DEFAULT_CATEGORIES = [
    "Novela",
    "Cuentos",
    "No Ficción",
    "Poesía",
    "Infantil y Juvenil",
    "Ensayo",
    "Teatro",
    "Biografía",
    "OPORTUNIDADES",
]

# Source-sheet name (normalized) -> canonical seeded category name. NOVELAS is
# an alias of the Novela category (REQ-IMP-2: sheet -> category map).
SHEET_CATEGORY_ALIASES = {
    "no ficcion": "No Ficción",
    "cuentos": "Cuentos",
    "novela": "Novela",
    "novelas": "Novela",
    "infantil y juvenil": "Infantil y Juvenil",
    "poesia": "Poesía",
    "oportunidades": "OPORTUNIDADES",
}

# Sheet names (normalized) that are skipped at parse time. "Cuentas" is an
# accounts sheet, not a catalog sheet, so it must not produce rows or errors.
SKIP_SHEETS = {"cuentas"}

# Broadest seeded catch-all applied to genre-driven rows whose genre is empty
# or unmapped (REQ-IMP: per-row category fallback).
GENRE_FALLBACK_CATEGORY = "No Ficción"

# Normalized genre token -> canonical category. Keys are accent/case-insensitive
# (looked up through :func:`_normalize_genre_token`); any token prefixed with
# "autobiograf" resolves to Biografía.
GENRE_CATEGORY_MAP = {
    "novela": "Novela",
    "cuentos": "Cuentos",
    "poesia": "Poesía",
    "ensayo": "Ensayo",
    "teatro": "Teatro",
    "biografia": "Biografía",
    "cronica": "No Ficción",
    "cronicas": "No Ficción",
    "memorias": "Biografía",
    "cartas": "No Ficción",
}


def strip_accents(value: str) -> str:
    """Remove combining diacritics so ``Ó`` and ``O`` compare equal."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_header(value: str) -> str:
    """Normalize a header cell for keyword matching (strip, fold case, accents)."""
    return strip_accents(value.strip()).casefold()


def normalize_sheet_name(value: str) -> str:
    """Stable key for a sheet name: strip, fold case, strip accents, collapse spaces."""
    return " ".join(strip_accents(value.strip()).casefold().split())


def is_header_row(cells: list[str | None]) -> bool:
    """True when ``cells`` look like ``TÍTULO | AUTOR | EDITORIAL | PRECIO(S) | STOCK``."""
    non_empty = [cell for cell in cells if cell]
    if not non_empty:
        return False
    first = normalize_header(non_empty[0])
    rest = [normalize_header(cell) for cell in non_empty[1:]]
    return first in TITULO_KEYWORDS and any(cell in COLUMN_KEYWORDS for cell in rest)


def category_for_sheet(sheet_name: str, available: Iterable[str]) -> str | None:
    """Map a sheet name to a category that actually exists in ``available``.

    Matching is accent/case-insensitive against the canonical seeded names, so
    a renamed category (e.g. ``Oportunidades`` vs ``OPORTUNIDADES``) still maps.
    """
    key = normalize_sheet_name(sheet_name)
    canonical = SHEET_CATEGORY_ALIASES.get(key)
    if canonical is None:
        return None
    canonical_key = normalize_sheet_name(canonical)
    for name in available:
        if normalize_sheet_name(name) == canonical_key:
            return name
    return None


def _normalize_genre_token(value: str) -> str:
    """Normalize a genre token for map lookup (strip, fold case, accents, collapse spaces)."""
    return " ".join(strip_accents(value.strip()).casefold().split())


def _genre_to_category(token: str) -> str | None:
    """Map a single normalized genre token to a canonical category name."""
    key = _normalize_genre_token(token)
    if key.startswith("autobiograf"):
        return "Biografía"
    return GENRE_CATEGORY_MAP.get(key)


def category_for_genre(genre: str | None, available: Iterable[str]) -> str | None:
    """Map a genre string to a canonical category present in ``available``.

    Combo genres split on ``/``, ``,``, ``;`` and the standalone word `` y ``
    and return the FIRST token mapping to an available category. Empty or
    unmapped genres return ``None`` (the caller applies the fallback).
    """
    if not genre:
        return None
    available_keys = {normalize_sheet_name(name) for name in available}
    tokens = re.split(r"[/,;]|\s+y\s+", genre)
    for token in tokens:
        canonical = _genre_to_category(token)
        if canonical is None:
            continue
        if normalize_sheet_name(canonical) in available_keys:
            return canonical
    return None


def has_genre_column(cells: list[str | None]) -> bool:
    """True when any header cell normalizes to ``genero`` (genre layout)."""
    return any(normalize_header(cell) == "genero" for cell in cells if cell)


def observaciones_column_index(cells: list[str | None]) -> int | None:
    """Index of the first header cell matching ``/observ/i``, else ``None``.

    The catalog (and sales) sheets expose an "Observaciones"/"OBSERVACIONES"
    column whose position varies by layout; matching is accent/case-insensitive
    so the column is found wherever it lands.
    """
    for index, cell in enumerate(cells):
        if cell is not None and "observ" in normalize_header(cell):
            return index
    return None
