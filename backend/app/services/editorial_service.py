"""Editorial-scoped bulk update service (REQ-BULK-1/2).

Filtered operations apply to every active book of a given editorial (optionally
scoped to one category): ``stock_add``, ``stock_set``, ``price_set`` and
``price_percent`` (positive or negative percentage). Preview computes the diff
without writing; apply mutates every matching book in one transaction.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Book, User
from ..schemas.editorial import BulkPreviewRow
from .audit import log_audit

STOCK_ACTIONS = frozenset({"stock_add", "stock_set"})
PRICE_ACTIONS = frozenset({"price_set", "price_percent"})


class BulkUpdateError(Exception):
    """The requested bulk operation is invalid or would break a book row."""


def _validate_amount(action: str, amount: Decimal) -> Decimal | int:
    if action in STOCK_ACTIONS:
        if amount != amount.to_integral_value():
            raise BulkUpdateError("Stock amounts must be whole numbers")
        return int(amount)
    return amount


def _apply_action(current: int | Decimal, action: str, amount: Decimal | int):
    """Compute the resulting value for a book (no side effects)."""
    if action == "stock_add":
        return int(current) + int(amount)
    if action == "stock_set":
        return int(amount)
    if action == "price_set":
        return Decimal(amount).quantize(Decimal("0.01"))
    if action == "price_percent":
        factor = (Decimal("100") + Decimal(amount)) / Decimal("100")
        return (Decimal(current) * factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    raise BulkUpdateError(f"Unknown action {action!r}")


def _field_for(action: str) -> str:
    return "price" if action in PRICE_ACTIONS else "stock"


async def _matching_books(
    session: AsyncSession,
    *,
    editorial: str | None,
    author: str | None,
    category_id: int | None,
) -> list[Book]:
    query = select(Book).where(Book.is_active.is_(True))
    if editorial:
        query = query.where(
            func.lower(Book.editorial) == editorial.strip().lower()
        )
    if author:
        query = query.where(
            func.lower(Book.author).like(f"%{author.strip().lower()}%")
        )
    if category_id is not None:
        query = query.where(Book.category_id == category_id)
    query = query.order_by(Book.title)
    return list((await session.execute(query)).scalars().all())


async def preview_bulk(
    session: AsyncSession,
    *,
    editorial: str | None,
    author: str | None = None,
    category_id: int | None,
    action: str,
    amount: Decimal,
) -> list[BulkPreviewRow]:
    """Return the affected books with computed old -> new values (no writes)."""
    coerced = _validate_amount(action, amount)
    books = await _matching_books(
        session, editorial=editorial, author=author, category_id=category_id
    )
    field = _field_for(action)
    rows: list[BulkPreviewRow] = []
    for book in books:
        old_value = getattr(book, field)
        new_value = _apply_action(old_value, action, coerced)
        if Decimal(new_value) < 0:
            raise BulkUpdateError(
                f"{book.title}: {action} would produce a negative {field}"
            )
        rows.append(
            BulkPreviewRow(
                id=book.id,
                title=book.title,
                editorial=book.editorial,
                field=field,
                old_value=str(old_value),
                new_value=str(new_value),
            )
        )
    return rows


async def apply_bulk(
    session: AsyncSession,
    *,
    admin: User,
    editorial: str | None,
    author: str | None = None,
    category_id: int | None,
    action: str,
    amount: Decimal,
) -> dict:
    """Apply the operation to every matching book in one transaction (caller commits)."""
    coerced = _validate_amount(action, amount)
    books = await _matching_books(
        session, editorial=editorial, author=author, category_id=category_id
    )
    field = _field_for(action)
    for book in books:
        old_value = getattr(book, field)
        new_value = _apply_action(old_value, action, coerced)
        if Decimal(new_value) < 0:
            raise BulkUpdateError(
                f"{book.title}: {action} would produce a negative {field}"
            )
        setattr(book, field, new_value)

    affected = len(books)
    await log_audit(
        session,
        user_id=admin.id,
        entity_type="book",
        entity_id=None,
        action="bulk_update",
        changes={
            "editorial": editorial,
            "author": author,
            "category_id": category_id,
            "action": action,
            "amount": str(amount),
            "affected": affected,
        },
    )
    return {"affected": affected}