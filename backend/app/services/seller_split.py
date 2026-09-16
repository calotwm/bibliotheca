"""Automatic per-seller percentage splits derived from a book's ``observaciones``.

The split reflects who acquired the book (free-text ``observaciones`` like
"Juli", "Cande", "Juli y Cande"; blank/None means Juli). The resulting
``(juli_share, cande_share)`` percentages are STORED on each sale at creation
time and reused by the per-seller earnings report. Legacy sales whose share
columns are still NULL derive the split from the first item's book at query
time.

The three-bucket rule lives in ``seller_bucket`` and is shared with the
``seller`` filter on ``GET /api/books`` via ``seller_filter_condition`` so the
money split and the UI filter can never drift.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from sqlalchemy import and_, func
from sqlalchemy.sql.elements import ColumnElement

from ..models import Book

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..models import Sale

SellerBucket = Literal["Juli", "Cande", "Juli y Cande"]

_TWO_PLACES = Decimal("0.01")

_BUCKET_SHARES: dict[SellerBucket, tuple[Decimal, Decimal]] = {
    "Juli y Cande": (Decimal("50"), Decimal("50")),
    "Cande": (Decimal("0"), Decimal("100")),
    "Juli": (Decimal("85"), Decimal("15")),
}


def seller_bucket(observaciones: str | None) -> SellerBucket:
    """Classify ``observaciones`` into one of three buckets.

    - contains both "cande" and "juli" -> "Juli y Cande"
    - contains only "cande"            -> "Cande"
    - everything else (Juli-only, blank, None, or no name) -> "Juli"

    Blank/None defaults to "Juli" by business rule ("las que no digan nada son
    adquiridas por Juli").
    """
    text = (observaciones or "").lower()
    has_cande = "cande" in text
    has_juli = "juli" in text
    if has_cande and has_juli:
        return "Juli y Cande"
    if has_cande:
        return "Cande"
    return "Juli"


def seller_filter_condition(bucket: SellerBucket) -> ColumnElement[bool]:
    """Return a SQLAlchemy boolean expression matching ``bucket``.

    Uses ``func.coalesce(observaciones, "")`` so NULL rows are grouped with the
    empty string and land in the "Juli" bucket on both PostgreSQL and SQLite
    — a naive ``NOT LIKE '%cande%'`` evaluates to NULL for NULL input and
    silently drops blank books from the Juli bucket.
    """
    text = func.lower(func.coalesce(Book.observaciones, ""))
    has_cande: ColumnElement[bool] = text.like("%cande%")
    has_juli: ColumnElement[bool] = text.like("%juli%")
    if bucket == "Juli":
        return ~has_cande
    if bucket == "Cande":
        return and_(has_cande, ~has_juli)
    if bucket == "Juli y Cande":
        return and_(has_cande, has_juli)
    raise ValueError(f"Invalid seller bucket: {bucket!r}")


def compute_shares(observaciones: str | None) -> tuple[Decimal, Decimal]:
    """Return ``(juli_share, cande_share)`` percentages for ``observaciones``.

    - "Juli y Cande" (both names present)        -> 50 / 50
    - "Cande"      (only Cande)                   -> 0 / 100
    - "Juli"       (Juli only, blank, None, etc.) -> 85 / 15

    Derived from ``seller_bucket`` so the filter and the share split share one
    source of truth. Output Decimal values are quantized to two places and
    stay byte-identical with the pre-shared implementation.
    """
    juli_share, cande_share = _BUCKET_SHARES[seller_bucket(observaciones)]
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
