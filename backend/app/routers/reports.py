"""Sales, inventory, category, and editorial reports (REQ-REP-1).

Tables-first JSON summaries consumed by the frontend Reports page and the
dashboard. All endpoints require ``require_user`` and are rate-limited with
the standard API limit. Aggregations stay dialect-portable (no PostgreSQL-only
functions) so the same queries run on SQLite (tests) and asyncpg (prod).
"""

from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import Book, Category, Sale, SaleItem, User
from ..schemas.reports import (
    CategoryMetric,
    DaySummary,
    EditorialMetric,
    InventoryReport,
    SalesGroupSummary,
    SalesReport,
    TopSellerRead,
)
from ..security.deps import require_user
from ..security.limiter import limiter
from ..services.stock import STOCK_IN_STOCK, STOCK_OUT

router = APIRouter(prefix="/api/reports", tags=["reports"])

_settings = get_settings()

GROUP_BY_VALUES = {"category", "editorial"}


def _money(value) -> Decimal:
    """Coerce an aggregation result to a 2-decimal Decimal."""
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _period_filters(start_date: date | None, end_date: date | None) -> list:
    """Build the ``Sale.date`` range conditions (same convention as ``sales.py``)."""
    filters = []
    if start_date is not None:
        filters.append(Sale.date >= datetime.combine(start_date, time.min))
    if end_date is not None:
        filters.append(Sale.date <= datetime.combine(end_date, time.max))
    return filters


async def _grouped_summary(
    session: AsyncSession, group_by: str | None, filters: list
) -> list[SalesGroupSummary]:
    """Group revenue/units/sales by category or editorial (sale_items→book join)."""
    if group_by == "category":
        query = (
            select(
                Category.name.label("key"),
                func.count(func.distinct(SaleItem.sale_id)),
                func.coalesce(func.sum(SaleItem.quantity), 0),
                func.coalesce(func.sum(SaleItem.subtotal), 0),
            )
            .join(Book, Book.id == SaleItem.book_id)
            .join(Category, Category.id == Book.category_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(*filters)
            .group_by(Category.id, Category.name)
            .order_by(
                func.coalesce(func.sum(SaleItem.subtotal), 0).desc(), Category.name
            )
        )
    elif group_by == "editorial":
        query = (
            select(
                Book.editorial.label("key"),
                func.count(func.distinct(SaleItem.sale_id)),
                func.coalesce(func.sum(SaleItem.quantity), 0),
                func.coalesce(func.sum(SaleItem.subtotal), 0),
            )
            .join(Book, Book.id == SaleItem.book_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(*filters)
            .group_by(Book.editorial)
            .order_by(
                func.coalesce(func.sum(SaleItem.subtotal), 0).desc(), Book.editorial
            )
        )
    else:
        return []

    rows = (await session.execute(query)).all()
    return [
        SalesGroupSummary(
            key=row[0], sales=row[1], units=row[2], revenue=_money(row[3])
        )
        for row in rows
    ]


@router.get("/sales", response_model=SalesReport)
@limiter.limit(_settings.rate_limit_api)
async def sales_report(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    start_date: date | None = None,
    end_date: date | None = None,
    group_by: str | None = None,
) -> SalesReport:
    """Sales summary for a period: totals, by-day breakdown, optional grouping."""
    if group_by is not None and group_by not in GROUP_BY_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by must be 'category', 'editorial', or omitted",
        )

    filters = _period_filters(start_date, end_date)

    total_sales, total_revenue = (
        await session.execute(
            select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0)).where(
                *filters
            )
        )
    ).one()

    day_expr = func.date(Sale.date).label("day")
    day_rows = (
        await session.execute(
            select(
                day_expr,
                func.count(Sale.id),
                func.coalesce(func.sum(Sale.total), 0),
            )
            .where(*filters)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    by_day = [
        DaySummary(date=row[0], sales=row[1], revenue=_money(row[2]))
        for row in day_rows
    ]

    return SalesReport(
        start_date=start_date,
        end_date=end_date,
        total_sales=total_sales,
        total_revenue=_money(total_revenue),
        by_day=by_day,
        group_by=group_by,
        groups=await _grouped_summary(session, group_by, filters),
    )


@router.get("/top-sellers", response_model=list[TopSellerRead])
@limiter.limit(_settings.rate_limit_api)
async def top_sellers(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    limit: int = Query(10, ge=1, le=100),
) -> list[TopSellerRead]:
    """Top N books by quantity sold, with revenue from the price snapshot."""
    query = (
        select(
            SaleItem.book_id,
            Book.title,
            Book.author,
            Book.editorial,
            func.coalesce(func.sum(SaleItem.quantity), 0).label("quantity_sold"),
            func.coalesce(func.sum(SaleItem.subtotal), 0).label("revenue"),
        )
        .join(Book, Book.id == SaleItem.book_id)
        .group_by(SaleItem.book_id, Book.title, Book.author, Book.editorial)
        .order_by(
            func.sum(SaleItem.quantity).desc(),
            func.sum(SaleItem.subtotal).desc(),
            Book.title,
        )
        .limit(limit)
    )
    rows = (await session.execute(query)).all()
    return [
        TopSellerRead(
            book_id=row[0],
            title=row[1],
            author=row[2],
            editorial=row[3],
            quantity_sold=row[4],
            revenue=_money(row[5]),
        )
        for row in rows
    ]


@router.get("/inventory", response_model=InventoryReport)
@limiter.limit(_settings.rate_limit_api)
async def inventory_report(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    category_id: int | None = None,
) -> InventoryReport:
    """Stock value and per-status counts for active books (optionally by category).

    Only the binary states are reported: In Stock (``stock > 0``) and
    Out of Stock (``stock == 0``). The former low-stock bucket is omitted.
    """
    threshold = _settings.low_stock_threshold
    in_condition = Book.stock > 0
    out_condition = Book.stock == 0

    query = select(
        func.count(Book.id),
        func.coalesce(func.sum(Book.stock), 0),
        func.coalesce(func.sum(Book.price * Book.stock), 0),
        func.coalesce(func.sum(case((in_condition, 1), else_=0)), 0),
        func.coalesce(func.sum(case((out_condition, 1), else_=0)), 0),
    ).where(Book.is_active.is_(True))
    if category_id is not None:
        query = query.where(Book.category_id == category_id)

    total_books, total_units, stock_value, in_stock, out = (
        await session.execute(query)
    ).one()
    return InventoryReport(
        total_books=total_books,
        total_units=total_units,
        stock_value=_money(stock_value),
        status_counts={
            STOCK_IN_STOCK: in_stock,
            STOCK_OUT: out,
        },
        threshold=threshold,
        category_id=category_id,
    )


@router.get("/category", response_model=list[CategoryMetric])
@limiter.limit(_settings.rate_limit_api)
async def category_report(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> list[CategoryMetric]:
    """Revenue and units by category (categories with no sales show zeros)."""
    query = (
        select(
            Category.id,
            Category.name,
            func.count(func.distinct(SaleItem.sale_id)),
            func.coalesce(func.sum(SaleItem.quantity), 0),
            func.coalesce(func.sum(SaleItem.subtotal), 0),
        )
        .outerjoin(Book, Book.category_id == Category.id)
        .outerjoin(SaleItem, SaleItem.book_id == Book.id)
        .group_by(Category.id, Category.name)
        .order_by(
            func.coalesce(func.sum(SaleItem.subtotal), 0).desc(), Category.name
        )
    )
    rows = (await session.execute(query)).all()
    return [
        CategoryMetric(
            category_id=row[0],
            category=row[1],
            sales=row[2],
            units=row[3],
            revenue=_money(row[4]),
        )
        for row in rows
    ]


@router.get("/editorial", response_model=list[EditorialMetric])
@limiter.limit(_settings.rate_limit_api)
async def editorial_report(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> list[EditorialMetric]:
    """Revenue and units by editorial (editorials with no sales show zeros)."""
    query = (
        select(
            Book.editorial,
            func.count(func.distinct(SaleItem.sale_id)),
            func.coalesce(func.sum(SaleItem.quantity), 0),
            func.coalesce(func.sum(SaleItem.subtotal), 0),
        )
        .select_from(Book)
        .outerjoin(SaleItem, SaleItem.book_id == Book.id)
        .group_by(Book.editorial)
        .order_by(
            func.coalesce(func.sum(SaleItem.subtotal), 0).desc(), Book.editorial
        )
    )
    rows = (await session.execute(query)).all()
    return [
        EditorialMetric(
            editorial=row[0], sales=row[1], units=row[2], revenue=_money(row[3])
        )
        for row in rows
    ]