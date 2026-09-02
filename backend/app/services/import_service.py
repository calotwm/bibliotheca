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

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..excel_import.parser import ParsedRow, parse_workbook
from ..models import Book, Category, User
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


def _canonical_sheets(sheets: Iterable[ImportSheet]) -> list[dict]:
    """Stable JSON-serializable view of the apply payload (excludes ``is_new``)."""
    return [
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
                    "observaciones": row.observaciones,
                }
                for row in sheet.rows
            ],
        }
        for sheet in sheets
    ]


def compute_token(sheets: Iterable[ImportSheet], deactivated: int = 0) -> str:
    """Content hash of the reviewed rows + deactivated count; mismatch aborts apply."""
    payload = {"sheets": _canonical_sheets(sheets), "deactivated": int(deactivated)}
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def _active_books_with_keys(
    session: AsyncSession,
) -> list[tuple[int, tuple[str, str, str]]]:
    """Return ``(book_id, natural_key)`` for every currently-active book."""
    rows = (
        await session.execute(
            select(Book.id, Book.title, Book.author, Book.editorial).where(
                Book.is_active.is_(True)
            )
        )
    ).all()
    return [
        (book_id, natural_key(title, author, editorial))
        for book_id, title, author, editorial in rows
    ]


async def _count_deactivated(
    session: AsyncSession, present_keys: set[tuple[str, str, str]]
) -> int:
    """Count active books whose natural key is absent from the file's row set."""
    return sum(
        1 for _, key in await _active_books_with_keys(session) if key not in present_keys
    )


async def _deactivate_absent_books(
    session: AsyncSession, present_keys: set[tuple[str, str, str]]
) -> int:
    """Deactivate active books not present in ``present_keys``; return the count."""
    absent_ids = [
        book_id
        for book_id, key in await _active_books_with_keys(session)
        if key not in present_keys
    ]
    if absent_ids:
        await session.execute(
            update(Book).where(Book.id.in_(absent_ids)).values(is_active=False)
        )
    return len(absent_ids)


async def _classify_rows(
    session: AsyncSession,
    sheet_name: str,
    rows: Iterable[ParsedRow],
    seen: set[tuple[str, str, str]],
) -> tuple[list[ImportRow], int, int, int, int, list[ImportRowError]]:
    """Classify one emit group's rows into insert/update/skip/error.

    Shared with the single-sheet path so genre-driven groups and aliased sheets
    use identical accounting (REQ-IMP-3).
    """
    inserts = updates = skips = row_errors = 0
    rows_payload: list[ImportRow] = []
    errors: list[ImportRowError] = []
    for row in rows:
        if row.skip_reason is not None:
            skips += 1
            # Noise rows never enter the payload (nor apply) and are never errors.
            continue
        if row.error is not None:
            row_errors += 1
            errors.append(
                ImportRowError(
                    sheet=sheet_name, row_number=row.row_number, message=row.error
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
                    observaciones=row.observaciones,
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
                observaciones=row.observaciones,
                is_new=is_new,
            )
        )
    return rows_payload, inserts, updates, skips, row_errors, errors


async def preview_import(
    session: AsyncSession, data: bytes, filename: str
) -> ImportPreviewResponse:
    """Parse the workbook and classify every row into insert/update/skip/error.

    Read-only: performs natural-key lookups but never writes (REQ-IMP-3).
    Genre-driven sheets are grouped by resolved category into one ImportSheet
    per category; aliased sheets are processed before genre-driven sheets so
    shared natural keys are claimed by the intended category.
    """
    available = list((await session.execute(select(Category.name))).scalars().all())
    workbook = parse_workbook(data, filename=filename, available_categories=available)

    sheets_payload: list[ImportSheet] = []
    summaries: list[ImportSheetSummary] = []
    errors: list[ImportRowError] = []
    totals = ImportTotals()
    seen: set[tuple[str, str, str]] = set()

    for sheet in sorted(workbook.sheets, key=lambda s: s.genre_driven):
        if sheet.genre_driven:
            groups: dict[str, list[ParsedRow]] = {}
            for row in sheet.rows:
                groups.setdefault(row.category, []).append(row)
            emissions = [(sheet.name, category, rows) for category, rows in groups.items()]
        else:
            emissions = [(sheet.name, sheet.category, sheet.rows)]

        for sheet_name, category, rows in emissions:
            rows_payload, inserts, updates, skips, row_errors, group_errors = (
                await _classify_rows(session, sheet_name, rows, seen)
            )
            errors.extend(group_errors)
            summaries.append(
                ImportSheetSummary(
                    sheet=sheet_name,
                    category=category,
                    parsed=len(rows),
                    inserts=inserts,
                    updates=updates,
                    skips=skips,
                    errors=row_errors,
                )
            )
            if category is not None and rows_payload:
                sheets_payload.append(
                    ImportSheet(sheet=sheet_name, category=category, rows=rows_payload)
                )

            totals.parsed += len(rows)
            totals.inserts += inserts
            totals.updates += updates
            totals.skips += skips
            totals.errors += row_errors

    deactivated = await _count_deactivated(session, seen)
    return ImportPreviewResponse(
        token=compute_token(sheets_payload, deactivated),
        filename=filename,
        sheets=sheets_payload,
        summaries=summaries,
        errors=errors,
        totals=totals,
        deactivated=deactivated,
    )


async def apply_import(
    session: AsyncSession, admin: User, request: ImportApplyRequest
) -> ImportApplyResponse:
    """Upsert the reviewed rows in ONE transaction (caller commits/rolls back).

    All-or-nothing (REQ-IMP-3): any invalid row aborts the whole import. In-file
    duplicate natural keys are skipped, matching the preview accounting.
    """
    if request.token != compute_token(request.sheets, request.deactivated):
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
                    observaciones=row.observaciones or "Juli",
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

    # REPLACE mode: after upserting (which re-activates present rows), deactivate
    # the active books whose natural key is absent from the imported row set.
    deactivated = await _deactivate_absent_books(session, seen)

    await log_audit(
        session,
        user_id=admin.id,
        entity_type="book",
        entity_id=None,
        action="import_apply",
        changes={
            "filename": request.filename,
            "deactivated": deactivated,
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
    return ImportApplyResponse(
        sheets=summaries, totals=totals, deactivated=deactivated
    )