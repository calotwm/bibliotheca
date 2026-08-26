"""add supplier sale condition and discount

Revision ID: bbd4ff3e1647
Revises: 7e82d91dbe21
Create Date: 2026-08-26 12:15:45.024206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbd4ff3e1647'
down_revision: Union[str, Sequence[str], None] = '7e82d91dbe21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "suppliers", sa.Column("discount", sa.Text(), nullable=True)
    )
    op.add_column(
        "suppliers", sa.Column("sale_condition", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("suppliers", "sale_condition")
    op.drop_column("suppliers", "discount")
