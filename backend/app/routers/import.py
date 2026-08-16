"""Excel import endpoints: preview (read-only) and transactional apply.

Admin-only (require_admin). The module is deliberately named ``import`` per
the SDD design; it is wired into the app via ``importlib`` in ``main.py``
because ``import`` is a reserved keyword in ``from ... import ...``.
"""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..excel_import.parser import ExcelImportError
from ..models import User
from ..schemas.import_data import (
    ImportApplyRequest,
    ImportApplyResponse,
    ImportPreviewResponse,
)
from ..security.deps import require_admin
from ..security.limiter import limiter
from ..services.import_service import (
    MAX_UPLOAD_BYTES,
    ImportApplyError,
    apply_import,
    preview_import,
)

router = APIRouter(prefix="/api/import", tags=["import"])

_settings = get_settings()


@router.post("/preview", response_model=ImportPreviewResponse)
@limiter.limit(_settings.rate_limit_api)
async def preview(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
    file: UploadFile = File(...),
) -> ImportPreviewResponse:
    """Parse an uploaded ``.xlsx`` and report per-sheet counts. Never writes."""
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type; expected an .xlsx file",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )
    try:
        return await preview_import(session, data, file.filename or "catalog.xlsx")
    except ExcelImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/apply", response_model=ImportApplyResponse)
@limiter.limit(_settings.rate_limit_api)
async def apply(
    request: Request,
    body: ImportApplyRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(require_admin)],
) -> ImportApplyResponse:
    """Apply a reviewed preview payload in one all-or-nothing transaction."""
    try:
        result = await apply_import(session, admin, body)
    except ImportApplyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return result