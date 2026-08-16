from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)

    editorials: Mapped[list["SupplierEditorial"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierEditorial(Base):
    __tablename__ = "supplier_editorials"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id", "editorial", name="uq_supplier_editorials_supplier_editorial"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    editorial: Mapped[str] = mapped_column(String(255), nullable=False)

    supplier: Mapped["Supplier"] = relationship(back_populates="editorials")
