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


class TodaySales(BaseModel):
    count: int
    revenue: Decimal


class LowStockItem(BaseModel):
    book_id: int
    title: str
    author: str
    editorial: str
    stock: int
    stock_status: str


class RecentSaleRead(BaseModel):
    id: int
    sale_number: int
    date: datetime
    total: Decimal
    payment_method: str | None = None
    customer_name: str | None = None
    created_by: int | None = None
    item_count: int


class SalesDetailRow(BaseModel):
    sale_id: int
    sale_number: int
    date: date
    sale_datetime: datetime | None = None
    title: str
    author: str
    editorial: str
    category: str | None = None
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    stock: int
    payment_method: str | None = None
    observaciones: str | None = None
    juli_share: Decimal | None = None
    cande_share: Decimal | None = None


class EarningsRow(BaseModel):
    seller: str
    sale_count: int
    revenue: Decimal


class EarningsReport(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    rows: list[EarningsRow] = []


class DashboardRead(BaseModel):
    total_books: int
    total_units: int
    stock_value: Decimal
    today_sales: TodaySales
    low_stock: list[LowStockItem] = []
    out_of_stock_count: int
    recent_sales: list[RecentSaleRead] = []