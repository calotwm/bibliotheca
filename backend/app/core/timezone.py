"""Buenos Aires timezone helpers (UTC-3, no DST).

``Sale.date`` stores absolute instants: fresh sales use ``now()``, which
PostgreSQL stores as ``timestamptz`` (UTC) and SQLite stores as the naive UTC
``CURRENT_TIMESTAMP``. The test suite seeds naive datetime objects and,
throughout this module, naive stored values are interpreted as UTC so the same
boundaries work on both dialects.

- :func:`period_filters` bounds a Buenos-Aires calendar range to absolute
  instants for ``WHERE`` clauses.
- :func:`ba_day_expr` yields the Buenos-Aires calendar day of a stored instant
  for ``GROUP BY``/``ORDER BY`` (PostgreSQL converts with ``timezone()``;
  SQLite shifts by the fixed -3h offset).
- :func:`ba_local_date` converts a stored instant to its Buenos-Aires day in
  Python (used when rows are already loaded).
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement

TZ_NAME = "America/Argentina/Buenos_Aires"
# Buenos Aires is UTC-3 with NO DST, so a fixed-offset timezone behaves
# identically to the IANA zone without requiring the ``tzdata`` package
# (Windows has no system tz database). PostgreSQL's ``timezone(TZ_NAME, ...)``
# still resolves the IANA name on the server side.
BUENOS_AIRES_TZ = timezone(timedelta(hours=-3))
UTC = timezone.utc
UTC_OFFSET = timedelta(hours=-3)
POSTGRES_DIALECT = "postgresql"


def ba_today() -> date:
    """Current calendar day in Buenos Aires."""
    return datetime.now(BUENOS_AIRES_TZ).date()


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Aware UTC instants bounding ``day`` as a Buenos-Aires calendar day."""
    start = datetime.combine(day, time.min, tzinfo=BUENOS_AIRES_TZ).astimezone(UTC)
    end = datetime.combine(day, time.max, tzinfo=BUENOS_AIRES_TZ).astimezone(UTC)
    return start, end


def as_utc(value: datetime) -> datetime:
    """Interpret a stored instant as aware UTC (naive stored values mean UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def as_naive_utc(value: datetime) -> datetime:
    """UTC instant with tzinfo dropped, for binding against SQLite values."""
    return as_utc(value).replace(tzinfo=None)


def ba_local_date(value: datetime) -> date:
    """Buenos-Aires calendar day of a stored instant (Python-convertible)."""
    return as_utc(value).astimezone(BUENOS_AIRES_TZ).date()


def ba_local_datetime(value: datetime) -> datetime:
    """Buenos-Aires local naive datetime of a stored absolute instant.

    Used to expose a stored instant to the client in the same local frame as
    :func:`ba_local_date`, so ``sale_datetime.date()`` == ``ba_local_date(...)``
    for a given instant.
    """
    return as_utc(value).astimezone(BUENOS_AIRES_TZ).replace(tzinfo=None)


def bound_for_dialect(instant: datetime, *, dialect_name: str) -> datetime:
    """Prepare an absolute instant as a comparison value for the dialect.

    PostgreSQL binds tz-aware values for its ``timestamptz`` column; SQLite
    stores naive values interpreted as UTC, so the tzinfo is dropped.
    """
    if dialect_name == POSTGRES_DIALECT:
        return instant
    return instant.replace(tzinfo=None)


def period_filters(
    column,
    start_date: date | None,
    end_date: date | None,
    *,
    dialect_name: str,
) -> list:
    """Range conditions on ``column`` (stored absolute instants).

    ``start_date``/``end_date`` are Buenos-Aires calendar days.
    """
    filters = []
    if start_date is not None:
        start, _ = day_bounds_utc(start_date)
        filters.append(column >= bound_for_dialect(start, dialect_name=dialect_name))
    if end_date is not None:
        _, end = day_bounds_utc(end_date)
        filters.append(column <= bound_for_dialect(end, dialect_name=dialect_name))
    return filters


def ba_day_expr(column, *, dialect_name: str) -> "ColumnElement":
    """SQL expression of the Buenos-Aires calendar day of a stored instant."""
    if dialect_name == POSTGRES_DIALECT:
        return func.date(func.timezone(TZ_NAME, column))
    return func.date(column, "-3 hours")