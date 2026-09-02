"""drop seller and add automatic share columns to sales

Revision ID: f4a2c7e9b1d3
Revises: 5d9c1e3f7a28
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a2c7e9b1d3'
down_revision: Union[str, Sequence[str], None] = '5d9c1e3f7a28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the free-text ``seller`` column and add the share columns."""
    op.drop_column("sales", "seller")
    op.add_column(
        "sales", sa.Column("juli_share", sa.Numeric(precision=5, scale=2), nullable=True)
    )
    op.add_column(
        "sales", sa.Column("cande_share", sa.Numeric(precision=5, scale=2), nullable=True)
    )


def downgrade() -> None:
    """Restore ``seller`` and remove the share columns."""
    op.drop_column("sales", "cande_share")
    op.drop_column("sales", "juli_share")
    op.add_column("sales", sa.Column("seller", sa.String(length=40), nullable=True))
