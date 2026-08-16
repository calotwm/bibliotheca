"""Sale request/response schemas (REQ-POS)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SaleItemCreate(BaseModel):
    book_id: int
    quantity: int = Field(ge=1)


class SaleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    items: list[SaleItemCreate] = Field(min_length=1)
    payment_method: str | None = Field(default=None, max_length=50)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_cuit: str | None = Field(default=None, max_length=32)


class SaleItemRead(BaseModel):
    id: int
    book_id: int
    book_title: str | None = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class SaleRead(BaseModel):
    id: int
    sale_number: int
    date: datetime
    total: Decimal
    payment_method: str | None = None
    customer_name: str | None = None
    customer_cuit: str | None = None
    invoice_pdf_path: str | None = None
    created_by: int | None = None
    created_at: datetime
    items: list[SaleItemRead] = []


class SaleListRead(BaseModel):
    id: int
    sale_number: int
    date: datetime
    total: Decimal
    payment_method: str | None = None
    customer_name: str | None = None
    customer_cuit: str | None = None
    created_by: int | None = None
    created_at: datetime
    item_count: int = 0