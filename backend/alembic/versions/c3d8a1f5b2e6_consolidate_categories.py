"""consolidate biography/essay categories into No Ficción

Revision ID: c3d8a1f5b2e6
Revises: f4a2c7e9b1d3
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

import unicodedata

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d8a1f5b2e6'
down_revision: Union[str, Sequence[str], None] = 'f4a2c7e9b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# "unificamos todo en No ficción": biography, autobiography, chronicle, letters,
# diary and essay categories are merged into the single No Ficción category.
MERGE_TARGET = "No Ficción"
MERGE_SOURCES = (
    "Biografía",
    "Autobiografía",
    "Crónicas",
    "Cartas",
    "Diarios",
    "Ensayo",
)


def _fold(value: str) -> str:
    """Fold case and strip accents so category names compare loosely."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(
        c for c in decomposed if not unicodedata.combining(c)
    ).strip().casefold()


def _merge_categories(bind) -> list[str]:
    """Move every book into ``MERGE_TARGET`` and delete the merged categories.

    Idempotent-ish: categories that are already absent are skipped. Returns the
    display names of the categories that were deleted.
    """
    rows = bind.execute(sa.text("SELECT id, name FROM categories")).fetchall()

    target_id = None
    for category_id, name in rows:
        if _fold(name) == _fold(MERGE_TARGET):
            target_id = category_id
            break

    if target_id is None:
        bind.execute(
            sa.text("INSERT INTO categories (name) VALUES (:name)"),
            {"name": MERGE_TARGET},
        )
        target_id = bind.execute(
            sa.text("SELECT id FROM categories WHERE name = :name"),
            {"name": MERGE_TARGET},
        ).scalar()

    source_folded = {_fold(name) for name in MERGE_SOURCES}
    deleted: list[str] = []
    for category_id, name in rows:
        if category_id == target_id:
            continue
        if _fold(name) in source_folded:
            bind.execute(
                sa.text(
                    "UPDATE books SET category_id = :target WHERE category_id = :cid"
                ),
                {"target": target_id, "cid": category_id},
            )
            bind.execute(
                sa.text("DELETE FROM categories WHERE id = :cid"),
                {"cid": category_id},
            )
            deleted.append(name)
    return deleted


def upgrade() -> None:
    """Consolidate the merged categories into No Ficción."""
    _merge_categories(op.get_bind())


def downgrade() -> None:
    """No-op: the consolidation is irreversible (books stay under No Ficción)."""
