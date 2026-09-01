"""add observaciones to books and sales

Revision ID: 5d9c1e3f7a28
Revises: a92e6ff2d840
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d9c1e3f7a28'
down_revision: Union[str, Sequence[str], None] = 'a92e6ff2d840'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "books", sa.Column("observaciones", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "sales", sa.Column("observaciones", sa.String(length=200), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sales", "observaciones")
    op.drop_column("books", "observaciones")
