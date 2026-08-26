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
    "discount": "50% / 40%",
    "sale_condition": "Neto 30 días",
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
    assert data["discount"] == SUPPLIER_PAYLOAD["discount"]
    assert data["sale_condition"] == SUPPLIER_PAYLOAD["sale_condition"]

    detail = await client.get(f"/api/suppliers/{supplier_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["contact_name"] == "María López"
    assert detail.json()["discount"] == "50% / 40%"
    assert detail.json()["sale_condition"] == "Neto 30 días"

    listed = await client.get("/api/suppliers", headers=auth_headers)
    assert listed.status_code == 200
    listed_item = next(item for item in listed.json() if item["id"] == supplier_id)
    assert listed_item["discount"] == SUPPLIER_PAYLOAD["discount"]
    assert listed_item["sale_condition"] == SUPPLIER_PAYLOAD["sale_condition"]

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

    updated_fields = await client.put(
        f"/api/suppliers/{supplier_id}",
        json={"discount": "30%", "sale_condition": "Contado"},
        headers=auth_headers,
    )
    assert updated_fields.status_code == 200
    assert updated_fields.json()["discount"] == "30%"
    assert updated_fields.json()["sale_condition"] == "Contado"

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


async def test_supplier_nullable_fields_omit(auth_headers, client):
    created = await client.post(
        "/api/suppliers",
        json={
            "name": "Distribuidora Sin Datos",
            "contact_name": None,
            "email": None,
            "editorials": [],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["discount"] is None
    assert created.json()["sale_condition"] is None

    updated = await client.put(
        f"/api/suppliers/{created.json()['id']}",
        json={"discount": None, "sale_condition": None},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["discount"] is None
    assert updated.json()["sale_condition"] is None


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
    create_log = next(log for log in audit if log.action == "create")
    assert "discount" in create_log.changes_json
    assert create_log.changes_json["discount"] == SUPPLIER_PAYLOAD["discount"]
    assert "sale_condition" in create_log.changes_json
    assert create_log.changes_json["sale_condition"] == SUPPLIER_PAYLOAD["sale_condition"]


async def test_supplier_update_audited_with_field_diff(auth_headers, session, client):
    created = await client.post("/api/suppliers", json=SUPPLIER_PAYLOAD, headers=auth_headers)
    supplier_id = created.json()["id"]

    updated = await client.put(
        f"/api/suppliers/{supplier_id}",
        json={"discount": "30%", "sale_condition": "Contado"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["discount"] == "30%"
    assert updated.json()["sale_condition"] == "Contado"

    from app.models import AuditLog

    audit = (
        await session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "supplier",
                AuditLog.entity_id == supplier_id,
                AuditLog.action == "update",
            )
        )
    ).scalars().all()
    assert len(audit) == 1
    assert audit[0].changes_json["discount"] == {"old": "50% / 40%", "new": "30%"}
    assert audit[0].changes_json["sale_condition"] == {"old": "Neto 30 días", "new": "Contado"}