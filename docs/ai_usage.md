# AI Usage Log

Logged as work happens, per project convention — not reconstructed retroactively.

## 2026-08-19

**Asked**: Read and analyze CLAUDE.md, recommend how to work and how to start.

**Changed**:
- Initialized git repo.
- Created folder structure: `client/`, `admin/`, `server/{routers,schemas,services,models,deps,core,tests}/`,
  `db/migrations/versions/`, `docs/`.
- Added `.gitignore`, `.env.example` (DB/Redis/JWT/CORS/storage/base-domain vars),
  root `README.md` skeleton.

**Learned / decided**:
- Frontend: plain React (Vite), not Next.js — the app is login-gated/users-only
  with no public/SEO pages, so Next's SSR/server layer would add a second runtime
  server for no benefit and cut against the doc's "REST only, no server-side
  rendering" rule.
- Tooling: npm + pip/venv over pnpm/Poetry — doc doesn't mandate either, npm/pip
  need nothing extra installed.
- Local machine is missing a real Python install (only the Windows Store stub
  alias is on PATH) and Docker — both needed before Phase 1 steps 2 (docker-compose)
  and 4 (running FastAPI) can actually be executed/tested, not just written.

## 2026-08-22

**Asked**: Set up local dev environment (Python, Docker Desktop, MySQL GUI), then
Phase 1 step 2 — docker-compose.yml with app + MySQL + Redis and a minimal FastAPI
skeleton with `/health`.

**Changed**:
- Installed Python 3.14.7, Docker Desktop (required enabling the "Virtual Machine
  Platform" and "Windows Subsystem for Linux" Windows features first), DBeaver.
- Added `server/main.py` (FastAPI app, CORS configured from `CORS_ORIGINS` env var,
  `/health` route), `server/requirements.txt` (fastapi, uvicorn, python-dotenv),
  `server/Dockerfile` (python:3.12-slim base), `server/.dockerignore`.
- Added root `docker-compose.yml`: `db` (mysql:8.0, healthcheck via mysqladmin
  ping), `redis` (redis:7-alpine), `app` (built from `server/Dockerfile`, depends
  on db being healthy).
- Added `MYSQL_ROOT_PASSWORD` to `.env.example` (needed by the mysql image/healthcheck).
- Verified: `docker compose up -d --build` starts all 3 containers, MySQL reports
  `(healthy)`, `GET /health` returns `{"status":"ok"}`.

**Learned / decided**:
- Container's Python is pinned to 3.12-slim, independent of the host's 3.14 install
  — the two don't need to match, and 3.12 is a safer/more-tested target for the
  FastAPI/SQLAlchemy/Alembic ecosystem than a just-released Python version.
- Docker Desktop on this Windows 11 machine needed WSL2 prerequisites enabled
  manually via Settings > "Turn Windows features on or off" before the engine
  would start, even though BIOS-level virtualization was already on.

**Also 2026-08-22 — Phase 1 step 3**: full schema as SQLAlchemy models + Alembic migration.

**Changed**:
- Added `server/core/database.py` (engine/session/`Base`, reads `DATABASE_URL`) and
  `server/models/` — one file per table: `tenant.py`, `user.py`, `case.py`,
  `document.py`, `subscription.py`, `setting.py`, `work_log.py`, `narrative.py`,
  `audit_log.py`, plus shared `enums.py` (UserRole, Plan, DocumentFolderType,
  WorkLogSource). Every tenant-scoped table has an indexed `tenant_id` FK.
- Added `sqlalchemy`, `alembic`, `pymysql`, `cryptography` to `server/requirements.txt`.
- Created a local venv (`.venv/`, gitignored) and installed backend deps into it —
  needed to run Alembic directly from Windows against the MySQL container.
- Scaffolded Alembic (`alembic.ini` at repo root, `db/migrations/` for env.py +
  versioned scripts, per CLAUDE.md's folder layout). Edited `env.py` to add
  `server/` to `sys.path` (so it imports models the same way the app does) and to
  use `DATABASE_URL_LOCAL` instead of `DATABASE_URL`.
- Added `DATABASE_URL_LOCAL` to `.env`/`.env.example` — same DB, but with hostname
  `localhost` instead of `db`, since Alembic runs on the host, not inside Docker.
- Generated and applied the initial migration (`db/migrations/versions/58ccfaf49fbc_create_initial_schema.py`).
- Added `db/schema.sql` as a readable snapshot of the live schema.
- Verified: `SHOW TABLES` inside the `db` container lists all 9 tables plus
  Alembic's own `alembic_version` bookkeeping table.

**Learned / decided**:
- Alembic runs from the host (via the new local venv) rather than inside the `app`
  container — avoids needing to mount `db/` into the container or restructure the
  Docker build, and reuses the Python install already set up. This is why two
  separate DB URLs exist (`DATABASE_URL` for the app container, `DATABASE_URL_LOCAL`
  for host-run tools) — `db` as a hostname only resolves inside Docker's network.
- Seed data (`db/seed.sql`, the two required demo users) is deliberately deferred to
  Phase 1 step 4 (auth) — a real seed needs bcrypt/argon2-hashed passwords, which
  don't exist yet; seeding now would mean fake/wrong password hashes.

**Also 2026-08-22 — renamed the project.**

**Asked**: Rename the project away from "MultiVendor Hub" (the leftover name from the
original e-commerce assignment template CLAUDE.md was adapted from) to something
that actually fits a law-firm SaaS product.

**Changed**:
- Renamed to **CaseHub** everywhere: `CLAUDE.md` and `README.md` titles, the FastAPI
  app title in `server/main.py`, the MySQL database name (`multivendor_hub` →
  `casehub`) in `.env`/`.env.example`, and `db/schema.sql`'s header comment.
- Since the database name is baked into the MySQL container's data volume at first
  boot, renaming it meant `docker compose down -v` (safe — no real data existed yet,
  just empty tables from the schema step) followed by `docker compose up -d --build`
  to reinitialize under the new name, then re-running the existing Alembic migration
  against the fresh `casehub` database.
- Verified: all 9 tables exist under `casehub`, `/health` still responds correctly.
