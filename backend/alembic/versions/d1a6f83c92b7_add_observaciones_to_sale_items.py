"""add observaciones to sale_items

Revision ID: d1a6f83c92b7
Revises: c3d8a1f5b2e6
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1a6f83c92b7'
down_revision: Union[str, Sequence[str], None] = 'c3d8a1f5b2e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "sale_items", sa.Column("observaciones", sa.String(length=200), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sale_items", "observaciones")
