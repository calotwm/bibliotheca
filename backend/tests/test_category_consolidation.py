"""Tests for the category-consolidation data migration (biography/essay -> No Ficción)."""

import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, text

from app.models import Base

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "c3d8a1f5b2e6_consolidate_categories.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "consolidate_categories", _MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration()


def _insert_book(conn, title, category_id):
    conn.execute(
        text(
            "INSERT INTO books (title, author, editorial, category_id, price, stock) "
            "VALUES (:t, 'Autor', 'Ed', :c, '10.00', 1)"
        ),
        {"t": title, "c": category_id},
    )


def _category_id(conn, name):
    return conn.execute(
        text("SELECT id FROM categories WHERE name = :n"), {"n": name}
    ).scalar()


def test_merge_moves_books_and_deletes_categories(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'consolidate.db'}")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        for name in ("No Ficción", "Biografía", "Ensayo", "Novela", "Teatro"):
            conn.execute(text("INSERT INTO categories (name) VALUES (:n)"), {"n": name})
        _insert_book(conn, "Bio Book", _category_id(conn, "Biografía"))
        _insert_book(conn, "Ensayo Book", _category_id(conn, "Ensayo"))
        _insert_book(conn, "Novela Book", _category_id(conn, "Novela"))

    with engine.begin() as conn:
        deleted = migration._merge_categories(conn)

    assert set(deleted) == {"Biografía", "Ensayo"}

    with engine.connect() as conn:
        names = {row[0] for row in conn.execute(text("SELECT name FROM categories"))}
        assert "Biografía" not in names
        assert "Ensayo" not in names
        assert "No Ficción" in names
        assert "Novela" in names

        target = _category_id(conn, "No Ficción")
        moved = {
            row[0]
            for row in conn.execute(
                text("SELECT title FROM books WHERE category_id = :c"), {"c": target}
            )
        }
        assert moved == {"Bio Book", "Ensayo Book"}
        # The unrelated category's book is untouched.
        assert _category_id(conn, "Novela") is not None


def test_merge_creates_no_ficcion_when_missing(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'consolidate2.db'}")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO categories (name) VALUES ('Ensayo')"))
        _insert_book(conn, "Ensayo Book", _category_id(conn, "Ensayo"))

    with engine.begin() as conn:
        migration._merge_categories(conn)

    with engine.connect() as conn:
        names = {row[0] for row in conn.execute(text("SELECT name FROM categories"))}
        assert "No Ficción" in names
        assert "Ensayo" not in names
        target = _category_id(conn, "No Ficción")
        moved = [
            row[0]
            for row in conn.execute(
                text("SELECT title FROM books WHERE category_id = :c"), {"c": target}
            )
        ]
        assert moved == ["Ensayo Book"]


def test_merge_idempotent_when_sources_missing(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'consolidate3.db'}")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO categories (name) VALUES ('No Ficción')"))

    with engine.begin() as conn:
        deleted = migration._merge_categories(conn)

    assert deleted == []
    with engine.connect() as conn:
        names = {row[0] for row in conn.execute(text("SELECT name FROM categories"))}
        assert names == {"No Ficción"}
