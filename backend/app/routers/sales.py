"""Sales POS endpoints: create, list, and detail."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sqlalchemy import text

from ..config import get_settings
from ..core.timezone import period_filters
from ..db import get_session
from ..models import Sale, SaleItem, User
from ..schemas.sale import SaleCreate, SaleItemRead, SaleListRead, SaleRead
from ..security.deps import require_admin, require_user
from ..security.limiter import limiter
from ..services import pdf_service
from ..services.sale_service import (
    BookUnavailableError,
    OversellError,
    create_sale,
)
from ..services.numbering import NUMBERING_KEY, PG_SEQUENCE

router = APIRouter(prefix="/api/sales", tags=["sales"])

_settings = get_settings()


def _item_to_read(item: SaleItem) -> SaleItemRead:
    return SaleItemRead(
        id=item.id,
        book_id=item.book_id,
        book_title=item.book.title if item.book is not None else None,
        quantity=item.quantity,
        unit_price=item.unit_price,
        subtotal=item.subtotal,
    )


def _sale_to_read(sale: Sale) -> SaleRead:
    return SaleRead(
        id=sale.id,
        sale_number=sale.sale_number,
        date=sale.date,
        total=sale.total,
        seller=sale.seller,
        payment_method=sale.payment_method,
        customer_name=sale.customer_name,
        customer_cuit=sale.customer_cuit,
        invoice_pdf_path=sale.invoice_pdf_path,
        created_by=sale.created_by,
        created_at=sale.created_at,
        items=[_item_to_read(item) for item in sale.items],
    )


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(_settings.rate_limit_api)
async def create_sale_endpoint(
    request: Request,
    body: SaleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> SaleRead:
    try:
        sale = await create_sale(
            session,
            cashier=user,
            items=body.items,
            seller=body.seller,
            payment_method=body.payment_method,
            customer_name=body.customer_name,
            customer_cuit=body.customer_cuit,
        )
    except OversellError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    except BookUnavailableError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    await session.commit()

    sale = (
        await session.execute(
            select(Sale)
            .options(selectinload(Sale.items).selectinload(SaleItem.book))
            .where(Sale.id == sale.id)
        )
    ).scalar_one()
    return _sale_to_read(sale)


@router.get("", response_model=list[SaleListRead])
@limiter.limit(_settings.rate_limit_api)
async def list_sales(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[SaleListRead]:
    item_count = (
        select(SaleItem.sale_id, func.count(SaleItem.id).label("count"))
        .group_by(SaleItem.sale_id)
        .subquery()
    )
    query = (
        select(Sale, item_count.c.count.label("item_count"))
        .outerjoin(item_count, item_count.c.sale_id == Sale.id)
        .order_by(Sale.date.desc(), Sale.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if start_date is not None or end_date is not None:
        query = query.where(
            *period_filters(
                Sale.date,
                start_date,
                end_date,
                dialect_name=session.get_bind().dialect.name,
            )
        )

    rows = (await session.execute(query)).all()
    return [
        SaleListRead(
            id=sale.id,
            sale_number=sale.sale_number,
            date=sale.date,
            total=sale.total,
            seller=sale.seller,
            payment_method=sale.payment_method,
            customer_name=sale.customer_name,
            customer_cuit=sale.customer_cuit,
            created_by=sale.created_by,
            created_at=sale.created_at,
            item_count=count if count is not None else 0,
        )
        for sale, count in rows
    ]


@router.get("/{sale_id}", response_model=SaleRead)
@limiter.limit(_settings.rate_limit_api)
async def get_sale(
    request: Request,
    sale_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> SaleRead:
    sale = (
        await session.execute(
            select(Sale)
            .options(selectinload(Sale.items).selectinload(SaleItem.book))
            .where(Sale.id == sale_id)
        )
    ).scalar_one_or_none()
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found"
        )
    return _sale_to_read(sale)


@router.get("/{sale_id}/invoice.pdf")
@limiter.limit(_settings.rate_limit_api)
async def get_sale_invoice(
    request: Request,
    sale_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> Response:
    """Generate (or reprint) the sale's non-fiscal PDF invoice (REQ-PDF-1/2)."""
    sale = (
        await session.execute(
            select(Sale)
            .options(
                selectinload(Sale.items).selectinload(SaleItem.book),
                selectinload(Sale.user),
            )
            .where(Sale.id == sale_id)
        )
    ).scalar_one_or_none()
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found"
        )

    pdf_bytes = pdf_service.build_invoice_pdf(sale)
    storage_path = pdf_service.persist_invoice(sale.sale_number, pdf_bytes)
    if sale.invoice_pdf_path != str(storage_path):
        sale.invoice_pdf_path = str(storage_path)
        await session.commit()

    filename = pdf_service.invoice_filename(sale.sale_number)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/reset")
@limiter.limit(_settings.rate_limit_api)
async def reset_sales(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
    confirm: bool = False,
) -> dict:
    """Destructive admin-only reset: delete all sales and reset invoice numbering.

    Requires ``?confirm=true`` as an explicit guard (the operation is
    irreversible). Sale rows do NOT restore book stock (by design). Runs in a
    single transaction.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset requires ?confirm=true",
        )

    sale_items_deleted = (
        await session.execute(select(func.count(SaleItem.id)))
    ).scalar_one()
    sales_deleted = (await session.execute(select(func.count(Sale.id)))).scalar_one()
    await session.execute(text("DELETE FROM sale_items"))
    await session.execute(text("DELETE FROM sales"))

    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        await session.execute(
            text(f"ALTER SEQUENCE {PG_SEQUENCE} RESTART WITH 1")
        )
    else:
        await session.execute(
            text("UPDATE numbering SET value = 0 WHERE name = :name"),
            {"name": NUMBERING_KEY},
        )

    await session.commit()

    return {
        "deleted_sale_items": sale_items_deleted,
        "deleted_sales": sales_deleted,
        "invoice_numbering": "reset",
    }