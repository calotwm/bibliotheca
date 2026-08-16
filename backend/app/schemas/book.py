"""Book request/response schemas."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    editorial: str = Field(min_length=1, max_length=255)
    category_id: int
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0, default=0)
    isbn: str | None = Field(default=None, max_length=32)
    genre: str | None = Field(default=None, max_length=120)


class BookUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    editorial: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    isbn: str | None = Field(default=None, max_length=32)
    genre: str | None = Field(default=None, max_length=120)


class BookRead(BaseModel):
    id: int
    title: str
    author: str
    editorial: str
    category_id: int
    category_name: str | None = None
    price: Decimal
    stock: int
    isbn: str | None = None
    genre: str | None = None
    source_sheet: str | None = None
    is_active: bool
    stock_status: str
