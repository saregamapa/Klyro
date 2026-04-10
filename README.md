# KlyroAI

Production-oriented monorepo starter for a **SiteGPT-like chatbot builder**: **FastAPI** backend, **HTML + Tailwind CSS + vanilla JS** frontend, with the UI served from the same process via static files and Jinja2 templates.

## Layout

```text
/backend
  /app
    /api        # HTTP routers (versioned under /api/v1/…)
    /core       # Settings, JWT/bcrypt helpers (security.py)
    /db         # SQLite connection helper + schema init (raw SQL)
    /models     # Domain types (optional; persistence is SQL + repos)
    /repositories  # Raw SQL data access (users, chatbots, conversations, leads)
    /schemas    # Pydantic request/response schemas
    /services   # Business logic
    /utils      # Small shared helpers
  main.py       # ASGI app for uvicorn: `main:app`
  database.db   # Created at runtime (see DATABASE_PATH; gitignored by default)
/frontend
  /static       # CSS, JS, images (mounted at /static)
  /templates    # Jinja2 HTML templates
```

## Prerequisites

- Python 3.11+ recommended
- A virtual environment (optional but recommended)

## Setup

1. Copy environment defaults (repo root or `backend/` — both are loaded if present):

   ```bash
   cp .env.example .env
   # optional: cp .env backend/.env
   ```

2. Create a venv and install dependencies **from the repo root**:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Ensure paths in `.env` match your machine. Defaults assume you run uvicorn with `backend` as the working directory and use `../frontend/static` and `../frontend/templates`.

## Run the API + UI

From the **`backend`** directory (so `main:app` and `.env` resolve correctly):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health JSON:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **OpenAPI docs** (only when `DEBUG=true` in `.env`): [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

## Environment variables

See `.env.example`. `pydantic-settings` loads, in order: `backend/.env`, then the monorepo root `.env`. Use absolute paths for `FRONTEND_STATIC_DIR` / `FRONTEND_TEMPLATES_DIR` if your working directory differs.

## Database (SQLite)

- Default file: **`database.db`** under `backend/` (`DATABASE_PATH` in `.env`).
- **No ORM:** `sqlite3` with parameterized SQL in `app/repositories/`.
- **Schema:** `app/db/init_db.py` runs on application startup (`lifespan`) and uses `CREATE TABLE IF NOT EXISTS` plus foreign keys (`PRAGMA foreign_keys = ON` on each connection).
- **Requests:** routes depend on `DbConn` (`app/api/deps.py`), which yields a connection per request, commits on success, and rolls back on errors.

Example API (all under `/api/v1`):

| Method | Path | Auth | Purpose |
|--------|------|------|--------|
| POST | `/signup` | No | Register (`email`, `password`); bcrypt hash stored in SQLite |
| POST | `/login` | No | Returns `{ "access_token", "token_type": "bearer" }` (JWT) |
| GET | `/users/me` | Bearer | Current user profile |
| POST | `/chatbots` | Bearer | Create chatbot (`name`, `website_url`) for JWT user |
| GET | `/chatbots` | Bearer | List caller’s chatbots |
| GET | `/chatbots/{id}` | Bearer | Get chatbot if owned |
| DELETE | `/chatbots/{id}` | Bearer | Delete if owned (cascades) |
| POST | `/chatbots/{id}/conversations` | Bearer | Save turn (owner only) |
| GET | `/chatbots/{id}/conversations` | Bearer | List turns (owner only) |
| POST | `/chatbots/{id}/leads` | Bearer | Capture lead (owner only) |

Send `Authorization: Bearer <access_token>` on protected routes. `CurrentUser` / `get_current_user` live in `app/api/deps.py`.

## Next steps for a real SaaS

- Add refresh tokens, password reset, and rate limiting on `/login` / `/signup`.
- Swap SQLite for PostgreSQL by introducing a small DB adapter while keeping the repository function signatures stable.
- Move Tailwind to a build step (CLI or PostCSS) for production; the starter uses the CDN for zero-config dev.
- Add CI, Docker, and structured logging as you harden the stack.

## License

Use and modify for your product as needed.
