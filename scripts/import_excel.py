"""Import the real Excel catalog file against the local database.

Preview-only by default (parses and reports per-sheet counts without writing).
Pass ``--apply`` to run the same all-or-nothing upsert the API uses.

Usage:
  py scripts/import_excel.py [path.xlsx] [--apply]

Requires the backend env vars; sensible dev defaults are applied when unset.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

os.environ.setdefault("SECRET_KEY", "dev-secret-not-for-production")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./bibliotheca.db")

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.models import Base, User  # noqa: E402
from app.routers.categories import seed_categories  # noqa: E402
from app.schemas.import_data import ImportApplyRequest  # noqa: E402
from app.security.password import hash_password  # noqa: E402
from app.services.import_service import apply_import, preview_import  # noqa: E402

DEFAULT_FILE = Path.home() / "Downloads" / "Catálogo Agosto '26.xlsx"


async def _ensure_admin(session) -> User:
    username = os.environ["ADMIN_USERNAME"]
    admin = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if admin is None:
        admin = User(
            username=username,
            password_hash=hash_password(os.environ["ADMIN_PASSWORD"]),
            role="admin",
        )
        session.add(admin)
        await session.commit()
    return admin


async def main(path: Path, apply: bool) -> int:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_categories(session)
        preview = await preview_import(session, path.read_bytes(), path.name)
        print(f"\n{path.name}")
        for summary in preview.summaries:
            print(
                f"  {summary.sheet:<20} cat={summary.category!r:<16} "
                f"parsed={summary.parsed} ins={summary.inserts} "
                f"upd={summary.updates} skip={summary.skips} err={summary.errors}"
            )
        print(
            f"  {'TOTAL':<20} parsed={preview.totals.parsed} ins={preview.totals.inserts} "
            f"upd={preview.totals.updates} skip={preview.totals.skips} err={preview.totals.errors}"
        )
        for error in preview.errors:
            print(f"  ERROR {error.sheet} row {error.row_number}: {error.message}")

        if apply:
            admin = await _ensure_admin(session)
            request = ImportApplyRequest(
                token=preview.token, filename=path.name, sheets=preview.sheets
            )
            result = await apply_import(session, admin, request)
            await session.commit()
            print(
                f"\nAPPLIED: ins={result.totals.inserts} "
                f"upd={result.totals.updates} skip={result.totals.skips}"
            )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import the Ojo de Poeta - Libros Excel catalog locally"
    )
    parser.add_argument("file", nargs="?", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(2)
    raise SystemExit(asyncio.run(main(args.file, args.apply)))