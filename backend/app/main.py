"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Admin bootstrap and category seeding are wired in later slices.
    yield


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
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    _mount_spa_if_built(app)
    return app


app = create_app()
