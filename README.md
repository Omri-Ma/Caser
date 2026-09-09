# CaseHub — Law Firm Multi-Tenant SaaS

A multi-tenant SaaS platform for law firms. Each law firm is a tenant with its own
subdomain, branding, and subscription plan.

> Status: Phase 1 (auth/tenancy foundation) done; Phase 2 in progress — Cases
> backend slice done, frontend auth shell done (register/login/signup screens,
> no Cases UI yet). This README is updated progressively as features land, per
> project convention — not reconstructed at the end.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Alembic, MySQL (shared DB, row-level tenant
  isolation via `tenant_id` on every tenant-scoped table), Redis for caching.
- **Frontend**: two separate React (Vite) apps — `client/` (lawyer + client portal)
  and `admin/` (office manager + super admin CMS).
- **Tenancy**: identified by subdomain (`office1.lvh.me`), resolved by a FastAPI
  middleware/dependency that injects `tenant_id` into request state. Every
  tenant-scoped query goes through one reusable filtering dependency.
- **Auth**: JWT (access + refresh), bcrypt/argon2 password hashing, RBAC enforced
  server-side (frontend route guards are UX only).

See `/docs` for the ERD, OpenAPI export, and Postman collection — all three are
generated, not hand-maintained (see "Regenerating /docs" below), and are
refreshed whenever routes or models change.

## Install & run

Prerequisites: Docker Desktop, Node.js 18+.

1. Copy `.env.example` to `.env` (and `client/.env.example` → `client/.env`,
   `admin/.env.example` → `admin/.env`) — defaults work as-is for local dev.
2. Start the backend + database + cache:
   ```
   docker-compose up -d
   ```
   This runs `client_api` on port 8000, `admin_api` on port 8001, MySQL, and
   Redis. Check both are up: `curl http://lvh.me:8000/health` and
   `curl http://lvh.me:8001/health`.
3. Apply the schema (first time only) and seed data:
   ```
   alembic upgrade head
   docker exec -i <mysql-container> mysql -u app_user -p casehub < db/seed.sql
   ```
4. Start the two frontends (separate terminals):
   ```
   cd client && npm install && npm run dev   # http://<subdomain>.lvh.me:5173
   cd admin  && npm install && npm run dev   # http://<subdomain>.lvh.me:5174
   ```
   `lvh.me` resolves any subdomain to `127.0.0.1`, so no `/etc/hosts` editing
   is needed. Both apps must be opened at a real tenant subdomain (e.g.
   `office1.lvh.me:5173`), not bare `localhost` — that's what makes the
   session cookie and CORS both work (see `CLAUDE.md`'s Multi-tenancy
   architecture section).
5. To found a new firm: open `http://<subdomain>.lvh.me:5174/signup` (any
   subdomain not already taken). To use an existing firm, use the demo users
   below at `demo.lvh.me`.

## Demo users

Seeded via `db/seed.sql`, attached to a dedicated `demo` tenant:

| Role           | App                          | URL                         | Email                              | Password           |
|----------------|-------------------------------|-----------------------------|-------------------------------------|--------------------|
| office_manager | admin (CMS)                   | `demo.lvh.me:5174/login`    | `office_manager@casehub.example.com` | `OfficeManager123!` |
| client         | client (portal)                | `demo.lvh.me:5173/login`    | `client@casehub.example.com`         | `Client123!`        |

Plus the `super_admin` bootstrap account (platform-only, not one of the two
required demo users): `super@casehub.example.com` / `SuperAdmin123!`, logs in
at `platform.lvh.me:5174/login` — the cross-tenant firm list and
platform-wide stats dashboard (suspend/reactivate a firm from there too).

## Regenerating /docs

`docs/openapi_client.json`, `docs/openapi_admin.json`, `docs/postman_collection_client.json`,
`docs/postman_collection_admin.json`, `docs/erd.png`, and `docs/erd.mmd.md` are
all generated from code (route declarations and `server/shared/models`), never
edited by hand. Re-run this after any change to routes or table/relationship
definitions:

```
# one-time setup
server/.venv/Scripts/python.exe -m pip install -r server/requirements.txt -r server/scripts/requirements-docs.txt
# (Node/npm on PATH is also required — used via npx for the Postman conversion)

# every time routes or models change
bash server/scripts/export_docs.sh
```

This runs three independent scripts in order (each can also be run alone):
- `server/scripts/export_openapi.py` — imports the `client_api`/`admin_api`
  FastAPI app objects directly and calls `.openapi()`; no server needs to be
  running, no Docker needed.
- `server/scripts/generate_erd.py` — imports `shared.models` and feeds
  `Base.metadata` to `eralchemy2`, which reads the real `ForeignKey`
  constraints; also no DB connection needed.
- `server/scripts/generate_postman.sh` — converts the two OpenAPI files above
  into Postman collections via Postman's own `openapi-to-postmanv2` CLI (via
  `npx`, pinned version).

Review the diff under `docs/` and commit the results like any other
generated-but-tracked artifact.

## Screenshots

_Added as UI screens are completed._
