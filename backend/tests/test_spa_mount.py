"""SPA static-mount guard: fresh-clone safety, index.html fallback, API priority.

These tests build a fake ``frontend/dist`` tree and pass it explicitly to
``create_app(spa_dist=...)`` so the assertions never depend on whether a real
frontend build happens to exist on disk.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

INDEX_HTML = "<!doctype html><html><body>SPA</body></html>"
ASSET_JS = "console.log('app');"


@pytest.fixture
def fake_dist(tmp_path: Path) -> Path:
    """A minimal built-SPA tree: index.html + assets/."""
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (assets / "app.js").write_text(ASSET_JS, encoding="utf-8")
    return dist


async def _client_for(spa_dist: Path) -> AsyncClient:
    app = create_app(spa_dist=spa_dist)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_spa_served_from_dist(fake_dist: Path) -> None:
    async with await _client_for(fake_dist) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.text == INDEX_HTML


async def test_spa_fallback_for_client_routes(fake_dist: Path) -> None:
    async with await _client_for(fake_dist) as client:
        for route in ("/inventario", "/ventas", "/reportes", "/proveedores", "/importar"):
            response = await client.get(route)
            assert response.status_code == 200
            assert response.text == INDEX_HTML


async def test_spa_assets_served(fake_dist: Path) -> None:
    async with await _client_for(fake_dist) as client:
        response = await client.get("/assets/app.js")
        assert response.status_code == 200
        assert response.text == ASSET_JS


async def test_api_keeps_priority_over_spa(fake_dist: Path) -> None:
    async with await _client_for(fake_dist) as client:
        # Health endpoint still wins.
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Authenticated API route keeps priority (401 without a token, not HTML).
        response = await client.get("/api/books")
        assert response.status_code == 401


async def test_unknown_api_paths_stay_api_semantics(fake_dist: Path) -> None:
    async with await _client_for(fake_dist) as client:
        response = await client.get("/api/definitely-not-a-route")
        assert response.status_code == 404


async def test_no_spa_mount_without_build(tmp_path: Path) -> None:
    empty = tmp_path / "dist"
    empty.mkdir()
    async with await _client_for(empty) as client:
        response = await client.get("/")
        assert response.status_code == 404