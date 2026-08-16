"""FastAPI application entry point."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import SessionLocal
from .models import User
from .routers import auth
from .security.cors import parse_allowed_origins
from .security.limiter import limiter
from .security.password import hash_password

settings = get_settings()


async def bootstrap_admin(session: AsyncSession) -> None:
    """Create the admin user from env on first run (idempotent)."""
    existing = (
        await session.execute(
            select(User).where(User.username == settings.admin_username)
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
        )
        await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with SessionLocal() as session:
        await bootstrap_admin(session)
    yield


def _rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return 429 with a Retry-After header (always set)."""
    response = JSONResponse(
        status_code=429, content={"detail": "Rate limit exceeded"}
    )
    retry_after = 60
    view_rate_limit = getattr(request.state, "view_rate_limit", None)
    if view_rate_limit is not None:
        rate_limit_item, keys = view_rate_limit
        try:
            reset_time, _ = limiter.limiter.get_window_stats(
                rate_limit_item, *keys
            )
            retry_after = max(1, int(reset_time - time.time()))
        except Exception:
            pass
    response.headers["Retry-After"] = str(retry_after)
    return response


def _mount_spa_if_built(app: FastAPI) -> None:
    """Mount the built SPA only if ``frontend/dist/assets`` exists.

    Fresh-clone guard: a checkout without a frontend build must not crash the
    backend on startup (lubricentro lesson).
    """
    dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    if dist_dir.is_dir() and assets_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="spa")


def create_app() -> FastAPI:
    app = FastAPI(title="Bibliotheca", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_allowed_origins(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)

    _mount_spa_if_built(app)
    return app


app = create_app()
