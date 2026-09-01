"""Sale request/response schemas (REQ-POS)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SellerName = Literal["Cande", "Julieta", "Cande y Julieta"]


class SaleItemCreate(BaseModel):
    book_id: int
    quantity: int = Field(ge=1)


class SaleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    items: list[SaleItemCreate] = Field(min_length=1)
    seller: SellerName
    payment_method: str | None = Field(default=None, max_length=50)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_cuit: str | None = Field(default=None, max_length=32)
    observaciones: str | None = Field(default=None, max_length=200)


class SaleItemRead(BaseModel):
    id: int
    book_id: int
    book_title: str | None = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class SaleUpdate(BaseModel):
    """Optional sale header fields; at least one must be provided.

    ``None`` explicitly clears a field (e.g. ``seller: null`` means
    "Sin vendedor"). Only fields present in the request body are updated; the
    validator distinguishes "not sent" from "sent as null".
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    seller: SellerName | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_cuit: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _at_least_one_field_present(self) -> "SaleUpdate":
        if not (
            self.model_fields_set
            & {"seller", "payment_method", "customer_name", "customer_cuit"}
        ):
            raise ValueError(
                "At least one field (seller, payment_method, customer_name, "
                "customer_cuit) must be provided"
            )
        return self


class SaleRead(BaseModel):
    id: int
    sale_number: int
    date: datetime
    total: Decimal
    seller: str | None = None
    payment_method: str | None = None
    customer_name: str | None = None
    customer_cuit: str | None = None
    invoice_pdf_path: str | None = None
    observaciones: str | None = None
    created_by: int | None = None
    created_at: datetime
    items: list[SaleItemRead] = []


class SaleListRead(BaseModel):
    id: int
    sale_number: int
    date: datetime
    total: Decimal
    seller: str | None = None
    payment_method: str | None = None
    customer_name: str | None = None
    customer_cuit: str | None = None
    observaciones: str | None = None
    created_by: int | None = None
    created_at: datetime
    item_count: int = 0