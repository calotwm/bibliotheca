"""add sale_number sequence for postgresql

Revision ID: 7e82d91dbe21
Revises: c8a237641254
Create Date: 2026-08-15 23:39:45.154857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e82d91dbe21'
down_revision: Union[str, Sequence[str], None] = 'c8a237641254'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE SEQUENCE IF NOT EXISTS sale_number_seq")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP SEQUENCE IF EXISTS sale_number_seq")
