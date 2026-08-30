"""add seller to sales

Revision ID: a92e6ff2d840
Revises: bbd4ff3e1647
Create Date: 2026-08-29 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a92e6ff2d840'
down_revision: Union[str, Sequence[str], None] = 'bbd4ff3e1647'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("sales", sa.Column("seller", sa.String(length=40), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sales", "seller")