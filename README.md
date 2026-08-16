# Bibliotheca

Bookstore inventory & sales webapp (single-tenant). Replaces a manual Excel
inventory (1724 books, 6 sheets) with a web app: catalog management, POS sales,
editorial batch updates, distributors, reports, Excel import with preview, and
non-fiscal PDF invoices.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 async — PostgreSQL (`asyncpg`) in
  production, SQLite (`aiosqlite`) for tests/dev — with Alembic async
  migrations.
- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS v4, TanStack Query
  for server state, React Router 7, vitest + React Testing Library.

## Repository layout

```
backend/
  app/       # FastAPI application (config, db, models, routers, services)
  alembic/   # async migrations
  tests/     # pytest suite (pytest-asyncio + httpx)
frontend/
  src/       # React SPA (auth, api hooks, components, pages)
  tests      # vitest suite (@testing-library/react)
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

### Serving the built SPA

When `frontend/dist` exists (a fresh `npm run build`), the backend serves it
directly: `/api/**` and `/health` keep priority, static assets are served from
`frontend/dist/assets`, and any other GET falls back to `index.html` so
client-side routes (e.g. `/inventario`) resolve to the SPA. Without a build the
backend starts fine and serves only the API (fresh-clone safe).

## Frontend setup

Requires Node 22+ and npm 10+.

```powershell
cd frontend
npm install
```

Run the dev server (proxies `/api` → `http://localhost:8000`):

```powershell
npm run dev
```

Build the production bundle (typecheck with `tsc -b`, then `vite build`):

```powershell
npm run build
```

Run the tests:

```powershell
npm run test
```