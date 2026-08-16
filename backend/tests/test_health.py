"""Tests for the FastAPI app entrypoint, health endpoint, and CORS wiring."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_no_spa_mount_when_dist_missing(client):
    # Fresh clone: no frontend/dist/assets → "/" is not mounted, so it 404s.
    response = await client.get("/")
    assert response.status_code == 404


async def test_cors_preflight_allowlisted(client):
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_app_title():
    assert app.title == "Bibliotheca"
