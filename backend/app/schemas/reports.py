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