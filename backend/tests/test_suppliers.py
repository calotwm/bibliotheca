"""Tests for supplier CRUD + editorial mapping (REQ-SUP)."""

from sqlalchemy import select

from app.models import Supplier, User
from app.security.jwt import create_access_token
from app.security.password import hash_password

SUPPLIER_PAYLOAD = {
    "name": "Distribuidora del Sur",
    "contact_name": "María López",
    "phone": "11-5555-1234",
    "email": "ventas@distribuidoradelsur.com.ar",
    "address": "Av. de Mayo 789",
    "notes": "Entrega semanal",
    "editorials": ["Sudamericana", "Planeta"],
}


async def _cashier_headers(session) -> dict:
    user = User(username="cashier", password_hash=hash_password("cashier"), role="cashier")
    session.add(user)
    await session.commit()
    token = create_access_token("cashier", "cashier")
    return {"Authorization": f"Bearer {token}"}


async def test_supplier_crud_happy_path(auth_headers, session, client):
    created = await client.post("/api/suppliers", json=SUPPLIER_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    data = created.json()
    supplier_id = data["id"]
    assert data["name"] == SUPPLIER_PAYLOAD["name"]
    assert data["editorials"] == ["Planeta", "Sudamericana"]

    detail = await client.get(f"/api/suppliers/{supplier_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["contact_name"] == "María López"

    listed = await client.get("/api/suppliers", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == supplier_id for item in listed.json())

    search = await client.get("/api/suppliers?q=del%20sur", headers=auth_headers)
    assert search.status_code == 200
    assert [item["name"] for item in search.json()] == ["Distribuidora del Sur"]

    updated = await client.put(
        f"/api/suppliers/{supplier_id}",
        json={"phone": "11-5555-9999", "editorials": ["Planeta"]},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "11-5555-9999"
    assert updated.json()["editorials"] == ["Planeta"]

    mapping = await client.put(
        f"/api/suppliers/{supplier_id}/editorials",
        json={"editorials": ["Sudamericana", "Emecé"]},
        headers=auth_headers,
    )
    assert mapping.status_code == 200
    assert mapping.json()["editorials"] == ["Emecé", "Sudamericana"]

    deleted = await client.delete(f"/api/suppliers/{supplier_id}", headers=auth_headers)
    assert deleted.status_code == 204
    gone = await client.get(f"/api/suppliers/{supplier_id}", headers=auth_headers)
    assert gone.status_code == 404


async def test_supplier_validation(auth_headers, client):
    empty_name = await client.post(
        "/api/suppliers", json={"name": "  "}, headers=auth_headers
    )
    assert empty_name.status_code == 422

    too_long = await client.post(
        "/api/suppliers", json={"name": "x" * 256}, headers=auth_headers
    )
    assert too_long.status_code == 422


async def test_supplier_duplicate_name_409(auth_headers, client):
    first = await client.post("/api/suppliers", json=SUPPLIER_PAYLOAD, headers=auth_headers)
    assert first.status_code == 201
    duplicate = await client.post("/api/suppliers", json=SUPPLIER_PAYLOAD, headers=auth_headers)
    assert duplicate.status_code == 409


async def test_supplier_cashier_cannot_write(auth_headers, session, client):
    headers = await _cashier_headers(session)
    created = await client.post("/api/suppliers", json=SUPPLIER_PAYLOAD, headers=headers)
    assert created.status_code == 403
    listed = await client.get("/api/suppliers", headers=headers)
    assert listed.status_code == 200


async def test_supplier_reads_require_auth(client):
    assert (await client.get("/api/suppliers")).status_code == 401
    assert (await client.get("/api/suppliers/1")).status_code == 401


async def test_supplier_missing_404(auth_headers, client):
    assert (await client.get("/api/suppliers/9999", headers=auth_headers)).status_code == 404
    assert (
        await client.put(
            "/api/suppliers/9999", json={"phone": "x"}, headers=auth_headers
        )
    ).status_code == 404
    assert (
        await client.delete("/api/suppliers/9999", headers=auth_headers)
    ).status_code == 404


async def test_supplier_audited_on_create_and_delete(auth_headers, session, client):
    created = await client.post("/api/suppliers", json=SUPPLIER_PAYLOAD, headers=auth_headers)
    supplier_id = created.json()["id"]
    await client.delete(f"/api/suppliers/{supplier_id}", headers=auth_headers)

    logs = (await session.execute(select(Supplier))).scalars().all()
    assert len(logs) == 0
    # audit rows survive the hard delete
    from app.models import AuditLog

    audit = (
        await session.execute(
            select(AuditLog).where(AuditLog.entity_type == "supplier")
        )
    ).scalars().all()
    assert [log.action for log in audit] == ["create", "delete"]