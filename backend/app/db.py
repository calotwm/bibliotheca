"""Async database engine and session factory.

Dialect-aware: PostgreSQL (asyncpg) in production, SQLite (aiosqlite) for
tests/dev. SQLite connections get ``PRAGMA foreign_keys=ON`` and transactions
are forced to ``BEGIN IMMEDIATE`` to serialize writers (used by the
invoice-numbering counter in a later slice).
"""

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

settings = get_settings()


def _configure_sqlite(engine: Engine) -> None:
    """Apply SQLite-specific pragmas and serialized write transactions."""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # Stop the DBAPI from emitting its own BEGIN/COMMIT so we control the
        # transaction mode in the "begin" listener below.
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _on_begin(connection):
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def build_engine(url: str):
    """Create an async engine for ``url`` with SQLite wiring applied."""
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_async_engine(url, echo=False, connect_args=connect_args)
    _configure_sqlite(engine.sync_engine)
    return engine


engine = build_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    async with SessionLocal() as session:
        yield session
