"""Editorial-scoped bulk update endpoints: preview + apply (admin only).

``POST /api/editorial-bulk-update/preview`` and ``/apply`` follow the design's
review-before-commit flow (REQ-BULK-2). ``POST /api/books/bulk-update`` is the
direct apply convenience the user story requested ("actualizar según la
distribuidora o la editorial"): stock_add, stock_set, price_set, price_percent.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import User
from ..schemas.editorial import (
    BulkApplyResponse,
    BulkPreviewResponse,
    BulkUpdateRequest,
)
from ..security.deps import require_admin
from ..security.limiter import limiter
from ..services.editorial_service import BulkUpdateError, apply_bulk, preview_bulk

router = APIRouter(prefix="/api", tags=["editorial-bulk"])

_settings = get_settings()


def _apply_body(body: BulkUpdateRequest) -> dict:
    return {
        "editorial": body.editorial,
        "category_id": body.category_id,
        "action": body.action,
        "amount": body.amount,
    }


@router.post("/editorial-bulk-update/preview", response_model=BulkPreviewResponse)
@limiter.limit(_settings.rate_limit_api)
async def bulk_preview(
    request: Request,
    body: BulkUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> BulkPreviewResponse:
    """Show the filtered diff (old -> new per book) without writing."""
    try:
        rows = await preview_bulk(session, **_apply_body(body))
    except BulkUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return BulkPreviewResponse(
        editorial=body.editorial,
        category_id=body.category_id,
        action=body.action,
        amount=body.amount,
        affected=len(rows),
        rows=rows,
    )


@router.post("/editorial-bulk-update/apply", response_model=BulkApplyResponse)
@limiter.limit(_settings.rate_limit_api)
async def bulk_apply(
    request: Request,
    body: BulkUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> BulkApplyResponse:
    """Apply the filtered operation transactionally (all matching books or none)."""
    try:
        result = await apply_bulk(session, admin=admin, **_apply_body(body))
    except BulkUpdateError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return BulkApplyResponse(
        editorial=body.editorial,
        category_id=body.category_id,
        action=body.action,
        amount=body.amount,
        affected=result["affected"],
    )


@router.post("/books/bulk-update", response_model=BulkApplyResponse)
@limiter.limit(_settings.rate_limit_api)
async def bulk_update_books(
    request: Request,
    body: BulkUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> BulkApplyResponse:
    """Direct apply convenience at ``/api/books/bulk-update`` (same semantics)."""
    try:
        result = await apply_bulk(session, admin=admin, **_apply_body(body))
    except BulkUpdateError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return BulkApplyResponse(
        editorial=body.editorial,
        category_id=body.category_id,
        action=body.action,
        amount=body.amount,
        affected=result["affected"],
    )