"""Supplier CRUD endpoints (REQ-SUP).

Reads require any authenticated user; writes (create/update/delete/editorial
mapping) require admin, per the design's ``GET/POST /api/suppliers`` and
``PUT/DELETE /api/suppliers/{id}`` matrix. Every mutating op is audited via
:func:`~app.services.audit.log_audit`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..db import get_session
from ..models import Supplier, SupplierEditorial, User
from ..schemas.supplier import (
    SupplierCreate,
    SupplierEditorialsUpdate,
    SupplierRead,
    SupplierUpdate,
)
from ..security.deps import require_admin, require_user
from ..security.limiter import limiter
from ..services.audit import log_audit

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

_settings = get_settings()


def _editorial_names(supplier: Supplier) -> list[str]:
    return sorted(ed.editorial for ed in supplier.editorials)


def _normalize_editorials(names: list[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in names or []:
        clean = raw.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _to_read(supplier: Supplier) -> SupplierRead:
    return SupplierRead(
        id=supplier.id,
        name=supplier.name,
        contact_name=supplier.contact_name,
        phone=supplier.phone,
        email=supplier.email,
        address=supplier.address,
        notes=supplier.notes,
        discount=supplier.discount,
        sale_condition=supplier.sale_condition,
        editorials=_editorial_names(supplier),
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
    )


async def _load_with_editorials(
    session: AsyncSession, supplier_id: int
) -> Supplier | None:
    return (
        await session.execute(
            select(Supplier)
            .options(selectinload(Supplier.editorials))
            .where(Supplier.id == supplier_id)
        )
    ).scalar_one_or_none()


def _set_editorials(supplier: Supplier, editorials: list[str]) -> None:
    """Populate the editorial mapping on a pending (not yet flushed) supplier.

    The transient collection is initialized empty, so no DB access happens
    here; FK is assigned by the relationship cascade on flush.
    """
    for name in editorials:
        supplier.editorials.append(SupplierEditorial(editorial=name))


async def _replace_editorials(
    session: AsyncSession, supplier: Supplier, editorials: list[str]
) -> None:
    """Replace a persisted supplier's editorial mapping.

    The clears are flushed before the inserts so a value being both removed
    and re-added in one replacement does not trip the unique constraint.
    """
    supplier.editorials.clear()
    await session.flush()
    for name in editorials:
        supplier.editorials.append(SupplierEditorial(editorial=name))


async def _name_taken(session: AsyncSession, name: str, *, exclude_id: int) -> bool:
    query = select(Supplier.id).where(func.lower(Supplier.name) == name.lower())
    if exclude_id is not None:
        query = query.where(Supplier.id != exclude_id)
    return (await session.execute(query)).scalar_one_or_none() is not None


@router.get("", response_model=list[SupplierRead])
@limiter.limit(_settings.rate_limit_api)
async def list_suppliers(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
) -> list[SupplierRead]:
    query = (
        select(Supplier)
        .options(selectinload(Supplier.editorials))
        .order_by(Supplier.name)
    )
    if q:
        like = f"%{q.lower()}%"
        query = query.where(func.lower(Supplier.name).like(like))
    query = query.offset((page - 1) * page_size).limit(page_size)
    suppliers = (await session.execute(query)).scalars().all()
    return [_to_read(supplier) for supplier in suppliers]


@router.get("/{supplier_id}", response_model=SupplierRead)
@limiter.limit(_settings.rate_limit_api)
async def get_supplier(
    request: Request,
    supplier_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> SupplierRead:
    supplier = await _load_with_editorials(session, supplier_id)
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    return _to_read(supplier)


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(_settings.rate_limit_api)
async def create_supplier(
    request: Request,
    body: SupplierCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> SupplierRead:
    if await _name_taken(session, body.name, exclude_id=-1):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Supplier name already exists"
        )
    editorials = _normalize_editorials(body.editorials)
    supplier = Supplier(
        name=body.name,
        contact_name=body.contact_name,
        phone=body.phone,
        email=body.email,
        address=body.address,
        notes=body.notes,
        discount=body.discount,
        sale_condition=body.sale_condition,
    )
    session.add(supplier)
    # Pending supplier: the editorial collection is initialized empty (no lazy
    # load), so it is safe to populate before flushing.
    _set_editorials(supplier, editorials)
    try:
        await session.flush()
        await log_audit(
            session,
            user_id=admin.id,
            entity_type="supplier",
            entity_id=supplier.id,
            action="create",
            changes={
                "name": supplier.name,
                "contact_name": supplier.contact_name,
                "phone": supplier.phone,
                "email": supplier.email,
                "address": supplier.address,
                "discount": supplier.discount,
                "sale_condition": supplier.sale_condition,
                "editorials": editorials,
            },
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Supplier name already exists",
        ) from exc

    supplier = await _load_with_editorials(session, supplier.id)
    assert supplier is not None
    return _to_read(supplier)


@router.put("/{supplier_id}", response_model=SupplierRead)
@limiter.limit(_settings.rate_limit_api)
async def update_supplier(
    request: Request,
    supplier_id: int,
    body: SupplierUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> SupplierRead:
    supplier = await _load_with_editorials(session, supplier_id)
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )

    data = body.model_dump(exclude_unset=True)
    editorials = _normalize_editorials(data.pop("editorials", None))
    if "name" in data and data["name"] != supplier.name:
        if await _name_taken(session, data["name"], exclude_id=supplier.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Supplier name already exists",
            )

    changes: dict = {}
    for field, value in data.items():
        old = getattr(supplier, field)
        if old != value:
            changes[field] = {"old": old, "new": value}
            setattr(supplier, field, value)

    if "editorials" in body.model_dump(exclude_unset=True) and (
        _editorial_names(supplier) != editorials
    ):
        await _replace_editorials(session, supplier, editorials)
        changes["editorials"] = editorials

    if changes:
        await log_audit(
            session,
            user_id=admin.id,
            entity_type="supplier",
            entity_id=supplier.id,
            action="update",
            changes=changes,
        )
    await session.commit()

    supplier = await _load_with_editorials(session, supplier.id)
    assert supplier is not None
    return _to_read(supplier)


@router.put("/{supplier_id}/editorials", response_model=SupplierRead)
@limiter.limit(_settings.rate_limit_api)
async def update_supplier_editorials(
    request: Request,
    supplier_id: int,
    body: SupplierEditorialsUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> SupplierRead:
    supplier = await _load_with_editorials(session, supplier_id)
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    editorials = _normalize_editorials(body.editorials)
    await _replace_editorials(session, supplier, editorials)
    await log_audit(
        session,
        user_id=admin.id,
        entity_type="supplier",
        entity_id=supplier.id,
        action="update_editorials",
        changes={"editorials": editorials},
    )
    await session.commit()

    supplier = await _load_with_editorials(session, supplier.id)
    assert supplier is not None
    return _to_read(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(_settings.rate_limit_api)
async def delete_supplier(
    request: Request,
    supplier_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> Response:
    # Editorials are eager-loaded so the delete-orphan cascade can run without
    # a lazy load in the async context.
    supplier = await _load_with_editorials(session, supplier_id)
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
        )
    name = supplier.name
    await log_audit(
        session,
        user_id=admin.id,
        entity_type="supplier",
        entity_id=supplier.id,
        action="delete",
        changes={"name": name},
    )
    await session.delete(supplier)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)