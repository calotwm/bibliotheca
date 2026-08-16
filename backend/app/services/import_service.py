"""Excel import preview and apply services (REQ-IMP-1..4).

Preview parses the workbook and reports per-sheet counts WITHOUT writing
anything; apply runs one all-or-nothing transaction reusing the catalog
natural-key upsert and audits the outcome. The preview token ties apply to the
exact reviewed payload (no server-side state required).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..excel_import.parser import ExcelImportError, parse_workbook
from ..models import Category, User
from ..schemas.import_data import (
    ImportApplyRequest,
    ImportApplyResponse,
    ImportPreviewResponse,
    ImportRow,
    ImportRowError,
    ImportSheet,
    ImportSheetSummary,
    ImportTotals,
)
from .audit import log_audit
from .catalog import find_by_natural_key, natural_key, upsert_book

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class ImportApplyError(Exception):
    """Apply failed; the caller rolls back the whole transaction."""


def _canonical_sheets(sheets: Iterable[ImportSheet]) -> str:
    """Stable JSON view of the apply payload (excludes the preview-only ``is_new``)."""
    payload = [
        {
            "sheet": sheet.sheet,
            "category": sheet.category,
            "rows": [
                {
                    "row_number": row.row_number,
                    "title": row.title,
                    "author": row.author,
                    "editorial": row.editorial,
                    "genre": row.genre,
                    "price": str(row.price),
                    "stock": row.stock,
                }
                for row in sheet.rows
            ],
        }
        for sheet in sheets
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_token(sheets: Iterable[ImportSheet]) -> str:
    """Content hash of the reviewed rows; mismatch aborts apply."""
    return hashlib.sha256(_canonical_sheets(sheets).encode("utf-8")).hexdigest()


async def preview_import(
    session: AsyncSession, data: bytes, filename: str
) -> ImportPreviewResponse:
    """Parse the workbook and classify every row into insert/update/skip/error.

    Read-only: performs natural-key lookups but never writes (REQ-IMP-3).
    """
    available = list((await session.execute(select(Category.name))).scalars().all())
    try:
        workbook = parse_workbook(data, filename=filename, available_categories=available)
    except ExcelImportError as exc:
        raise exc

    sheets_payload: list[ImportSheet] = []
    summaries: list[ImportSheetSummary] = []
    errors: list[ImportRowError] = []
    totals = ImportTotals()
    seen: set[tuple[str, str, str]] = set()

    for sheet in workbook.sheets:
        inserts = updates = skips = row_errors = 0
        rows_payload: list[ImportRow] = []
        for row in sheet.rows:
            if row.error is not None:
                row_errors += 1
                errors.append(
                    ImportRowError(
                        sheet=sheet.name, row_number=row.row_number, message=row.error
                    )
                )
                continue
            key = natural_key(row.title, row.author, row.editorial)
            if key in seen:
                skips += 1
                # Still carried in the payload so apply's skip count matches the
                # preview; apply re-detects the duplicate and never upserts it.
                rows_payload.append(
                    ImportRow(
                        row_number=row.row_number,
                        title=row.title,
                        author=row.author,
                        editorial=row.editorial,
                        genre=row.genre,
                        price=row.price,
                        stock=row.stock,
                        is_new=False,
                    )
                )
                continue
            seen.add(key)
            existing = await find_by_natural_key(
                session, row.title, row.author, row.editorial
            )
            is_new = existing is None
            if is_new:
                inserts += 1
            else:
                updates += 1
            rows_payload.append(
                ImportRow(
                    row_number=row.row_number,
                    title=row.title,
                    author=row.author,
                    editorial=row.editorial,
                    genre=row.genre,
                    price=row.price,
                    stock=row.stock,
                    is_new=is_new,
                )
            )

        parsed = len(sheet.rows)
        summaries.append(
            ImportSheetSummary(
                sheet=sheet.name,
                category=sheet.category,
                parsed=parsed,
                inserts=inserts,
                updates=updates,
                skips=skips,
                errors=row_errors,
            )
        )
        if sheet.category is not None and rows_payload:
            sheets_payload.append(
                ImportSheet(sheet=sheet.name, category=sheet.category, rows=rows_payload)
            )

        totals.parsed += parsed
        totals.inserts += inserts
        totals.updates += updates
        totals.skips += skips
        totals.errors += row_errors

    return ImportPreviewResponse(
        token=compute_token(sheets_payload),
        filename=filename,
        sheets=sheets_payload,
        summaries=summaries,
        errors=errors,
        totals=totals,
    )


async def apply_import(
    session: AsyncSession, admin: User, request: ImportApplyRequest
) -> ImportApplyResponse:
    """Upsert the reviewed rows in ONE transaction (caller commits/rolls back).

    All-or-nothing (REQ-IMP-3): any invalid row aborts the whole import. In-file
    duplicate natural keys are skipped, matching the preview accounting.
    """
    if request.token != compute_token(request.sheets):
        raise ImportApplyError("Preview token mismatch; re-run preview before applying")

    category_names = {sheet.category for sheet in request.sheets}
    categories = (
        await session.execute(
            select(Category).where(Category.name.in_(category_names))
        )
    ).scalars().all()
    category_ids = {category.name: category.id for category in categories}

    summaries: list[ImportSheetSummary] = []
    totals = ImportTotals()
    seen: set[tuple[str, str, str]] = set()

    try:
        for sheet in request.sheets:
            category_id = category_ids.get(sheet.category)
            if category_id is None:
                raise ImportApplyError(f"Unknown category {sheet.category!r}")
            inserts = updates = skips = 0
            for row in sheet.rows:
                key = natural_key(row.title, row.author, row.editorial)
                if key in seen:
                    skips += 1
                    continue
                seen.add(key)
                _, created = await upsert_book(
                    session,
                    title=row.title,
                    author=row.author,
                    editorial=row.editorial,
                    category_id=category_id,
                    price=row.price,
                    stock=row.stock,
                    genre=row.genre,
                    source_sheet=sheet.sheet,
                )
                if created:
                    inserts += 1
                else:
                    updates += 1
            summaries.append(
                ImportSheetSummary(
                    sheet=sheet.sheet,
                    category=sheet.category,
                    parsed=len(sheet.rows),
                    inserts=inserts,
                    updates=updates,
                    skips=skips,
                    errors=0,
                )
            )
            totals.parsed += len(sheet.rows)
            totals.inserts += inserts
            totals.updates += updates
            totals.skips += skips
    except IntegrityError as exc:
        raise ImportApplyError(
            "Import aborted: a row violates a database constraint"
        ) from exc

    await log_audit(
        session,
        user_id=admin.id,
        entity_type="book",
        entity_id=None,
        action="import_apply",
        changes={
            "filename": request.filename,
            "sheets": [
                {
                    "sheet": s.sheet,
                    "inserts": s.inserts,
                    "updates": s.updates,
                    "skips": s.skips,
                }
                for s in summaries
            ],
        },
    )
    return ImportApplyResponse(sheets=summaries, totals=totals)