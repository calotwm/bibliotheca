"""Pydantic schemas for editorial-scoped bulk updates (REQ-BULK)."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BulkAction = Literal["stock_add", "stock_set", "price_set", "price_percent"]


class BulkUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    editorial: str = Field(min_length=1, max_length=255)
    category_id: int | None = None
    action: BulkAction
    amount: Decimal


class BulkPreviewRow(BaseModel):
    """One affected book with the computed old -> new value for its field."""

    id: int
    title: str
    editorial: str
    field: str
    old_value: str
    new_value: str


class BulkPreviewResponse(BaseModel):
    editorial: str
    category_id: int | None = None
    action: str
    amount: Decimal
    affected: int
    rows: list[BulkPreviewRow] = Field(default_factory=list)


class BulkApplyResponse(BaseModel):
    editorial: str
    category_id: int | None = None
    action: str
    amount: Decimal
    affected: int