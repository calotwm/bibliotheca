"""Tests for the async engine/session factory."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import build_engine


async def test_engine_session_roundtrip(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path.as_posix()}/test.db"
    engine = build_engine(url)
    try:
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()


async def test_sqlite_foreign_keys_enabled(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path.as_posix()}/fk.db"
    engine = build_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA foreign_keys"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()
