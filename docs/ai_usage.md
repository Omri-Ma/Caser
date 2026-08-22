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
