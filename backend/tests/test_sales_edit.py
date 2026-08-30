"""Integration tests for PATCH /api/sales/{sale_id} (sale header edit)."""

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


async def _create_sale(
    session, client, headers, *, seller="Cande", quantity=1
) -> tuple[dict, int]:
    book_id = await _seed_book(session, stock=5)
    response = await client.post(
        "/api/sales",
        json={"items": [{"book_id": book_id, "quantity": quantity}], "seller": seller},
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


async def test_edit_seller_and_payment(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers, seller="Cande")
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"seller": "Julieta", "payment_method": "Efectivo"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["seller"] == "Julieta"
    assert data["payment_method"] == "Efectivo"

    detail = await client.get(f"/api/sales/{sale_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["seller"] == "Julieta"
    assert detail.json()["payment_method"] == "Efectivo"

    logs = await _sale_logs(session, sale_id)
    updates = [log for log in logs if log.action == "update"]
    assert len(updates) == 1
    assert updates[0].changes_json["seller"] == {"old": "Cande", "new": "Julieta"}
    assert updates[0].changes_json["payment_method"] == {
        "old": None,
        "new": "Efectivo",
    }


async def test_edit_rejects_invalid_seller(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers)
    response = await client.patch(
        f"/api/sales/{created['id']}",
        json={"seller": "Eva"},
        headers=auth_headers,
    )
    assert response.status_code == 422


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
        "/api/sales/9999", json={"seller": "Cande"}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_edit_requires_auth(session, client):
    response = await client.patch("/api/sales/1", json={"seller": "Cande"})
    assert response.status_code == 401


async def test_edit_clears_seller_with_null(auth_headers, session, client):
    created, _ = await _create_sale(session, client, auth_headers, seller="Cande")
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}", json={"seller": None}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["seller"] is None

    detail = await client.get(f"/api/sales/{sale_id}", headers=auth_headers)
    assert detail.json()["seller"] is None

    logs = await _sale_logs(session, sale_id)
    updates = [log for log in logs if log.action == "update"]
    assert len(updates) == 1
    assert updates[0].changes_json["seller"] == {"old": "Cande", "new": None}


async def test_edit_does_not_change_total_items_or_date(auth_headers, session, client):
    created, book_id = await _create_sale(session, client, auth_headers, quantity=2)
    sale_id = created["id"]

    response = await client.patch(
        f"/api/sales/{sale_id}",
        json={"customer_name": "Ana", "seller": "Cande y Julieta"},
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