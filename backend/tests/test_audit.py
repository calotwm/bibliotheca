"""Tests for the read-only audit log (REQ-AUD-1/2, admin only)."""

from app.models import User
from app.security.jwt import create_access_token
from app.security.password import hash_password

SUPPLIER_PAYLOAD = {"name": "Distribuidora del Norte", "editorials": ["Planeta"]}


async def _cashier_headers(session) -> dict:
    user = User(username="cashier", password_hash=hash_password("cashier"), role="cashier")
    session.add(user)
    await session.commit()
    token = create_access_token("cashier", "cashier")
    return {"Authorization": f"Bearer {token}"}


async def _seed_audit_rows(client, auth_headers) -> None:
    for name in ["Distribuidora del Norte", "Distribuidora del Este"]:
        await client.post(
            "/api/suppliers",
            json={"name": name, "editorials": ["Planeta"]},
            headers=auth_headers,
        )


async def test_audit_lists_supplier_mutations(auth_headers, session, client):
    await _seed_audit_rows(client, auth_headers)
    response = await client.get("/api/audit", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert all(row["entity_type"] == "supplier" for row in rows)
    assert all(row["action"] == "create" for row in rows)
    assert all(row["username"] == "admin" for row in rows)
    assert "changes_json" in rows[0]


async def test_audit_filters_by_entity_and_action(auth_headers, session, client):
    await _seed_audit_rows(client, auth_headers)

    by_type = await client.get("/api/audit?entity_type=book", headers=auth_headers)
    assert by_type.status_code == 200
    assert by_type.json() == []

    by_action = await client.get(
        "/api/audit?entity_type=supplier&action=update", headers=auth_headers
    )
    assert by_action.json() == []


async def test_audit_filters_by_user_and_date(auth_headers, session, client):
    await _seed_audit_rows(client, auth_headers)

    by_user = await client.get("/api/audit?username=admin", headers=auth_headers)
    assert by_user.status_code == 200
    assert len(by_user.json()) == 2

    by_user_miss = await client.get("/api/audit?username=ghost", headers=auth_headers)
    assert by_user_miss.json() == []

    in_range = await client.get(
        "/api/audit?start_date=2000-01-01&end_date=2999-12-31", headers=auth_headers
    )
    assert len(in_range.json()) == 2

    out_of_range = await client.get(
        "/api/audit?start_date=2000-01-01&end_date=2000-01-02", headers=auth_headers
    )
    assert out_of_range.json() == []


async def test_audit_paginated(auth_headers, session, client):
    await _seed_audit_rows(client, auth_headers)
    page1 = await client.get("/api/audit?page=1&page_size=1", headers=auth_headers)
    page2 = await client.get("/api/audit?page=2&page_size=1", headers=auth_headers)
    assert len(page1.json()) == 1
    assert len(page2.json()) == 1
    assert page1.json()[0]["id"] != page2.json()[0]["id"]


async def test_audit_non_admin_403(auth_headers, session, client):
    headers = await _cashier_headers(session)
    response = await client.get("/api/audit", headers=headers)
    assert response.status_code == 403


async def test_audit_requires_auth(client):
    assert (await client.get("/api/audit")).status_code == 401