"""Catalog helpers: natural-key normalization, lookup, and upsert."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Book


def normalize_key(value: str) -> str:
    """Normalize a natural-key component for case-insensitive matching."""
    return value.strip().lower()


def natural_key(title: str, author: str, editorial: str) -> tuple[str, str, str]:
    """Return the canonical (case-insensitive) natural key for a book."""
    return (normalize_key(title), normalize_key(author), normalize_key(editorial))


async def find_by_natural_key(
    session: AsyncSession, title: str, author: str, editorial: str
) -> Book | None:
    """Find a book by its case-insensitive (title, author, editorial) key."""
    ntitle, nauthor, neditorial = natural_key(title, author, editorial)
    result = await session.execute(
        select(Book).where(
            func.lower(Book.title) == ntitle,
            func.lower(Book.author) == nauthor,
            func.lower(Book.editorial) == neditorial,
        )
    )
    return result.scalar_one_or_none()


async def upsert_book(
    session: AsyncSession,
    *,
    title: str,
    author: str,
    editorial: str,
    category_id: int,
    price: Decimal,
    stock: int,
    isbn: str | None = None,
    genre: str | None = None,
) -> tuple[Book, bool]:
    """Create-or-update a book by natural key (returns ``(book, created)``).

    On a natural-key match the existing row is updated in place and re-activated
    (REQ-CAT-1: duplicate key → update, not insert).
    """
    existing = await find_by_natural_key(session, title, author, editorial)
    if existing is not None:
        existing.title = title.strip()
        existing.author = author.strip()
        existing.editorial = editorial.strip()
        existing.category_id = category_id
        existing.price = price
        existing.stock = stock
        existing.isbn = isbn
        existing.genre = genre
        existing.is_active = True
        return existing, False

    book = Book(
        title=title.strip(),
        author=author.strip(),
        editorial=editorial.strip(),
        category_id=category_id,
        price=price,
        stock=stock,
        isbn=isbn,
        genre=genre,
    )
    session.add(book)
    await session.flush()
    return book, True
