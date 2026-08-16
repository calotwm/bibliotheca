"""Race-safe sequential invoice numbering (REQ-POS-3).

Portable strategy (design D1):
- PostgreSQL: ``pg_advisory_xact_lock`` + a real sequence inside the caller's
  transaction; the lock is released automatically on commit/rollback.
- SQLite (tests/dev): write-serialized ``numbering`` counter row. SQLite
  connections already force ``BEGIN IMMEDIATE`` (see ``app.db``), which
  serializes writers so the increment is race-safe.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

NUMBERING_KEY = "sale_number"
PG_SEQUENCE = "sale_number_seq"


async def next_sale_number(session: AsyncSession) -> int:
    """Allocate the next consecutive invoice number (caller controls commit).

    MUST be called inside the sale transaction: a rolled-back sale returns the
    number to the counter on SQLite (no gaps on abort), and the advisory lock
    is scoped to the transaction on PostgreSQL.
    """
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": NUMBERING_KEY}
        )
        result = await session.execute(text(f"SELECT nextval(:seq)"), {"seq": PG_SEQUENCE})
        return result.scalar_one()

    # SQLite fallback: write-serialized counter row.
    await session.execute(
        text(
            "INSERT INTO numbering (name, value) VALUES (:name, 0) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {"name": NUMBERING_KEY},
    )
    await session.execute(
        text("UPDATE numbering SET value = value + 1 WHERE name = :name"),
        {"name": NUMBERING_KEY},
    )
    result = await session.execute(
        text("SELECT value FROM numbering WHERE name = :name"), {"name": NUMBERING_KEY}
    )
    return result.scalar_one()