from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Numbering(Base):
    """SQLite-only fallback counter for sequential invoice numbers.

    Unused on PostgreSQL, where a real SEQUENCE + advisory lock is used.
    """

    __tablename__ = "numbering"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
