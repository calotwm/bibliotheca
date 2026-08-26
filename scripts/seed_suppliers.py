"""Seed distributor suppliers from a CSV against the local database.

Reads ``scripts/seed_suppliers.csv`` and inserts each row that is missing by
supplier ``name``. Re-runs are safe: rows whose name already exists are skipped,
so running this script twice inserts 17 on the first run and 0 on the second.

Usage:
  py scripts/seed_suppliers.py

Requires the backend env vars; sensible dev defaults are applied when unset.
"""

import asyncio
import csv
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
from app.models import Base, Supplier  # noqa: E402

CSV_PATH = REPO_ROOT / "scripts" / "seed_suppliers.csv"


def _to_none(value: str | None) -> str | None:
    """Coerce an empty CSV cell to None while preserving non-empty values."""
    if value is None or value == "":
        return None
    return value


async def main() -> int:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with CSV_PATH.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    async with SessionLocal() as session:
        existing = set(
            (
                await session.execute(select(Supplier.name))
            ).scalars().all()
        )
        inserted = 0
        skipped = 0
        for row in rows:
            name = (row.get("name") or "").strip()
            if not name:
                skipped += 1
                continue
            if name in existing:
                skipped += 1
                continue
            session.add(
                Supplier(
                    name=name,
                    contact_name=_to_none(row.get("contact_name")),
                    email=_to_none(row.get("email")),
                    sale_condition=_to_none(row.get("sale_condition")),
                    notes=_to_none(row.get("notes")),
                    discount=_to_none(row.get("discount")),
                )
            )
            existing.add(name)
            inserted += 1
        await session.commit()

    total = len(rows)
    print(f"inserted={inserted} skipped={skipped} total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
