"""Dashboard aggregate metrics for the SPA home view (REQ-REP-1).

One endpoint aggregates the headline numbers the home screen needs: inventory
totals and value, today's sales, the low-stock watchlist, out-of-stock count,
and the ten most recent sales. All aggregations are dialect-portable.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.timezone import ba_today, bound_for_dialect, day_bounds_utc
from ..db import get_session
from ..models import Book, Sale, SaleItem, User
from ..schemas.reports import DashboardRead, LowStockItem, RecentSaleRead, TodaySales
from ..security.deps import require_user
from ..security.limiter import limiter
from ..services.stock import compute_stock_status

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_settings = get_settings()

_RECENT_SALES_LIMIT = 10


def _money(value) -> Decimal:
    """Coerce an aggregation result to a 2-decimal Decimal."""
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("", response_model=DashboardRead)
@limiter.limit(_settings.rate_limit_api)
async def dashboard(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    low_stock_limit: int = Query(10, ge=1, le=50),
) -> DashboardRead:
    threshold = _settings.low_stock_threshold
    dialect = session.get_bind().dialect.name
    day_start, day_end = day_bounds_utc(ba_today())
    day_start = bound_for_dialect(day_start, dialect_name=dialect)
    day_end = bound_for_dialect(day_end, dialect_name=dialect)

    total_books, total_units, stock_value, out_of_stock = (
        await session.execute(
            select(
                func.count(Book.id),
                func.coalesce(func.sum(Book.stock), 0),
                func.coalesce(func.sum(Book.price * Book.stock), 0),
                func.coalesce(func.sum(case((Book.stock == 0, 1), else_=0)), 0),
            ).where(Book.is_active.is_(True))
        )
    ).one()

    today_count, today_revenue = (
        await session.execute(
            select(
                func.count(Sale.id),
                func.coalesce(func.sum(Sale.total), 0),
            ).where(Sale.date >= day_start, Sale.date <= day_end)
        )
    ).one()

    low_books = (
        await session.execute(
            select(Book)
            .where(
                Book.is_active.is_(True),
                Book.stock == 0,
            )
            .order_by(Book.stock, Book.title)
            .limit(low_stock_limit)
        )
    ).scalars().all()

    item_count = (
        select(SaleItem.sale_id, func.count(SaleItem.id).label("count"))
        .group_by(SaleItem.sale_id)
        .subquery()
    )
    recent_rows = (
        await session.execute(
            select(Sale, item_count.c.count.label("item_count"))
            .outerjoin(item_count, item_count.c.sale_id == Sale.id)
            .order_by(Sale.date.desc(), Sale.id.desc())
            .limit(_RECENT_SALES_LIMIT)
        )
    ).all()

    return DashboardRead(
        total_books=total_books,
        total_units=total_units,
        stock_value=_money(stock_value),
        today_sales=TodaySales(count=today_count, revenue=_money(today_revenue)),
        low_stock=[
            LowStockItem(
                book_id=book.id,
                title=book.title,
                author=book.author,
                editorial=book.editorial,
                stock=book.stock,
                stock_status=compute_stock_status(book.stock, threshold),
            )
            for book in low_books
        ],
        out_of_stock_count=out_of_stock,
        recent_sales=[
            RecentSaleRead(
                id=sale.id,
                sale_number=sale.sale_number,
                date=sale.date,
                total=sale.total,
                seller=sale.seller,
                payment_method=sale.payment_method,
                customer_name=sale.customer_name,
                created_by=sale.created_by,
                item_count=count if count is not None else 0,
            )
            for sale, count in recent_rows
        ],
    )