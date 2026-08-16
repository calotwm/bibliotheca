"""Read-only audit log history (REQ-AUD-2, admin only)."""

from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import AuditLog, User
from ..schemas.audit import AuditLogRead
from ..security.deps import require_admin
from ..security.limiter import limiter

router = APIRouter(prefix="/api/audit", tags=["audit"])

_settings = get_settings()


@router.get("", response_model=list[AuditLogRead])
@limiter.limit(_settings.rate_limit_api)
async def list_audit(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
    entity_type: str | None = None,
    action: str | None = None,
    username: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[AuditLogRead]:
    query = (
        select(AuditLog, User.username)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    if username:
        query = query.where(User.username == username)
    if start_date is not None:
        query = query.where(
            AuditLog.created_at >= datetime.combine(start_date, time.min)
        )
    if end_date is not None:
        query = query.where(
            AuditLog.created_at <= datetime.combine(end_date, time.max)
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(query)).all()
    return [
        AuditLogRead(
            id=log.id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            changes_json=log.changes_json,
            username=username,
            created_at=log.created_at,
        )
        for log, username in rows
    ]