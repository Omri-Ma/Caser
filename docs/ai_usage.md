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

## 2026-08-25

**Asked**: Document two pending guidance items in CLAUDE.md (supporting-library
policy from the tutor, public firm homepage feature), then Phase 1 step 4 — auth
(signup/login, JWT issuing, password hashing).

**Changed**:
- Committed the two pending `CLAUDE.md` edits (library guidance note under Tech
  stack, "Public firm homepage" bullet under Phase 2).
- Added `bcrypt`, `pyjwt`, `email-validator` to `server/requirements.txt`.
- Added `server/core/security.py` (bcrypt password hashing, JWT access/refresh
  token creation and decoding).
- Added `server/core/tenant.py` — `get_current_tenant` dependency that resolves
  the tenant from the subdomain in the `Host` header (e.g. `acme.lvh.me` ->
  subdomain `acme`), 404s on unknown/inactive tenant, 400s if no subdomain is
  present. This is CLAUDE.md's Phase 1 step 5, pulled forward into this step
  because login cannot work without it — user emails are only unique
  per-tenant (`UniqueConstraint(tenant_id, email)` on `users`), so login needs
  to know the tenant before it can look up the user.
- Added `server/core/errors.py` — global exception handlers so every error
  response (validation errors and raised `HTTPException`s alike) shares the
  same `{"error": ..., "field": ...}` JSON shape, per CLAUDE.md's API
  consistency rule.
- Added `server/schemas/auth.py` (`SignupRequest`, `LoginRequest`,
  `RefreshRequest`, `TokenResponse` Pydantic schemas) and
  `server/routers/auth.py` (`POST /auth/signup`, `POST /auth/login`,
  `POST /auth/refresh`), wired into `server/main.py`.
- Verified via curl: signup creates a `Tenant` + first `office_manager` `User`
  and returns a token pair; login at `acme.lvh.me:8000` succeeds with correct
  credentials and returns `401` on wrong password; login at an unknown or
  missing subdomain returns `404`/`400` respectively; duplicate subdomain
  signup returns `400`; refresh token issues a new token pair; `password_hash`
  in the DB is a bcrypt hash, never the plaintext password.

**Learned / decided**:
- `signup` registers a **new tenant** (law firm) plus its first
  `office_manager` account, not a generic "any role" signup — lawyer and
  client accounts are created later by the office manager through the admin
  CMS (Phase 2), matching how CLAUDE.md describes the roles. This means
  `/auth/signup` doesn't require a subdomain (it's creating one), while
  `/auth/login` does.
- Used `bcrypt` and `pyjwt` directly rather than `passlib`/`python-jose` —
  both are simpler, actively maintained, and avoid version-compatibility
  issues those wrapper libraries have had with newer bcrypt/JWT releases.
- Seed data (`db/seed.sql`) can now be written with real bcrypt hashes, since
  password hashing exists — still pending, deferred to when Phase 1 wraps up.

**Also 2026-08-26 — restructured Users into Identities + Memberships.**

**Asked**: A discussion starting from "why does login need a subdomain, why
can't a client see all their cases across firms in one dashboard" led to
designing and building a global-identity model: one login per person,
attachable to multiple firms, with an office manager able to add an existing
person to their firm by email instead of creating a new password for them.

**Changed**:
- Replaced `models/user.py` (`Users`, `tenant_id` + `role` baked in) with
  `models/identity.py` (`Identities` — just name/email/password_hash, no
  tenant) and `models/membership.py` (`Memberships` — `identity_id`,
  `tenant_id`, `role`, unique together). Updated `Cases.client_id`/`lawyer_id`,
  `Documents.uploaded_by`, `WorkLogs.lawyer_id`, `AuditLogs.user_id` to
  reference `memberships.id` instead of `users.id`.
- Switched sessions from a Bearer JWT returned in the response body (stored
  client-side in localStorage) to an httponly cookie scoped to the whole base
  domain (`Domain=.lvh.me`) — localStorage is locked to one origin and can't
  be shared across tenant subdomains, cookies with a parent-domain scope can.
  Added `COOKIE_SECURE` env var (false for local http dev, must be true in
  production over https).
- The JWT itself now only carries `identity_id` + `exp` — no more `tenant_id`/
  `role` baked in, since the same identity can have a different role at a
  different firm. Added `core/identity.py` (`get_current_identity` — reads
  the cookie, resolves who's logged in) and `core/membership.py`
  (`get_current_membership` — resolves their role at *this* tenant by
  joining `Memberships`, fresh on every request; also `require_role()`, a
  small RBAC dependency factory used to guard office-manager-only routes).
- Rewrote `routers/auth.py`: added `POST /auth/register` (bare identity, no
  firm — for a lawyer/client to create their account before being added to
  one), `POST /auth/logout`, `GET /auth/me`; `signup`/`login`/`refresh` now
  set/read cookies instead of returning tokens in the JSON body.
- Added `routers/members.py` — `POST /members`, office-manager-only (via
  `require_role`), looks up an existing `Identity` by email and creates a
  `Membership` for the current tenant. 404s if no account exists with that
  email (MVP policy: the person must already have registered — no
  invite-for-a-nonexistent-account flow, to keep scope contained).
- Deleted and regenerated the Alembic migration from scratch (no real data
  existed yet, only test rows from developing/testing auth) — `docker compose
  down -v` to reset the DB volume, then a fresh `alembic revision
  --autogenerate`. Regenerated `db/schema.sql` to match.
- Updated `CLAUDE.md`'s Data model and Multi-tenancy architecture sections to
  describe `Identities`/`Memberships` instead of `Users`, and the
  cookie-based session instead of a token with `tenant_id`/`role` baked in —
  this is a real, deliberate deviation from the originally-specified `Users`
  table, so the doc needed to match the code, not just the code match the doc.
- Verified via curl end-to-end with a shared cookie jar: register a bare
  identity; sign up a new firm (sets cookie); `GET /auth/me` succeeds from a
  *different* subdomain using the same cookie (proves the cross-subdomain
  session sharing actually works, not just in theory); office manager adds
  the registered identity to their firm by email; that person logs into the
  firm's subdomain with their *original* registration password (never
  touched by the office manager); duplicate-add and unknown-email add both
  rejected correctly; login to a firm you're not a member of is rejected;
  a non-office-manager hitting `POST /members` gets `403`; logout clears the
  cookie and `/auth/me` then returns `401`.

**Learned / decided**:
- The trigger for this redesign was realizing the original per-tenant `Users`
  row couldn't support "one client, multiple firms" without duplicate
  accounts — and that a global identity table is not actually a security
  downgrade, as long as authorization still happens at the membership/query
  layer (each request resolves role from `Memberships` for that specific
  tenant, same as before — isolation just moved one layer down).
- Chose cookies over keeping Bearer tokens specifically because of the
  cross-subdomain requirement — this is a browser storage constraint
  (localStorage is per-origin), not a security-driven choice on its own.
- Deliberately did *not* build the "one dashboard showing all your firms,
  click through into a subdomain" UI yet — that's frontend work for Phase 2.
  This session only built the backend piece that UI will depend on
  (`Identities`/`Memberships`/cookie sessions/add-by-email).
- Deliberately did *not* build invite-by-email for an email with no existing
  account (pending-invite tokens, etc.) — kept the MVP simpler: the person
  registers first, then gets added. Worth naming as a "what I'd add with more
  time" in the defense.

**Also 2026-08-26 — case assignment redesign + lawyer profiles + a real fix for the cross-tenant risk.**

**Asked**: Following on from the Identities/Memberships redesign, three more
schema questions came up: can a case have more than one lawyer (yes — the
office manager adds them, each added lawyer can view the case), should
lawyers get a profile page with a photo/bio shown on their firm's public
page, and how to actually prevent (not just remember to check) a request
made on one tenant's subdomain from ever touching another tenant's data.

**Changed**:
- Removed `Cases.client_id`/`lawyer_id` (single FK each) entirely. Added
  `models/case_assignment.py` (`CaseAssignments` — `tenant_id`, `case_id`,
  `membership_id`, unique on `(case_id, membership_id)`): one generic
  many-to-many table covering *both* lawyers and clients on a case (which one
  they are comes from `Membership.role`, not a field on this table). A case
  can now have any number of lawyers and any number of clients.
- Added a `CaseStatus` enum (`open`/`in_progress`/`on_hold`/`closed`) to
  `models/enums.py`, replacing `Cases.status`'s free `String(50)` — for
  consistency with how every other status-like field (`role`, `plan`,
  `folder_type`) is already a proper enum.
- Added `Identity.bio` (text) and `Identity.photo_url` (string) — global to
  the person, not per-firm, matching "his own page." Added
  `Membership.show_on_public_page` (boolean) — a per-firm toggle so each
  office manager independently controls whether that lawyer's profile
  actually appears on *their* firm's public page.
- Added `core/scoped.py` (`get_tenant_scoped(model, obj_id, tenant_id, db)`)
  — the actual fix for the cross-tenant risk discussed below. Any future
  route accepting a foreign id from the request body (e.g. a `membership_id`
  to assign to a case) must look it up through this instead of a bare
  `.filter(id == ...)`, so "does this belong to my tenant" is checked in one
  place, structurally, rather than being something each route author has to
  remember.
- Regenerated the Alembic migration again (same reasoning as before — only
  test data existed): `docker compose down -v`, fresh `alembic revision
  --autogenerate`, applied. Regenerated `db/schema.sql`.
- Updated `CLAUDE.md`'s Roles, Multi-tenancy architecture, and Data model
  sections to match: `super_admin` explicitly scoped to firm-level/aggregate
  data only, never case content; office manager auto-access to all cases at
  their tenant vs. lawyers needing explicit per-case assignment; the
  `CaseAssignments` table; the `get_tenant_scoped` helper as the concrete
  mechanism behind "every query touching tenant data MUST filter by
  tenant_id."
- Verified via curl: re-ran the full register/signup/add-member flow after
  the migration reset to confirm nothing broke; confirmed the new
  `case_assignments`/`cases` (enum status)/`identities` (bio, photo_url)/
  `memberships` (show_on_public_page) columns exist as expected via
  `mysqldump --no-data`.

**Learned / decided**:
- The cross-tenant risk isn't something a schema can prevent by itself — a
  foreign key only proves a row exists *somewhere*, not that it belongs to
  the tenant making the request. IDs are sequential and guessable, so this
  has to be enforced in application code, and the only reliable way to make
  sure every route does it is one shared, mandatory lookup helper
  (`get_tenant_scoped`) rather than hand-written checks that are easy to
  forget in a new route. This is a direct, concrete answer to the "where is
  authorization enforced" defense question.
- Considered but deliberately rejected: letting one `Membership` hold more
  than one role at the same tenant (e.g. a firm's own lawyer also being a
  client there). Decided against it — real complexity added to login/session
  resolution for a scenario that's rare and arguably something a real firm
  would avoid anyway (conflict of interest). Documented as a known,
  understood limitation rather than solved.
- `Documents.visible_to` (added back in the original schema step, before any
  of this design work) is now effectively redundant given `CaseAssignments`
  — access logic can be: internal folder → any lawyer assigned to that case,
  or the office manager; client folder → also any client assigned to that
  case. Left the column in place for now since dropping it isn't blocking
  anything yet; worth revisiting when Documents routes actually get built.
- Still haven't written the Phase 1 tenant-isolation pytest test, which
  CLAUDE.md calls for "early, not at the end" — flagged as the next thing to
  do before adding more schema/features.

## 2026-09-01

**Asked**: CLAUDE.md was just revised after an architecture review comparing
it against the course PDF and the actual code; the code hadn't caught up to
several of those decisions yet. Close that gap — six specific, non-feature-
coupled Phase 1 fixes — without starting Phase 2 feature work.

**Changed**:
- `POST /auth/signup`: when `admin_email` already has an `Identity`, the
  submitted password is now verified against that identity's existing
  `password_hash` and a new `office_manager` `Membership` is attached to it
  (name/photo/bio untouched — the existing identity's name is kept, not
  overwritten by `admin_name`), instead of hard-rejecting with "Email
  already registered". Wrong password on this path returns `401`.
- Added `Identities.token_version` (int, default 0). `core/security.py`'s
  `create_access_token`/`create_refresh_token`/`set_session_cookies` now
  take and embed it; `core/identity.py`'s `get_current_identity` and
  `routers/auth.py`'s `refresh` both compare the token's embedded value
  against the current DB value and reject with 401 on mismatch.
  `POST /auth/logout` now takes the identity/db dependencies, increments
  `token_version`, and commits before clearing cookies — verified via curl
  that a token captured before logout is accepted before and rejected
  (`"Session has been invalidated"`) after.
- `server/main.py` CORS switched from a fixed `CORS_ORIGINS`-list
  `allow_origins` to `allow_origin_regex=rf"https?://[a-z0-9-]+\.{BASE_DOMAIN}(:\d+)?"`
  (built from the existing `BASE_DOMAIN` env var). Removed the now-dead
  `CORS_ORIGINS` var from `.env`/`.env.example`. Verified via curl OPTIONS
  preflight: `http://acme1.lvh.me:5173` origin is allowed,
  `http://evil.com` is not.
- Added `core/tenant.py::RESERVED_SUBDOMAINS` (platform, www, api, admin,
  client, static, mail, app, assets, cdn, docs, health, localhost), checked
  in `signup` before the uniqueness check.
- `signup` and `POST /members` now wrap their inserts in
  `try/except IntegrityError`, converting the DB's unique-constraint
  rejection into the same clean `{"error": ...}` shape the pre-check gives —
  the pre-check alone is a race (two concurrent requests can both pass it
  before either has written). For `signup`, the exception handler inspects
  `str(exc.orig)` for "email" vs. the subdomain constraint to keep the
  message as accurate as the pre-check would have been, since either unique
  constraint can be the one that actually lost the race.
- Added `core/logging.py` (`configure_logging()` + `RequestLoggingMiddleware`,
  using `structlog`, JSON output). `get_current_tenant` now stashes
  `request.state.tenant_id` as soon as it resolves a tenant; the middleware
  (wraps everything, added last in `main.py` so it's outermost) reads it
  back after `call_next` and logs method/path/status/duration/tenant_id for
  every request — confirmed via `request.state` being backed by
  `scope["state"]` in Starlette 0.41 (shared across the middleware's Request
  object and the one built during dependency injection, not a private copy
  per `Request()` instantiation). Verified in container logs: tenant-scoped
  requests log a real `tenant_id`, non-tenant ones (e.g. CORS preflight)
  log `tenant_id: null`.
- Added `structlog==24.4.0` to `server/requirements.txt`.
- Regenerated the Alembic migration from scratch (same reasoning as every
  prior schema change — no real data exists yet): `docker compose down -v`,
  deleted the old single migration file, fresh
  `alembic revision --autogenerate` (now includes `token_version`), applied,
  regenerated `db/schema.sql` from a `mysqldump --no-data`.
- Verified the full flow end-to-end via curl against real `*.lvh.me:8000`
  subdomains (not spoofed `Host` headers against `localhost` — curl's cookie
  jar domain-matches against the actual request host, and a `Domain=.lvh.me`
  cookie set while connecting to `localhost` gets silently dropped by curl,
  which cost some debugging time before switching to real subdomains):
  signup (new firm + brand-new email), signup founding a *second* firm with
  an already-registered email (wrong password → 401, correct password →
  attaches, keeps original name), duplicate-subdomain and reserved-subdomain
  rejection, login, cross-subdomain `/auth/me` via the shared cookie,
  refresh, logout + old-token invalidation, register, `POST /members` (add,
  duplicate-add race path, non-office_manager 403), login rejected at a firm
  you're not a member of.

**Learned / decided**:
- `request.state` in Starlette 0.35+ is backed by `scope["state"]`, a dict
  shared across every `Request` object built from the same ASGI scope for
  that connection — this is what makes "set it in a dependency, read it back
  in an outer `BaseHTTPMiddleware`" actually work; older Starlette versions
  gave each `Request()` its own private `_state`, which would have silently
  broken this pattern.
- Starlette middleware order: `add_middleware` inserts at the front of
  `user_middleware`, and the stack is built by wrapping in reverse, so the
  *last*-added middleware ends up outermost (runs first on the way in, last
  on the way out). `RequestLoggingMiddleware` is added after `CORSMiddleware`
  specifically so it wraps CORS and captures the true end-to-end duration
  and final status code.
- Left the three Step-3 items from the CLAUDE.md review untouched on
  purpose, since they're coupled to features that don't exist yet: dropping
  `Documents.visible_to` (with Document routes), dropping `Tenants.plan` in
  favor of `Subscriptions` (with the subscription/plan-view feature), adding
  `is_super_admin` + the platform login route (with the super_admin
  dashboard), adding `Memberships.active` + reactivation (with
  member-removal). Building any of these now would mean building the
  feature around them too, which is explicitly out of scope for this
  session.
