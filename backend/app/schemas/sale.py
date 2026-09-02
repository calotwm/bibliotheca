"""Sale request/response schemas (REQ-POS)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SaleItemCreate(BaseModel):
    book_id: int
    quantity: int = Field(ge=1)


class SaleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    items: list[SaleItemCreate] = Field(min_length=1)
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

    ``None`` explicitly clears a field (e.g. ``payment_method: null``). Only
    fields present in the request body are updated; the validator distinguishes
    "not sent" from "sent as null". ``juli_share``/``cande_share`` are a pair:
    either both are sent (summing to exactly 100) or neither.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    date: datetime | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_cuit: str | None = Field(default=None, max_length=32)
    juli_share: Decimal | None = Field(default=None, ge=0, le=100)
    cande_share: Decimal | None = Field(default=None, ge=0, le=100)

    @field_validator("juli_share", "cande_share")
    @classmethod
    def _quantize_share(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        return value.quantize(Decimal("0.01"))

    @model_validator(mode="after")
    def _at_least_one_field_present(self) -> "SaleUpdate":
        if not (
            self.model_fields_set
            & {
                "date",
                "payment_method",
                "customer_name",
                "customer_cuit",
                "juli_share",
                "cande_share",
            }
        ):
            raise ValueError(
                "At least one field (date, payment_method, customer_name, "
                "customer_cuit, juli_share, cande_share) must be provided"
            )
        return self

    @model_validator(mode="after")
    def _shares_both_or_neither(self) -> "SaleUpdate":
        has_juli = "juli_share" in self.model_fields_set
        has_cande = "cande_share" in self.model_fields_set
        if has_juli or has_cande:
            if not (has_juli and has_cande):
                raise ValueError("juli_share and cande_share must be provided together")
            if self.juli_share is None or self.cande_share is None:
                raise ValueError("juli_share and cande_share are required together")
            if self.juli_share + self.cande_share != Decimal("100"):
                raise ValueError("juli_share and cande_share must sum to 100")
        return self

    @model_validator(mode="after")
    def _date_not_null_when_present(self) -> "SaleUpdate":
        if "date" in self.model_fields_set and self.date is None:
            raise ValueError("date must not be null")
        return self


class SaleRead(BaseModel):
    id: int
    sale_number: int
    date: datetime
    total: Decimal
    juli_share: Decimal | None = None
    cande_share: Decimal | None = None
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
    juli_share: Decimal | None = None
    cande_share: Decimal | None = None
    payment_method: str | None = None
    customer_name: str | None = None
    customer_cuit: str | None = None
    observaciones: str | None = None
    created_by: int | None = None
    created_at: datetime
    item_count: int = 0
