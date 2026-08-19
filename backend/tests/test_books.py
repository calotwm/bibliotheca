"""Integration tests for book catalog endpoints."""

from decimal import Decimal

from sqlalchemy import select

from app.models import AuditLog, Book, Category, User
from app.security.jwt import create_access_token
from app.security.password import hash_password


async def _category_id(session, name="Novela") -> int:
    category = Category(name=name)
    session.add(category)
    await session.commit()
    return category.id


def _book_payload(category_id: int, **overrides) -> dict:
    payload = {
        "title": "Rayuela",
        "author": "Julio Cortázar",
        "editorial": "Sudamericana",
        "category_id": category_id,
        "price": "12.50",
        "stock": 3,
    }
    payload.update(overrides)
    return payload


async def test_create_book(auth_headers, session, client):
    cid = await _category_id(session)
    response = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Rayuela"
    assert data["stock_status"] == "In Stock"
    assert data["category_name"] == "Novela"


async def test_create_book_requires_auth(client):
    response = await client.post(
        "/api/books", json=_book_payload(1)
    )
    assert response.status_code == 401


async def test_get_book(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]
    response = await client.get(f"/api/books/{book_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == book_id


async def test_get_book_not_found(auth_headers, client):
    response = await client.get("/api/books/9999", headers=auth_headers)
    assert response.status_code == 404


async def test_update_book(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]
    response = await client.put(
        f"/api/books/{book_id}",
        json={"stock": 10, "price": "15.00"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["stock"] == 10
    assert response.json()["stock_status"] == "In Stock"


async def test_update_book_not_found(auth_headers, client):
    response = await client.put(
        "/api/books/9999", json={"stock": 5}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_natural_key_upsert_same_key(auth_headers, session, client):
    cid = await _category_id(session)
    first = await client.post(
        "/api/books", json=_book_payload(cid, price="10.00"), headers=auth_headers
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/books", json=_book_payload(cid, price="20.00"), headers=auth_headers
    )
    assert second.status_code == 200
    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].price == Decimal("20.00")


async def test_natural_key_upsert_case_insensitive(auth_headers, session, client):
    cid = await _category_id(session)
    await client.post(
        "/api/books", json=_book_payload(cid, title="Rayuela"), headers=auth_headers
    )
    second = await client.post(
        "/api/books",
        json=_book_payload(cid, title="  rayuela  ", price="20.00"),
        headers=auth_headers,
    )
    assert second.status_code == 200
    books = (await session.execute(select(Book))).scalars().all()
    assert len(books) == 1
    assert books[0].price == Decimal("20.00")


async def test_list_books_filters(auth_headers, session, client):
    novela = await _category_id(session, "Novela")
    poesia = await _category_id(session, "Poesía")
    await client.post(
        "/api/books", json=_book_payload(novela, title="Rayuela", stock=0), headers=auth_headers
    )
    await client.post(
        "/api/books",
        json=_book_payload(poesia, title="Ficciones", author="Borges", stock=10),
        headers=auth_headers,
    )

    by_category = await client.get(
        f"/api/books?category_id={novela}", headers=auth_headers
    )
    assert len(by_category.json()) == 1
    assert by_category.json()[0]["title"] == "Rayuela"

    by_search = await client.get("/api/books?q=bor", headers=auth_headers)
    assert len(by_search.json()) == 1
    assert by_search.json()[0]["title"] == "Ficciones"

    by_status = await client.get("/api/books?stock_status=Out", headers=auth_headers)
    assert len(by_status.json()) == 1
    assert by_status.json()[0]["title"] == "Rayuela"


async def test_list_books_title_filter(auth_headers, session, client):
    novela = await _category_id(session, "Novela")
    poesia = await _category_id(session, "Poesía")
    await client.post(
        "/api/books", json=_book_payload(novela, title="Rayuela"), headers=auth_headers
    )
    await client.post(
        "/api/books",
        json=_book_payload(poesia, title="Rayuela de los sueños"),
        headers=auth_headers,
    )
    await client.post(
        "/api/books",
        json=_book_payload(poesia, title="Ficciones", author="Borges"),
        headers=auth_headers,
    )

    by_title = await client.get("/api/books?title=ray", headers=auth_headers)
    titles = [book["title"] for book in by_title.json()]
    assert sorted(titles) == ["Rayuela", "Rayuela de los sueños"]

    by_title = await client.get("/api/books?title=Ficciones", headers=auth_headers)
    assert len(by_title.json()) == 1
    assert by_title.json()[0]["title"] == "Ficciones"


async def test_list_books_title_combined_with_author_and_editorial(
    auth_headers, session, client
):
    novela = await _category_id(session, "Novela")
    await client.post(
        "/api/books",
        json=_book_payload(novela, title="Rayuela", author="Julio Cortázar",
                           editorial="Sudamericana"),
        headers=auth_headers,
    )
    await client.post(
        "/api/books",
        json=_book_payload(novela, title="Rayuela", author="Julio Cortázar",
                           editorial="Planeta"),
        headers=auth_headers,
    )
    await client.post(
        "/api/books",
        json=_book_payload(novela, title="Rayuela", author="Otro Autor",
                           editorial="Sudamericana"),
        headers=auth_headers,
    )

    # Pick an editorial, then narrow by author within it.
    url = "/api/books?title=rayuela&author=cort%C3%A1zar&editorial=sudamericana"
    response = await client.get(url, headers=auth_headers)
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["editorial"] == "Sudamericana"
    assert result[0]["author"] == "Julio Cortázar"


async def test_list_books_low_stock_returns_empty(auth_headers, session, client):
    novela = await _category_id(session, "Novela")
    await client.post(
        "/api/books", json=_book_payload(novela, title="A", stock=1), headers=auth_headers
    )
    await client.post(
        "/api/books", json=_book_payload(novela, title="B", stock=5), headers=auth_headers
    )

    # Old clients asking for "Low" get an empty result (never 400).
    response = await client.get("/api/books?stock_status=Low", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_books_in_stock_includes_single_unit(auth_headers, session, client):
    novela = await _category_id(session, "Novela")
    await client.post(
        "/api/books", json=_book_payload(novela, title="SoloUno", stock=1),
        headers=auth_headers,
    )
    await client.post(
        "/api/books", json=_book_payload(novela, title="Vacio", stock=0),
        headers=auth_headers,
    )

    response = await client.get("/api/books?stock_status=In%20Stock", headers=auth_headers)
    titles = [book["title"] for book in response.json()]
    assert titles == ["SoloUno"]


async def test_soft_delete_hides_from_list(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]

    deleted = await client.delete(f"/api/books/{book_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listing = await client.get("/api/books", headers=auth_headers)
    assert all(b["id"] != book_id for b in listing.json())

    # row is preserved (soft-delete), only is_active flipped
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one()
    assert book.is_active is False


async def test_soft_delete_requires_admin(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]

    session.add(User(username="cashier", password_hash=hash_password("c"), role="cashier"))
    await session.commit()
    cashier_token = create_access_token("cashier", "cashier")

    response = await client.delete(
        f"/api/books/{book_id}",
        headers={"Authorization": f"Bearer {cashier_token}"},
    )
    assert response.status_code == 403


async def test_negative_price_rejected(auth_headers, session, client):
    cid = await _category_id(session)
    response = await client.post(
        "/api/books", json=_book_payload(cid, price="-1.00"), headers=auth_headers
    )
    assert response.status_code == 422


async def test_negative_stock_rejected(auth_headers, session, client):
    cid = await _category_id(session)
    response = await client.post(
        "/api/books", json=_book_payload(cid, stock=-1), headers=auth_headers
    )
    assert response.status_code == 422


async def test_audit_logged_on_book_create(auth_headers, session, client):
    cid = await _category_id(session)
    await client.post("/api/books", json=_book_payload(cid), headers=auth_headers)
    logs = (await session.execute(select(AuditLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].entity_type == "book"
    assert logs[0].action == "create"


async def test_audit_logged_on_book_update(auth_headers, session, client):
    cid = await _category_id(session)
    created = await client.post(
        "/api/books", json=_book_payload(cid), headers=auth_headers
    )
    book_id = created.json()["id"]
    await client.put(f"/api/books/{book_id}", json={"stock": 7}, headers=auth_headers)
    logs = (
        await session.execute(select(AuditLog).where(AuditLog.action == "update"))
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].changes_json["stock"] == {"old": "3", "new": "7"}


async def _seed_sort_books(auth_headers, session, client):
    novela = await _category_id(session, "Novela")
    poesia = await _category_id(session, "Poesía")
    await client.post(
        "/api/books",
        json=_book_payload(novela, title="Zorro", author="Ana", editorial="Beta",
                           price="10.00", stock=5),
        headers=auth_headers,
    )
    await client.post(
        "/api/books",
        json=_book_payload(poesia, title="Amor", author="Bruno", editorial="Alfa",
                           price="2.00", stock=1),
        headers=auth_headers,
    )
    await client.post(
        "/api/books",
        json=_book_payload(novela, title="Casa", author="Carla", editorial="Gamma",
                           price="15.00", stock=0),
        headers=auth_headers,
    )
    return novela, poesia


async def test_list_books_sort_title_asc_and_desc(auth_headers, session, client):
    await _seed_sort_books(auth_headers, session, client)
    asc = await client.get("/api/books?sort_by=title", headers=auth_headers)
    assert [b["title"] for b in asc.json()] == ["Amor", "Casa", "Zorro"]
    desc = await client.get("/api/books?sort_by=title&sort_dir=desc", headers=auth_headers)
    assert [b["title"] for b in desc.json()] == ["Zorro", "Casa", "Amor"]


async def test_list_books_sort_author_and_editorial(auth_headers, session, client):
    await _seed_sort_books(auth_headers, session, client)
    by_author = await client.get("/api/books?sort_by=author", headers=auth_headers)
    assert [b["author"] for b in by_author.json()] == ["Ana", "Bruno", "Carla"]
    by_editorial = await client.get("/api/books?sort_by=editorial", headers=auth_headers)
    assert [b["editorial"] for b in by_editorial.json()] == ["Alfa", "Beta", "Gamma"]


async def test_list_books_sort_price_numeric(auth_headers, session, client):
    await _seed_sort_books(auth_headers, session, client)
    response = await client.get("/api/books?sort_by=price", headers=auth_headers)
    # Numeric ordering: 2 before 10 (lexicographic would put 10 first).
    assert [b["title"] for b in response.json()] == ["Amor", "Zorro", "Casa"]


async def test_list_books_sort_stock_desc(auth_headers, session, client):
    await _seed_sort_books(auth_headers, session, client)
    response = await client.get("/api/books?sort_by=stock&sort_dir=desc", headers=auth_headers)
    assert [b["stock"] for b in response.json()] == [5, 1, 0]


async def test_list_books_sort_invalid_sort_by(auth_headers, session, client):
    response = await client.get("/api/books?sort_by=isbn", headers=auth_headers)
    assert response.status_code == 400
    assert "title" in response.json()["detail"]


async def test_list_books_sort_invalid_sort_dir(auth_headers, session, client):
    response = await client.get("/api/books?sort_by=title&sort_dir=sideways", headers=auth_headers)
    assert response.status_code == 400
    assert "sort_dir" in response.json()["detail"]


async def test_list_books_sort_combined_with_filter(auth_headers, session, client):
    await _seed_sort_books(auth_headers, session, client)
    # Filter by editorial, then sort by price numerically.
    response = await client.get(
        "/api/books?editorial=beta&sort_by=price&sort_dir=asc", headers=auth_headers
    )
    assert response.status_code == 200
    assert [b["title"] for b in response.json()] == ["Zorro"]
