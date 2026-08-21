"""Pydantic schemas for editorial/author-scoped bulk updates (REQ-BULK)."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BulkAction = Literal["stock_add", "stock_set", "price_set", "price_percent"]


class BulkUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    editorial: str | None = Field(default=None, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    category_id: int | None = None
    action: BulkAction
    amount: Decimal

    @model_validator(mode="after")
    def _validate_scope(self) -> "BulkUpdateRequest":
        editorial = self.editorial.strip() if self.editorial else ""
        author = self.author.strip() if self.author else ""
        if editorial and author:
            raise ValueError("Proporcione editorial o autor, no ambos.")
        if not editorial and not author:
            raise ValueError("Proporcione editorial o autor.")
        return self


class BulkPreviewRow(BaseModel):
    """One affected book with the computed old -> new value for its field."""

    id: int
    title: str
    editorial: str
    field: str
    old_value: str
    new_value: str


class BulkPreviewResponse(BaseModel):
    editorial: str | None = None
    author: str | None = None
    category_id: int | None = None
    action: str
    amount: Decimal
    affected: int
    rows: list[BulkPreviewRow] = Field(default_factory=list)


class BulkApplyResponse(BaseModel):
    editorial: str | None = None
    author: str | None = None
    category_id: int | None = None
    action: str
    amount: Decimal
    affected: int