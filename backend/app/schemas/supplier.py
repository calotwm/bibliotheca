"""Supplier request/response schemas (REQ-SUP)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SupplierBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=512)
    notes: str | None = None
    editorials: list[str] = Field(default_factory=list)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=512)
    notes: str | None = None
    editorials: list[str] | None = None


class SupplierEditorialsUpdate(BaseModel):
    editorials: list[str] = Field(default_factory=list)


class SupplierRead(BaseModel):
    id: int
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    editorials: list[str] = []
    created_at: datetime
    updated_at: datetime