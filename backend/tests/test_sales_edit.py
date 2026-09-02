"""Integration tests for PATCH /api/sales/{sale_id} (sale header edit)."""

from datetime import datetime

from sqlalchemy import select

from app.models import AuditLog, Book, Category, Sale, SaleItem


async def _category_id(session, name="Novela") -> int:
    existing = (
        await session.execute(select(Category).where(Category.name == name))
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


async def _seed_book(session, *, stock=5, price="10.00") -> int:
    cid = await _category_id(session)
    book = Book(
        title="Rayuela",
        author="Julio Cortázar",
        editorial="Sudamericana",
        category_id=cid,
        price=price,
        stock=stock,
    )
    session.add(book)
    await session.commit()
    return book.id


async def _create_sale(session, client, headers, *, quantity=1) -> tuple[dict, int]:
    book_id = await _seed_book(session, stock=5)
    response = await client.post(
        "/api/sales",
        json={"items": [{"book_id": book_id, "quantity": quantity}]},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json(), book_id


async def _sale_logs(session, sale_id):
    return (
        await session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "sale", AuditLog.entity_id == sale_id
            )
        )
    ).scalars().all()


async def test_edit_payment_and_customer(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"payment_method": "Efectivo", "customer_name": "Ana"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["payment_method"] == "Efectivo"
    assert data["customer_name"] == "Ana"

    detail = await client.get(f"/api/sales/{sale_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["payment_method"] == "Efectivo"
    assert detail.json()["customer_name"] == "Ana"

    logs = await _sale_logs(session, sale_id)
    updates = [log for log in logs if log.action == "update"]
    assert len(updates) == 1
    assert updates[0].changes_json["payment_method"] == {
        "old": None,
        "new": "Efectivo",
    }
    assert updates[0].changes_json["customer_name"] == {"old": None, "new": "Ana"}


async def test_edit_rejects_empty_body(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    response = await client.patch(f"/api/sales/{created['id']}", json={}, headers=auth_headers)
    assert response.status_code == 422

    # Unrelated-only fields are ignored, so no recognized field is present.
    response = await client.patch(
        f"/api/sales/{created['id']}", json={"items": []}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_edit_not_found(auth_headers, client):
    response = await client.patch(
        "/api/sales/9999", json={"payment_method": "Efectivo"}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_edit_requires_auth(session, client):
    response = await client.patch(
        "/api/sales/1", json={"payment_method": "Efectivo"}
    )
    assert response.status_code == 401


async def test_edit_clears_payment_with_null(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    sale_id = created["id"]

    # First set a payment method so the clear below is a real change.
    await client.patch(
        f"/api/sales/{sale_id}", json={"payment_method": "Efectivo"}, headers=auth_headers
    )

    response = await client.patch(
        f"/api/sales/{sale_id}", json={"payment_method": None}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["payment_method"] is None

    detail = await client.get(f"/api/sales/{sale_id}", headers=auth_headers)
    assert detail.json()["payment_method"] is None

    logs = await _sale_logs(session, sale_id)
    updates = [log for log in logs if log.action == "update"]
    assert len(updates) == 2
    assert updates[-1].changes_json["payment_method"] == {
        "old": "Efectivo",
        "new": None,
    }


async def test_edit_does_not_change_total_items_or_date(auth_headers, session, client):
    created, book_id = await _create_sale(session, client, auth_headers, quantity=2)
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"customer_name": "Ana", "customer_cuit": "20-12345678-9"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == created["total"]
    assert data["date"] == created["date"]
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["book_id"] == book_id
    assert item["quantity"] == 2
    assert item["unit_price"] == "10.00"
    assert item["subtotal"] == "20.00"

    rows = (
        await session.execute(select(SaleItem).where(SaleItem.sale_id == sale_id))
    ).scalars().all()
    assert len(rows) == 1
    sale = (await session.execute(select(Sale).where(Sale.id == sale_id))).scalar_one()
    assert str(sale.total) == "20.00"


async def test_edit_date(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"date": "2026-08-15T10:30:00"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["date"] == "2026-08-15T10:30:00"

    sale = (await session.execute(select(Sale).where(Sale.id == sale_id))).scalar_one()
    assert sale.date == datetime(2026, 8, 15, 10, 30, 0)


async def test_edit_shares_valid_pair(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    sale_id = created["id"]
    # Default split from a book with no observaciones is 85/15.
    assert created["juli_share"] == "85.00"
    assert created["cande_share"] == "15.00"

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"juli_share": 50, "cande_share": 50},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["juli_share"] == "50.00"
    assert response.json()["cande_share"] == "50.00"

    sale = (await session.execute(select(Sale).where(Sale.id == sale_id))).scalar_one()
    assert str(sale.juli_share) == "50.00"
    assert str(sale.cande_share) == "50.00"


async def test_edit_shares_accepts_0_100(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"juli_share": 0, "cande_share": 100},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["juli_share"] == "0.00"
    assert response.json()["cande_share"] == "100.00"


async def test_edit_rejects_single_share(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    response = await client.patch(
        f"/api/sales/{created['id']}",
        json={"juli_share": 50},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_edit_rejects_shares_not_summing_100(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    response = await client.patch(
        f"/api/sales/{created['id']}",
        json={"juli_share": 60, "cande_share": 50},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_edit_rejects_share_out_of_range(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    # Negative juli and >100 cande are both rejected by the 0..100 bounds.
    response = await client.patch(
        f"/api/sales/{created['id']}",
        json={"juli_share": -10, "cande_share": 110},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_edit_shares_leaves_other_fields_unchanged(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"juli_share": 50, "cande_share": 50},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == created["date"]
    assert data["payment_method"] is None
    assert data["customer_name"] is None
    assert data["customer_cuit"] is None


async def test_edit_rejects_null_date(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    response = await client.patch(
        f"/api/sales/{created['id']}",
        json={"date": None},
        headers=auth_headers,
    )
    assert response.status_code == 422
