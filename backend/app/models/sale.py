from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_cuit: Mapped[str | None] = mapped_column(String(32))
    invoice_pdf_path: Mapped[str | None] = mapped_column(String(512))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )
    user: Mapped["User"] = relationship(back_populates="sales")
