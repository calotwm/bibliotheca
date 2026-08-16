"""Tests for the data model: creation, round-trip, and constraints."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import AuditLog, Book, Category, Sale, SaleItem, User


async def _make_category(session, name="Novela") -> Category:
    category = Category(name=name)
    session.add(category)
    await session.flush()
    return category


def _make_book(category: Category, **overrides) -> Book:
    defaults = dict(
        title="Rayuela",
        author="Julio Cortázar",
        editorial="Sudamericana",
        category_id=category.id,
        price=Decimal("12.50"),
        stock=3,
    )
    defaults.update(overrides)
    return Book(**defaults)


async def test_book_create_and_roundtrip(session):
    category = await _make_category(session)
    session.add(_make_book(category))
    await session.commit()

    fetched = (
        await session.execute(select(Book).options(selectinload(Book.category)))
    ).scalar_one()
    assert fetched.title == "Rayuela"
    assert fetched.stock == 3
    assert fetched.is_active is True
    assert fetched.category.name == "Novela"


async def test_natural_key_uniqueness(session):
    category = await _make_category(session)
    session.add_all([_make_book(category), _make_book(category)])
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    remaining = (await session.execute(select(Book))).scalars().all()
    assert len(remaining) == 0


async def test_stock_check_constraint(session):
    category = await _make_category(session)
    session.add(_make_book(category, stock=-1))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_sale_and_items_roundtrip(session):
    category = await _make_category(session)
    user = User(username="admin", password_hash="hash", role="admin")
    session.add(user)
    await session.flush()

    book = _make_book(category, price=Decimal("10.00"))
    session.add(book)
    await session.flush()

    sale = Sale(sale_number=1, total=Decimal("20.00"), created_by=user.id)
    sale.items.append(
        SaleItem(
            book_id=book.id,
            quantity=2,
            unit_price=Decimal("10.00"),
            subtotal=Decimal("20.00"),
        )
    )
    session.add(sale)
    await session.commit()

    fetched = (
        await session.execute(select(Sale).options(selectinload(Sale.items)))
    ).scalar_one()
    assert fetched.sale_number == 1
    assert fetched.total == Decimal("20.00")
    assert len(fetched.items) == 1
    assert fetched.items[0].unit_price == Decimal("10.00")


async def test_audit_log_json_roundtrip(session):
    session.add(
        AuditLog(
            entity_type="book",
            entity_id=1,
            action="create",
            changes_json={"title": "Rayuela", "stock": 3},
        )
    )
    await session.commit()

    fetched = (await session.execute(select(AuditLog))).scalar_one()
    assert fetched.changes_json == {"title": "Rayuela", "stock": 3}
