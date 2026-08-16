"""Excel header and sheet-name normalization for the catalog importer.

Display strings keep their original case; matching uses the normalized form
(strip whitespace, fold case, strip accents).
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

# Header-row keywords. Row 1 counts as a header when its first cell looks like
# "TÍTULO" and a later cell looks like a known column (REQ-IMP-1).
TITULO_KEYWORDS = frozenset({"titulo", "título"})
COLUMN_KEYWORDS = frozenset(
    {"autor", "editorial", "precio", "precios", "stock", "genero", "género"}
)

# Exact category names seeded at startup (REQ-CAT-2). Shared with the
# categories router so the importer and the seed stay in sync.
DEFAULT_CATEGORIES = [
    "Novela",
    "Cuentos",
    "No Ficción",
    "Poesía",
    "Infantil y Juvenil",
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