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
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import Book, Category, Sale, SaleItem, User
from ..schemas.reports import (
    DaySummary,
    SalesGroupSummary,
    SalesReport,
)
from ..security.deps import require_user
from ..security.limiter import limiter
from ..services.stock import STOCK_IN_STOCK, STOCK_LOW, STOCK_OUT

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