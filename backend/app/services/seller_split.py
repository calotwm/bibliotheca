"""Automatic per-seller percentage splits derived from a book's ``observaciones``.

The split reflects who acquired the book (free-text ``observaciones`` like
"Juli", "Cande", "Juli y Cande"; blank/None means Juli). The resulting
``(juli_share, cande_share)`` percentages are STORED on each sale at creation
time and reused by the per-seller earnings report. Legacy sales whose share
columns are still NULL derive the split from the first item's book at query
time.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..models import Sale

_TWO_PLACES = Decimal("0.01")


def compute_shares(observaciones: str | None) -> tuple[Decimal, Decimal]:
    """Return ``(juli_share, cande_share)`` percentages for ``observaciones``.

    - both names present (e.g. "Juli y Cande") -> 50 / 50
    - only Cande                                 -> 0 / 100
    - otherwise (Juli only, blank, None, or no name found) -> 85 / 15
    """
    text = (observaciones or "").lower()
    has_cande = "cande" in text
    has_juli = "juli" in text
    if has_cande and has_juli:
        juli_share, cande_share = Decimal("50"), Decimal("50")
    elif has_cande:
        juli_share, cande_share = Decimal("0"), Decimal("100")
    else:
        juli_share, cande_share = Decimal("85"), Decimal("15")
    return (
        juli_share.quantize(_TWO_PLACES),
        cande_share.quantize(_TWO_PLACES),
    )


def sale_shares(sale: Sale) -> tuple[Decimal, Decimal]:
    """Resolve a sale's split.

    Prefer the stored share columns (new sales always store them). Legacy rows
    with NULL shares derive from the first item's book ``observaciones``; a
    sale with no items (or a missing book) falls back to ``compute_shares``
    of None, which yields the 85/15 "Juli" default.
    """
    if sale.juli_share is not None and sale.cande_share is not None:
        return sale.juli_share, sale.cande_share
    if sale.items:
        first_item = min(sale.items, key=lambda item: item.id)
        book = first_item.book
        observaciones = book.observaciones if book is not None else None
    else:
        observaciones = None
    return compute_shares(observaciones)
