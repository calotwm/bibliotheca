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
    seller: str | None = None
    payment_method: str | None = None
    customer_name: str | None = None
    created_by: int | None = None
    item_count: int


class SalesDetailRow(BaseModel):
    sale_id: int
    sale_number: int
    date: date
    title: str
    author: str
    editorial: str
    category: str | None = None
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    stock: int
    seller: str | None = None
    payment_method: str | None = None


class SellerSummary(BaseModel):
    seller: str
    sale_count: int
    total_revenue: Decimal
    shared_sale_count: int
    shared_revenue: Decimal


class SellerReport(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    sellers: list[SellerSummary] = []


class DashboardRead(BaseModel):
    total_books: int
    total_units: int
    stock_value: Decimal
    today_sales: TodaySales
    low_stock: list[LowStockItem] = []
    out_of_stock_count: int
    recent_sales: list[RecentSaleRead] = []