"""FastAPI application entry point."""

from __future__ import annotations

import importlib
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import SessionLocal
from .models import User
from .routers import audit, auth, books, categories, dashboard, editorial_bulk, reports, sales, suppliers
from .routers.categories import seed_categories
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
        await seed_categories(session)
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


def _mount_spa_if_built(app: FastAPI, dist_dir: Path | None = None) -> None:
    """Serve the built SPA with an ``index.html`` fallback.

    Fresh-clone guard: the mount only happens when a real build exists
    (``frontend/dist/assets`` present), so a checkout without a frontend build
    must not crash the backend on startup (lubricentro lesson).

    ``/api/**`` and ``/health`` are registered before the SPA routes, so they
    keep priority. Every other GET falls back to ``index.html`` so client-side
    routes (``/inventario``, ``/ventas``, ...) resolve to the SPA instead of
    404ing. Unknown ``/api/**`` paths keep API semantics (404), never a page.
    """
    if dist_dir is None:
        dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    index_file = dist_dir / "index.html"
    if dist_dir.is_dir() and assets_dir.is_dir() and index_file.is_file():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="spa-assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            if full_path == "health" or full_path.startswith("api/"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
                )
            return FileResponse(str(index_file))


def create_app(spa_dist: Path | None = None) -> FastAPI:
    app = FastAPI(title="Ojo de Poeta - Libros", lifespan=lifespan)

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
    app.include_router(categories.router)
    app.include_router(books.router)
    app.include_router(sales.router)
    app.include_router(suppliers.router)
    app.include_router(audit.router)
    app.include_router(reports.router)
    app.include_router(dashboard.router)
    # The import router lives in a module literally named ``import`` (reserved
    # keyword), so it is wired through importlib instead of ``from ... import``.
    app.include_router(importlib.import_module("app.routers.import").router)
    app.include_router(editorial_bulk.router)

    _mount_spa_if_built(app, spa_dist)
    return app


app = create_app()
