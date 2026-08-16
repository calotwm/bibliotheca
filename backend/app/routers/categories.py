"""Category endpoints and startup seed."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..excel_import.normalizer import DEFAULT_CATEGORIES
from ..models import Category, User
from ..schemas.category import CategoryCreate, CategoryRead
from ..security.deps import require_admin, require_user
from ..security.limiter import limiter
from ..services.audit import log_audit

router = APIRouter(prefix="/api/categories", tags=["categories"])

_settings = get_settings()


async def seed_categories(session: AsyncSession) -> None:
    """Seed the 6 default categories idempotently (missing names only)."""
    existing = set((await session.execute(select(Category.name))).scalars().all())
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            session.add(Category(name=name))
    await session.commit()


@router.get("", response_model=list[CategoryRead])
@limiter.limit(_settings.rate_limit_api)
async def list_categories(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(_settings.rate_limit_api)
async def create_category(
    request: Request,
    body: CategoryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> Category:
    existing = (
        await session.execute(select(Category).where(Category.name == body.name))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists",
        )
    category = Category(name=body.name)
    session.add(category)
    await session.flush()
    await log_audit(
        session,
        user_id=admin.id,
        entity_type="category",
        entity_id=category.id,
        action="create",
        changes={"name": category.name},
    )
    await session.commit()
    return category
