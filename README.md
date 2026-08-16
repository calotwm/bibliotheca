# Bibliotheca

Bookstore inventory & sales webapp (single-tenant). Replaces a manual Excel
inventory (1724 books, 6 sheets) with a web app: catalog management, POS sales,
editorial batch updates, distributors, reports, Excel import with preview, and
non-fiscal PDF invoices.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 async — PostgreSQL (`asyncpg`) in
  production, SQLite (`aiosqlite`) for tests/dev — with Alembic async
  migrations.
- **Frontend**: React 19 + Vite + TypeScript + Tailwind (landed in a later slice).

## Repository layout

```
backend/
  app/       # FastAPI application (config, db, models, routers, services)
  alembic/   # async migrations
  tests/     # pytest suite (pytest-asyncio + httpx)
frontend/    # React SPA (later slice)
```

## Backend setup

Requires Python 3.11+.

```powershell
cd backend
py -m pip install -r requirements.txt
```

Required environment variables (config fails fast if missing):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing key (HS256) |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowlist (never `*` with credentials) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Bootstrap admin credentials |
| `DATABASE_URL` | Async DSN (defaults to a local SQLite file) |

Run the server:

```powershell
py -m uvicorn app.main:app --reload
```

Run the tests:

```powershell
py -m pytest
```

Run migrations:

```powershell
py -m alembic upgrade head
```
