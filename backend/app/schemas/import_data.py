"""Pydantic schemas for Excel import preview/apply payloads."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ImportRow(BaseModel):
    """One normalized row returned by preview and accepted by apply.

    ``is_new`` is a preview-only prediction (insert vs update by natural key);
    apply recomputes reality from the database, so the flag is advisory.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    row_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    editorial: str = Field(min_length=1, max_length=255)
    genre: str | None = Field(default=None, max_length=120)
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0)
    observaciones: str | None = Field(default=None, max_length=200)
    is_new: bool = True


class ImportSheet(BaseModel):
    """Normalized rows for one source sheet (already mapped to a category)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sheet: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    rows: list[ImportRow] = Field(default_factory=list)


class ImportSheetSummary(BaseModel):
    """Per-sheet (or global) accounting for preview/apply."""

    sheet: str
    category: str | None = None
    parsed: int = 0
    inserts: int = 0
    updates: int = 0
    skips: int = 0
    errors: int = 0


class ImportTotals(BaseModel):
    parsed: int = 0
    inserts: int = 0
    updates: int = 0
    skips: int = 0
    errors: int = 0


class ImportRowError(BaseModel):
    sheet: str
    row_number: int
    message: str


class ImportPreviewResponse(BaseModel):
    """Stateless preview payload; ``token`` proves the applied rows were reviewed."""

    token: str
    filename: str
    sheets: list[ImportSheet] = Field(default_factory=list)
    summaries: list[ImportSheetSummary] = Field(default_factory=list)
    errors: list[ImportRowError] = Field(default_factory=list)
    totals: ImportTotals


class ImportApplyRequest(BaseModel):
    token: str = Field(min_length=1)
    filename: str = ""
    sheets: list[ImportSheet] = Field(default_factory=list)


class ImportApplyResponse(BaseModel):
    sheets: list[ImportSheetSummary] = Field(default_factory=list)
    totals: ImportTotals