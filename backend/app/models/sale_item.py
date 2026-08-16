from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    sale: Mapped["Sale"] = relationship(back_populates="items")
    book: Mapped["Book"] = relationship(back_populates="sale_items")
