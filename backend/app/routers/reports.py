"""Sales, inventory, category, and editorial reports (REQ-REP-1).

Tables-first JSON summaries consumed by the frontend Reports page and the
dashboard. All endpoints require ``require_user`` and are rate-limited with
the standard API limit. Aggregations stay dialect-portable (no PostgreSQL-only
functions) so the same queries run on SQLite (tests) and asyncpg (prod).
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.timezone import ba_day_expr, ba_local_date, ba_today, period_filters
from ..db import get_session
from ..models import Book, Category, Sale, SaleItem, User
from ..schemas.reports import (
    CategoryMetric,
    DaySummary,
    EditorialMetric,
    InventoryReport,
    SalesDetailRow,
    SalesGroupSummary,
    SalesReport,
    SellerReport,
    SellerSummary,
    TopSellerRead,
)
from ..security.deps import require_user
from ..security.limiter import limiter
from ..services.stock import STOCK_IN_STOCK, STOCK_OUT

router = APIRouter(prefix="/api/reports", tags=["reports"])

_settings = get_settings()

GROUP_BY_VALUES = {"category", "editorial"}
SHARED_SALES_SELLER = "Cande y Julieta"


def _money(value) -> Decimal:
    """Coerce an aggregation result to a 2-decimal Decimal."""
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

    filters = period_filters(
        Sale.date, start_date, end_date, dialect_name=session.get_bind().dialect.name
    )

    total_sales, total_revenue = (
        await session.execute(
            select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0)).where(
                *filters
            )
        )
    ).one()

    day_expr = ba_day_expr(
        Sale.date, dialect_name=session.get_bind().dialect.name
    ).label("day")
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


@router.get("/sales-detail", response_model=list[SalesDetailRow])
@limiter.limit(_settings.rate_limit_api)
async def sales_detail(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[SalesDetailRow]:
    """Per-item sales ledger (one row per sold item) for a Buenos-Aires range.

    Includes the book's CURRENT stock, category, and the seller as
    ``seller`` (null means "Sin vendedor"). Ordered by sale datetime desc.
    """
    filters = period_filters(
        Sale.date, start_date, end_date, dialect_name=session.get_bind().dialect.name
    )
    rows = (
        await session.execute(
            select(
                Sale.id,
                Sale.sale_number,
                Sale.date,
                Sale.payment_method,
                Sale.seller,
                Book.title,
                Book.author,
                Book.editorial,
                Category.name,
                SaleItem.unit_price,
                SaleItem.quantity,
                SaleItem.subtotal,
                Book.stock,
                Sale.observaciones,
            )
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .join(Book, Book.id == SaleItem.book_id)
            .join(Category, Category.id == Book.category_id)
            .where(*filters)
            .order_by(Sale.date.desc(), Sale.id.desc(), SaleItem.id.asc())
        )
    ).all()
    return [
        SalesDetailRow(
            sale_id=row[0],
            sale_number=row[1],
            date=ba_local_date(row[2]),
            payment_method=row[3],
            seller=row[4],
            title=row[5],
            author=row[6],
            editorial=row[7],
            category=row[8],
            unit_price=row[9],
            quantity=row[10],
            subtotal=row[11],
            stock=row[12],
            observaciones=row[13],
        )
        for row in rows
    ]


@router.get("/sellers", response_model=SellerReport)
@limiter.limit(_settings.rate_limit_api)
async def sellers_report(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    start_date: date | None = None,
    end_date: date | None = None,
) -> SellerReport:
    """Per-seller monthly stats with the shared-sale 50/50 split.

    Shared sales ("Cande y Julieta") count once for each seller and their
    revenue is split in half between both. Sales without a seller are ignored.
    Default period: the current Buenos-Aires month.
    """
    if start_date is None and end_date is None:
        today = ba_today()
        start_date = today.replace(day=1)
        end_date = today

    filters = period_filters(
        Sale.date, start_date, end_date, dialect_name=session.get_bind().dialect.name
    )
    is_shared = Sale.seller == SHARED_SALES_SELLER
    revenue_expr = func.coalesce(
        func.sum(case((is_shared, Sale.total * Decimal("0.5")), else_=Sale.total)), 0
    ).label("total_revenue")
    query = (
        select(
            Sale.seller,
            func.count(Sale.id),
            revenue_expr,
            func.coalesce(func.sum(case((is_shared, 1), else_=0)), 0),
            func.coalesce(
                func.sum(case((is_shared, Sale.total * Decimal("0.5")), else_=0)), 0
            ),
        )
        .where(Sale.seller.is_not(None), *filters)
        .group_by(Sale.seller)
        .order_by(revenue_expr.desc(), Sale.seller)
    )
    rows = (await session.execute(query)).all()
    # Shared sales are aggregated under "Cande y Julieta"; expand them into one
    # row per seller so the 50/50 split keeps both names on the ledger.
    merged: dict[str, dict] = {}
    for seller, count, revenue, shared_count, shared_rev in rows:
        targets = (
            SHARED_SALES_SELLER.split(" y ") if seller == SHARED_SALES_SELLER else (seller,)
        )
        for target in targets:
            entry = merged.setdefault(
                target,
                {
                    "sale_count": 0,
                    "total_revenue": Decimal("0.00"),
                    "shared_sale_count": 0,
                    "shared_revenue": Decimal("0.00"),
                },
            )
            entry["sale_count"] += count
            entry["total_revenue"] += revenue
            entry["shared_sale_count"] += shared_count
            entry["shared_revenue"] += shared_rev

    sellers = [
        SellerSummary(
            seller=target,
            sale_count=entry["sale_count"],
            total_revenue=_money(entry["total_revenue"]),
            shared_sale_count=entry["shared_sale_count"],
            shared_revenue=_money(entry["shared_revenue"]),
        )
        for target, entry in merged.items()
    ]
    sellers.sort(key=lambda summary: (-summary.total_revenue, summary.seller))
    return SellerReport(
        start_date=start_date,
        end_date=end_date,
        sellers=sellers,
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