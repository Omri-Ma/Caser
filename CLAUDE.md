# MultiVendor Hub — Law Firm Multi-Tenant SaaS

## Project
A multi-tenant SaaS platform for law firms. Each law firm is a tenant with its own
subdomain, branding, and subscription plan. Built for an academic exercise (level 4
difficulty), swapped from the original e-commerce theme — same technical requirements
apply in full.

## Roles
- `super_admin` — cross-tenant visibility, sees all firms and platform-wide data
- `office_manager` (tenant admin) — manages lawyers/clients, branding, subscription, scoped to their own tenant only
- `lawyer` — manages assigned cases, uploads/downloads documents (including internal-only folders clients cannot see), logs work hours
- `client` — views/uploads/downloads only their own documents (client-visible folders only)

## Tech stack (do not substitute without asking)
- Backend: FastAPI, Pydantic v2, SQLAlchemy (ORM), Alembic (migrations)
- Database: MySQL, single shared database, indexes on all search/filter fields
  (email, subdomain, case status, etc.), not just primary/foreign keys
- Auth: JWT (access + refresh tokens), bcrypt or argon2 password hashing
- Cache: Redis — used for caching (tenant lookups, dashboard stats), not locking
- Frontend: React (or Next.js), two separate apps: `client/` (portal) and `admin/` (CMS)
- Infra: Docker Compose (app + db + redis), Nginx (subdomain routing / reverse proxy)
- Testing: pytest + httpx
- Logging: structured logging (e.g. `structlog`) instead of `print()` — always
  include `tenant_id` on request-scoped logs, it's essential for tracing isolation bugs
- Docs: FastAPI auto OpenAPI at `/docs`, exported Postman Collection in `docs/`

## Multi-tenancy architecture (core requirement — this is the graded core, do not deviate)
- Strategy: **shared database, row-level isolation**. Every tenant-scoped table has a
  `tenant_id` column. Every query touching tenant data MUST filter by `tenant_id`.
  Build one reusable dependency/helper that applies this filter automatically —
  don't hand-write the filter in every route.
- Tenant identification: by **subdomain** (e.g. `office1.myapp.com`), read from the
  `Host` header via a FastAPI dependency/middleware that resolves the tenant and
  injects `tenant_id` into request state. Required as specified — do not replace
  with path-based routing. Locally, test subdomains via `lvh.me`
  (e.g. `office1.lvh.me:8000`), which resolves any subdomain to localhost with
  zero config.
- JWT payload includes `user_id`, `tenant_id`, `role`, `exp`.
- `super_admin` is the only role allowed to query across tenants — this goes
  through a clearly separate, explicitly named code path (never the default
  tenant-filtered query functions), so it can't accidentally leak into normal
  user-facing queries.
- RBAC enforcement happens in BOTH backend (`Depends()` checks, mandatory) and
  frontend (route guards, UX only — never trust the frontend for real security).
- A pytest test proving tenant A cannot retrieve tenant B's data is required —
  write it early (Phase 1), not at the end.

## Data model
Create all tables now, including future add-on tables, even before their features
are built — avoids painful migrations later.

- `Tenants` (id, name, subdomain, plan, logo_url, primary_color, active)
- `Users` (id, tenant_id, name, email, password_hash, role)
- `Cases` (id, tenant_id, client_id, lawyer_id, title, status, created_at)
- `Documents` (id, tenant_id, case_id, uploaded_by, file_url, folder_type, visible_to)
  — `folder_type`: `client` or `internal`. This enforces "lawyers see internal
  folders, clients don't" — enforce in both the query layer and role checks.
- `Subscriptions` (id, tenant_id, plan, start_date, end_date, active)
  — plan is `free` / `pro` / `enterprise`. Keep enforcement simple: one reusable
  check (e.g. `check_plan_limit(tenant_id, resource_type)`) comparing a resource
  count against a hardcoded per-plan limit (e.g. number of lawyers). No billing
  or payment integration needed — this is a resource gate, not a commerce system.
- `Settings` (id, tenant_id, key, value)
- `WorkLogs` (id, tenant_id, lawyer_id, case_id, date, hours, description, source)
  — `source`: `manual` or `excel_import`
- `Narratives` (id, tenant_id, case_id, generated_text, total_hours, total_fee, created_at)
- `AuditLogs` (id, tenant_id, user_id, action, target, timestamp) — add-on feature

## Folder structure (do not restructure later — this is part of the grade)
```
/client        — client/lawyer-facing React app
/admin         — office manager / super admin CMS
/server        — FastAPI backend (routers, schemas, services, models, deps, core)
/db            — schema.sql, seed.sql, Alembic migrations
/docs          — architecture.png, ERD, openapi.json, postman_collection.json, ai_usage.md
docker-compose.yml
.env.example
README.md
```

## Architecture rules
- REST only between frontend and backend. No server-side template rendering,
  no SQL queries from the frontend, no business logic that exists only client-side
  — every rule enforced server-side too, frontend checks are UX convenience only.
- CORS: frontend and backend are fully separate apps — configure allowed origins
  explicitly in FastAPI from the start, or requests will fail immediately.
- Add a basic `/health` endpoint so Docker Compose (and the grader) can confirm
  the app actually started, not just that the container is running.
- All list endpoints (cases, documents, users, work logs) use pagination — never
  return an entire table in one response.
- All input validated via Pydantic schemas, never manual checks. All error
  responses share one consistent JSON shape across every endpoint
  (e.g. `{"error": "message", "field": "..."}`).
- Every frontend screen that fetches server data explicitly handles three states:
  Loading, Error, and Empty — not just the happy path.
- Frontend UI is RTL (Hebrew): `dir="rtl"` at the root, right-aligned text,
  navigation on the right, mirrored directional icons.
- Excel import (work logs): reject the whole file if any row fails validation,
  report which row and why, let the user fix and re-upload — no partial imports.
- File storage: local disk for now, behind a small storage abstraction
  (e.g. `save_file()` / `get_file_url()`) so swapping to cloud storage later
  only touches one module.
- Never hardcode secrets, passwords, or API keys — always `.env`, never
  committed. Every new `.env` variable is mirrored in `.env.example`
  (placeholder value, no real secrets).
- All code — variables, functions, comments — in English, even though the
  product domain and UI copy are Hebrew/RTL.

## Code quality: scalable and reusable by default
- Backend: shared logic (tenant filtering, auth checks, pagination, error
  responses, file upload handling) lives in shared utilities/dependencies —
  never copy-pasted per route file.
- Frontend: one reusable data-table component, one reusable form component, one
  reusable modal/dialog pattern, and one reusable "list → detail → edit"
  structure — configured per entity (lawyers, clients, cases, documents), not
  rebuilt per entity.
- Frontend: colors, spacing, and typography live as CSS variables / a design
  tokens file, not hardcoded per component — this doubles as the mechanism for
  per-tenant branding, so build it once and reuse it for both purposes.
- Favor composition over duplication: if a UI or logic pattern appears twice,
  extract it into a shared component/function before a third copy gets written.
- Keep naming, response shapes, and file/folder conventions consistent across
  the whole codebase.

## Build order — CORE FIRST, add-ons strictly after
Do not start any add-on feature until the core below is fully working and tested.

**Phase 1 — Skeleton (in order, before any feature work)**
1. Repo + folder structure + `.gitignore`
2. `docker-compose.yml` (app + MySQL + Redis) — must run cleanly with `docker-compose up`
3. Full schema + Alembic migration (all tables above, including add-on tables)
4. Auth: signup/login, JWT issuing, password hashing
5. Subdomain-resolution middleware + tenant injection
6. Role-based route protection (backend + frontend)
7. Tenant-isolation pytest test

**Phase 2 — Core features** (one vertical slice at a time: DB model → API route →
frontend form → verified working, before starting the next)
- Office manager: manage lawyers/clients, branding settings, subscription/plan view
- Lawyer: case list, document upload/download (client + internal folders), manual work log entry
- Client: view/upload/download own documents only
- Super admin: cross-tenant firm list and stats
- Admin CMS: full CRUD per entity, stats dashboard (recharts), data export

**Phase 3 — Add-ons** (only after Phase 1 + 2 are fully working and tested)
1. Excel import for work logs (pandas or openpyxl — confirm which is allowed)
2. Narrative generation engine (start with a fixed-template version)
3. PDF export of the narrative (reportlab or weasyprint)
4. Audit log for document access
5. Billable-hours dashboard chart
6. Search/filtering on cases and documents

## Git, documentation, and delivery requirements
- Meaningful commits at least once per work day — never one commit at the end.
- Feature branches, minimum 3 documented Pull Requests.
- Log AI usage as you go in `docs/ai_usage.md`: what was asked, what was
  changed, what was learned — do not reconstruct this retroactively.
- Keep `/docs` (OpenAPI export, Postman Collection, architecture diagram/ERD)
  updated as endpoints stabilize, not only at submission time.
- Two seed demo users always available for login: one regular client, one admin.
- README.md: install/run instructions, architecture explanation, demo user
  credentials, and screenshots — written progressively as features are
  finished, not reconstructed from memory at the end.

## Defense prep (30 min total) — keep in mind while building, not just before the defense
- 10 min live demo: full run end-to-end as both client and admin
- 10 min code dive: explain the core exercise (multi-tenancy/isolation) and one
  specific architecture decision in depth
- 10 min questions — expect: what happens with simultaneous requests from two
  users; where authorization is enforced (server/frontend/both — show it in
  code); what edge case you discovered mid-development; what you'd do
  differently with one more week
- AI use is allowed and encouraged, but every part of the code, project
  structure, state management, API, and edge-case handling must be explainable
  by you personally — don't let Claude Code write anything you can't explain
  afterward.
