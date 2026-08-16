"""Report and dashboard response schemas (REQ-REP-1)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class DaySummary(BaseModel):
    date: date
    sales: int
    revenue: Decimal


class SalesGroupSummary(BaseModel):
    key: str
    sales: int
    units: int
    revenue: Decimal


class SalesReport(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    total_sales: int
    total_revenue: Decimal
    by_day: list[DaySummary] = []
    group_by: str | None = None
    groups: list[SalesGroupSummary] = []


class TopSellerRead(BaseModel):
    book_id: int
    title: str
    author: str
    editorial: str
    quantity_sold: int
    revenue: Decimal


class InventoryReport(BaseModel):
    total_books: int
    total_units: int
    stock_value: Decimal
    status_counts: dict[str, int]
    threshold: int
    category_id: int | None = None


class CategoryMetric(BaseModel):
    category_id: int
    category: str
    sales: int
    units: int
    revenue: Decimal


class EditorialMetric(BaseModel):
    editorial: str
    sales: int
    units: int
    revenue: Decimal