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

## 2026-09-03

**Asked**: CLAUDE.md changed again — most significantly, the backend went
from one FastAPI app to two independent apps (`client_api`, `admin_api`)
that never call each other over HTTP, sharing only the database and a
`/server/shared` package. Assess the actual code first (don't assume a prior
session already handled it), then restructure to match, apply the
foundation fixes in their new locations, and verify end-to-end. Explicitly
told not to touch `client/`/`admin/` (frontends) and not to start Phase 2.

**Changed**:
- Assessed first: `server/` was still the single unified app from the
  previous session (`main.py`, `core/`, `models/`, `routers/`, `schemas/`,
  one `Dockerfile`) — zero prior progress on the split, confirmed by
  diffing CLAUDE.md against the last commit and by listing `server/`
  directly rather than trusting memory.
- Moved `server/core/*` → `server/shared/*` and `server/models/*` →
  `server/shared/models/*` via `git mv` (preserves history), largely as-is
  per the instruction — only the internal `core.`/`models.` imports were
  rewritten to `shared.`/`shared.models.`.
- Split `server/routers/auth.py` (the one file that had signup, login,
  register, logout, refresh, me all together) by audience into
  `client_api/routers/auth.py` (register, login, logout, refresh, me) and
  `admin_api/routers/auth.py` (signup, login, the new platform-login route,
  logout, refresh, me); `members.py` moved to `admin_api/routers/`. Each
  app got its own `schemas/auth.py`, `main.py` (own CORS regex, own
  `/health`, own call to `configure_logging()`/`RequestLoggingMiddleware`),
  and `Dockerfile` (each `COPY`s in `shared/` plus only its own app
  directory, so `client_api`'s image doesn't contain `admin_api`'s route
  code or vice versa, even though the dev bind-mount in `docker-compose.yml`
  mounts all of `server/` for hot-reload either way).
- Added a role check to both apps' `/auth/login` that wasn't in the old
  single-app version: `client_api` now rejects a resolved `office_manager`
  membership (403, "logs in through the admin portal"), and `admin_api`
  rejects `lawyer`/`client` (403, "logs in through the client portal") —
  this is the actual enforcement behind CLAUDE.md's Roles-section rule that
  "nobody cross-logs into the other app," which the single-app version had
  no reason to check since there was only one login endpoint total.
- Added `Identities.is_super_admin` (bool, default false) and
  `admin_api`'s `POST /auth/platform-login`: no `get_current_tenant`
  dependency at all (platform isn't a `Tenant` row), checks
  `Identities.is_super_admin` directly, and additionally verifies the
  request's `Host` header actually is `platform.<BASE_DOMAIN>` before
  accepting the login — not explicitly required by CLAUDE.md's text, but a
  cheap defense-in-depth check so a login granting cross-tenant visibility
  can't be triggered from a random tenant subdomain. Added
  `db/seed.sql` with just the one bootstrap super_admin row (bcrypt-hashed
  password), applied manually via `mysql < db/seed.sql` — this is
  infrastructure per CLAUDE.md, not one of the two required demo users, so
  no docker-compose auto-seeding wiring was added for it.
- `shared/tenant.py` gained `is_reserved_subdomain()`, extending the
  existing `RESERVED_SUBDOMAINS` set check with the new pattern rule: any
  subdomain ending in `-admin` is also rejected (a firm registering
  `acme-admin` would otherwise collide with the real Acme firm's own CMS
  address under the new subdomain-suffix scheme). Used by `admin_api`'s
  signup; `client_api` never creates tenants so never needed it.
- `db/migrations/env.py` updated to import `shared.database`/`shared.models`
  instead of `core.database`/`models` — migrations stay singular (one
  `db/migrations/` tree, one `alembic.ini`) regardless of the backend split,
  per the instruction.
- `docker-compose.yml`: replaced the single `app` service with `client_api`
  (port 8000) and `admin_api` (port 8001), each with its own build context
  (`./server`) and Dockerfile path, both reading the same `.env`.
- Regenerated the Alembic migration from scratch (`docker compose down -v`
  — including manually removing an orphaned `caser-app-1` container/network
  left over from the old single-service compose file, which `down -v` alone
  didn't clean up since it's no longer declared in the compose file — fresh
  `alembic revision --autogenerate`, applied), regenerated `db/schema.sql`.
- Verified end-to-end via curl against real `*.lvh.me` subdomains on both
  ports: both apps' `/health`; `admin_api` signup (including the new
  `-admin`-suffix rejection alongside the existing literal blocklist);
  office_manager login via `admin_api` succeeds, via `client_api` gets 403;
  `client_api` register + office_manager adding that identity as `lawyer`
  via `admin_api`; that lawyer logs in via `client_api` successfully, via
  `admin_api` gets 403; `platform.lvh.me:8001` super_admin login succeeds,
  the same call at a tenant subdomain is rejected, a non-super_admin
  identity is rejected; **a token issued by `client_api` is accepted by
  `admin_api`'s `/auth/me` with zero HTTP call between the two processes**
  (shared `JWT_SECRET_KEY` + `token_version` lookup against the shared DB),
  and logging out via `client_api` invalidates that same token on
  `admin_api` too (`token_version` is per-Identity, not per-app); CORS
  allow/deny on `admin_api`; structured JSON logs with `tenant_id` on both
  apps independently.

**Learned / decided**:
- Hit the same `email-validator` reserved-TLD issue as last session, this
  time on the seed data: `super@casehub.local` was rejected by `EmailStr`
  the moment I tried to log in with it (`.local` is a reserved/special-use
  TLD), even though the row itself was inserted via raw SQL and never passed
  through Pydantic at insert time. Fixed by using `casehub.example.com`
  instead. Worth remembering for any future seed/demo email: `.test`,
  `.local`, `.example` (bare) and similar reserved TLDs will pass into the
  database fine but then can never be used to log in through a Pydantic
  `EmailStr` field.
- `docker compose down -v` only removes what the *current* compose file
  declares — a service renamed or removed from `docker-compose.yml` (here,
  `app` → `client_api`/`admin_api`) leaves its old container and the
  network genuinely orphaned, requiring a manual `docker stop`/`rm`/
  `network rm` before `up` can succeed cleanly. Worth checking `docker ps -a`
  after any compose service rename, not just after a plain `down -v`.
- Chose one shared `server/requirements.txt` (referenced by both
  Dockerfiles via the shared `./server` build context) rather than two
  near-identical per-app files, since both apps need essentially the same
  dependency set (they both import the same `shared/` code) — judged this
  as dependency-declaration bookkeeping, not the "application logic"
  duplication CLAUDE.md's Code quality section is actually trying to avoid
  between the two apps.
- Confirmed with the user before adding `is_super_admin`/the platform-login
  route: CLAUDE.md's Step 2 instruction named the route explicitly, but the
  same session's foundation-fixes list didn't mention the column, and a
  prior session had explicitly deferred it as feature-coupled. User chose
  to build it fully now (including the minimal seed row) rather than leave
  it stubbed, since Step 5 required verifying it end-to-end.

## 2026-09-05

**Asked**: Phase 2's first vertical slice — Cases. `Case`/`CaseAssignment`
already existed as models (Phase 1's "create all tables upfront" rule), so
this was routes only, split by audience: `admin_api` gets create/list-all
(office_manager sees every case automatically)/edit-title/change-status
(incl. reopening a closed case)/assign-unassign, all `office_manager`-only;
`client_api` gets list-assigned-only and view-if-assigned for
`lawyer`/`client`. Also due with this slice per CLAUDE.md's Build order: the
Phase 1 tenant-isolation pytest test, written against real endpoints.

**Changed**:
- `admin_api/routers/cases.py` + `admin_api/schemas/cases.py`: create, list
  (paginated), get, edit title, change status, and list/create/delete
  `CaseAssignment`. Every route taking a foreign id (`case_id` in the path,
  `membership_id` in the assign body) resolves it through `get_tenant_scoped`
  rather than a bare `.filter(id == ...)` — both are exercised by the
  isolation tests below.
- `client_api/routers/cases.py` + `client_api/schemas/cases.py`: list cases
  joined through `CaseAssignment` filtered to the caller's own
  `membership.id`; get-one resolves the case tenant-scoped first (404 if it
  isn't even this tenant's case), then checks the assignment separately
  (403 if the case exists here but isn't assigned to this membership).
- `admin_api/core/pagination.py` and `client_api/core/pagination.py`: a small
  `PageParams`/`Page`/`paginate()` helper, written once per app on purpose —
  CLAUDE.md's Code quality section scopes `/server/shared` to only table
  definitions + tenant/auth logic and calls out pagination specifically as
  something that stays separate per app rather than shared across the two.
- `server/tests/` (new): `conftest.py` (fresh-schema-per-test fixture against
  a dedicated `casehub_test` MySQL database — created manually via
  `docker exec ... mysql -uroot ... CREATE DATABASE casehub_test` and granted
  to `app_user` — plus `TestClient` fixtures for both apps with `get_db`
  overridden to the test session, and an `auth_for()` helper that mints a
  real JWT and passes it as a per-request cookie alongside a spoofed `Host`
  header, sidestepping the test client's cookie-jar domain matching
  entirely), `test_cases_admin.py`, `test_cases_client.py`, and
  `test_tenant_isolation.py` — the required Phase 1 test, proving an
  `office_manager`/`lawyer`/`client` authenticated on tenant A's subdomain
  cannot get, list, edit, change the status of, assign to, or unassign from
  tenant B's case on either backend, including the case where the
  `membership_id` in an assignment request body points at a foreign tenant's
  membership. 26 tests, all passing against real endpoints, not mocks.
- Added `pytest`/`httpx` to `server/requirements.txt` (named in CLAUDE.md's
  tech stack since the start but never actually added until this slice
  needed to run a test), a `TEST_DATABASE_URL` entry in `.env`/
  `.env.example`, and `server/pytest.ini` (`testpaths = tests`).

**Learned / decided**:
- Hit the same `email_validator` reserved-TLD rejection noted in the
  2026-08-25 entry above, this time in fresh test fixtures written without
  remembering that note: `@acme.test` failed `EmailStr` validation on every
  response model with an email field. Switched fixture domains to ordinary
  `.com` addresses.
- `docs/` existed already (this file has history back to 2026-08-19) but I
  didn't check for that before my first write attempt and nearly clobbered
  the whole log with a from-scratch version containing only this entry —
  caught it via `git diff` before committing anything and restored the
  original with `git checkout -- docs/ai_usage.md` before appending properly.
  Lesson: always check `git log`/read the existing file before writing to a
  path CLAUDE.md describes as a persistent, growing log, rather than
  trusting a single `find`/`ls` run from the wrong working directory.
- Verified both `admin_api` and `client_api` boot cleanly with the new
  routers registered by checking `/openapi.json` on the actual running
  Docker containers (which auto-reloaded on the file changes via
  `WatchFiles`) — pytest alone exercises the same route code but through an
  ASGI transport rather than a live uvicorn process, so this was a useful
  independent check.

## 2026-09-05

**Asked**: Close two remaining schema mismatches between CLAUDE.md's Data
model (already fully specified, just not yet built) and the actual code:
add `Memberships.active`, and drop `Tenants.plan` in favor of
`Subscriptions` being the sole source of truth for a firm's plan. Work
directly on `master` (Phase 1 foundational correction, not a new feature).

**Changed**:
- Found `feature/cases` had never actually been merged — it was identical
  to `master` (zero commits on the branch), with the entire Cases vertical
  slice (routers, schemas, pagination, and the required
  `test_tenant_isolation.py`) sitting uncommitted in the working tree.
  Flagged this to the user rather than assuming the merge already happened
  elsewhere; independently re-ran the test suite myself (26 passed) before
  trusting the existing session's "26 passed" claim in this file, then
  committed to `feature/cases` and merged it into `master` before starting
  today's actual task.
- `shared/models/tenant.py`: removed the `plan` column (and the now-unused
  `Plan` import).
- `shared/models/membership.py`: added `active` (bool, default `True`). Not
  wired into any query or route yet — no member-removal route exists yet,
  so there's nothing to filter `active = true` in and no reactivate-on-re-add
  logic to write. Left as a bare column, per the instruction, until whichever
  future session builds member removal.
- `admin_api/routers/auth.py`'s `signup` was the one place that read/wrote
  `Tenants.plan` (`plan=Plan.FREE` on the new `Tenant`) — changed to create
  the new firm's first `Subscription` row instead (`plan=Plan.FREE,
  start_date=today, active=True`), inside the same try/except-guarded
  transaction as the `Tenant`/`Identity`/`Membership` rows. `db/seed.sql`
  and `server/tests/conftest.py` were already `Plan`-free, so nothing else
  needed touching.
- Regenerated the Alembic migration from scratch for both changes together
  (`docker compose down -v`, fresh `alembic revision --autogenerate`,
  applied), regenerated `db/schema.sql`, re-applied `db/seed.sql` and
  recreated the `casehub_test` database (both live on the same MySQL volume
  `down -v` wipes).

**Learned / decided**:
- The existing pytest suite creates its test tenants directly via the
  `Tenant(...)` fixture in `conftest.py`, never through `POST /auth/signup`
  — so it gave no coverage at all of the signup-route change (the
  `Tenants.plan` → `Subscription`-row swap). All 26 tests still passed after
  the migration, but that only proved the schema change didn't break
  anything the tests touch, not that signup itself still worked. Verified
  the actual route separately via curl (`POST /auth/signup` against a fresh
  subdomain, then a DB query joining `tenants`/`subscriptions` to confirm
  the new firm actually got an active Free subscription row) before
  considering this done — a reminder that "the test suite is green" and
  "the changed code path works" aren't automatically the same claim.
- Confirmed before proceeding, rather than assuming: the task said
  `feature/cases` "has likely already been merged," but `git log`/
  `git rev-parse` showed master, `feature/cases`, and `origin/master` all
  pointing at the identical commit — i.e. never merged, with real
  uncommitted work at risk. Surfaced this explicitly instead of either
  silently merging on my own judgment or silently proceeding as if it had
  already happened.

## 2026-09-07

**Asked**: First frontend session — nothing existed yet in `client/`/`admin/`.
Scope: two real, separate Vite/React apps proving the login/cookie/session
mechanism works in a real browser (register/login/signup + a minimal
authenticated landing page calling `/auth/me`). Explicitly not Cases screens
yet. New branch `feature/frontend-auth-shell`, per the branch+PR discipline
that starts at Phase 2's first vertical slice.

**Changed**:
- Scaffolded `client/` and `admin/` as two independent `npm create vite@latest
  -- --template react` projects (plain JS, not TS — matches the rest of the
  codebase using plain Python without heavy type-ceremony) plus
  `react-router-dom`. Removed the default scaffold cruft (`App.css`, the
  Vite/React demo assets/logos).
- Both apps: `index.html` sets `<html lang="he" dir="rtl">` at the root (not
  just a wrapper div), so RTL is a document-level default before any CSS
  runs. `src/index.css` defines each app's own CSS custom properties
  (colors/spacing/typography) — genuinely different palettes (client: warm/
  light, teal primary; admin: cooler/denser, indigo primary) per CLAUDE.md's
  "deliberately different designs, not shared" rule, not just a copy-paste
  with one color swapped.
- `vite.config.js` (both apps): fixed `port`/`strictPort` (5173 client, 5174
  admin) and `server.allowedHosts: ['.lvh.me']` — Vite's dev server rejects
  unrecognized `Host` headers by default (DNS-rebinding protection), which
  would otherwise block every tenant-subdomain request (`office1.lvh.me:5173`)
  since Vite only trusts `localhost`/the literal configured host by default.
- `src/api/client.js` (both apps): the auth-aware fetch wrapper. Base URL is
  built from `window.location.hostname` (whatever tenant subdomain the page
  is actually being viewed at) plus a protocol/port pair read from
  `VITE_API_PORT`/`VITE_API_PROTOCOL` env vars — not a full hardcoded URL,
  since a full URL can't be both "from env" and "correct for every tenant
  subdomain" at once (the whole point of subdomain-based tenancy is that the
  frontend and backend share the same subdomain, differing only by port).
  Sends `credentials: 'include'` on every request, parses the `{error,
  field}` shape, and redirects to `/login` on a 401 — except login/register/
  signup calls themselves pass `redirectOn401: false`, since a 401 there
  means "wrong password" (an inline form error), not an expired session.
- `src/api/auth.js` (per app): thin wrappers per endpoint — `client/` has
  `register`/`login`/`me`/`logout`; `admin/` has `signup`/`login`/`me`/
  `logout` (platform-login skipped this session, per the task's own
  "nice-to-have, skip if short on time").
- Reusable component patterns established in both apps independently (own
  files, not shared — same reasoning as the CSS tokens): `DataTable` (handles
  Loading/Error/Empty explicitly, per CLAUDE.md's three-states rule — used
  today to render the logged-in identity's id/name/email on the landing
  page), `FormField`/`FormError` (used by every form this session), `Modal`
  (portal-based; wired into `Layout`'s "אודות/About" link so it's a real,
  exercised code path today rather than dead scaffolding waiting for Cases).
- `Layout` component (both apps): header with `<nav>` as the first DOM child
  — in an RTL flex row the first child lands at the "start" edge, which is
  the right side, giving "nav on the right" from plain source order rather
  than manual positioning.
- Screens: `client/` — `RegisterPage`, `LoginPage`, `LandingPage`; `admin/` —
  `SignupPage`, `LoginPage`, `LandingPage`. All UI copy (labels, buttons,
  headings, error banners) written in Hebrew per CLAUDE.md's "Frontend UI is
  RTL (Hebrew)" rule; code/variables/comments stayed English per the same
  rule. Backend error strings (e.g. "Invalid email or password") are
  displayed as-is in English — translating API error copy wasn't in scope
  this session.
- `db/seed.sql`: added the two required demo users (a dedicated `Demo Firm`
  tenant at subdomain `demo`, an active Free `Subscription` row for it, and
  one `office_manager` + one `client` `Identity`+`Membership` each) —
  `office_manager@casehub.example.com` / `OfficeManager123!` and
  `client@casehub.example.com` / `Client123!`. Applied directly to the
  running dev DB via `docker exec ... mysql`, not just written to the file.
- `client/.env.example` / `admin/.env.example` (+ matching `.env`, gitignored
  by the existing root pattern): `VITE_API_PROTOCOL`, `VITE_API_PORT` (8000 /
  8001 respectively).

**Verified**:
- Via curl with real `*.lvh.me` subdomains (not spoofed `Host` headers) and a
  shared cookie jar: `admin_api` signup at `office1.lvh.me:8001` sets the
  session cookie and returns the office_manager; `GET /auth/me` on
  `client_api` at the *same* subdomain, different port, recognizes the exact
  same cookie and resolves the identity — the concrete proof of CLAUDE.md's
  "one login, many apps" cookie-domain-scoping claim, this time actually
  exercised through what the frontend's own fetch wrapper does (not just
  cookie mechanics in the abstract). `client_api` register (bare identity),
  `/auth/me`, and the two demo users logging in via their respective apps at
  `demo.lvh.me` all confirmed working. CORS: a request carrying
  `Origin: http://office1.lvh.me:5173`/`:5174` gets back matching
  `access-control-allow-origin` + `allow-credentials: true` on both APIs,
  confirming the frontend's actual dev-server origins are trusted, not just
  the regex pattern read by eye. Logout correctly invalidates the session
  (`token_version` bump) — a captured cookie is rejected with 401
  immediately after.
- `npm run build` succeeds cleanly for both apps (no import/syntax errors).
  Both Vite dev servers confirmed serving `office1.lvh.me:5173`/`:5174` with
  HTTP 200 (proving `allowedHosts` actually works against a real tenant
  subdomain, not just `localhost`).
- Real-browser confirmation via headless Chromium (Playwright, installed
  fresh for this session — not previously set up in the project): drove the
  full admin-signup → landing → client-register → landing flow against real
  `*.lvh.me` subdomains on both dev-server ports, with screenshots at each
  step. Confirmed: `document.documentElement.dir === 'rtl'`; the nav element
  renders right of the brand element (`getBoundingClientRect().x` compared
  directly, not just eyeballed); the About modal opens correctly; both apps'
  distinct color tokens render as designed; `console` carried no errors
  except one real bug caught this way (see below). Also directly observed
  the cross-app cookie sharing in the browser itself, not just curl: after
  registering as a new identity in `client/`, reloading `admin/`'s landing
  page (same browser, no new admin login) showed the *client* identity's
  `/auth/me` data — the browser's single cookie jar for `.lvh.me` was
  overwritten by the more recent register call, exactly as the architecture
  predicts (one person, one session, shared across every app on the domain).
  This was flagged to the user as the expected mechanism, not a bug, since
  the recommended manual click-through would otherwise look like a broken
  session.

**Bug found and fixed via the browser check (not caught by `npm run
build`/lint or curl)**: `admin/src/pages/SignupPage.jsx`'s subdomain field
had `pattern="[a-z0-9-]+"`. Real Chromium logs a console error compiling
this as an invalid regex (`/[a-z0-9-]+/v: Invalid character class`) — some
Chromium versions validate the HTML5 `pattern` attribute using the regex `v`
(unicode-sets) flag, under which a bare trailing `-` in a character class is
ambiguous. Fixed by escaping it (`[a-z0-9\-]+`); re-verified zero console
errors after. Worth remembering for any other `pattern` attribute added
later in either app.

**Learned / decided**:
- The `VITE_API_PORT`/`VITE_API_PROTOCOL`-plus-`window.location.hostname`
  split (instead of one `VITE_API_BASE_URL`) is the one real design call
  made without asking first — reasoned through in the moment rather than
  guessed: a single full base URL read from env can't simultaneously be
  "configurable" and "correct for whatever tenant subdomain the page happens
  to be on," since the tenant subdomain is only known at request time in the
  browser, never at build/env time. Worth being able to explain this
  specific tradeoff in the defense if asked why the API URL isn't just one
  env var.
- Vite's dev-server `allowedHosts` default (only `localhost`/the configured
  host trusted, everything else 403's as a DNS-rebinding guard) would have
  silently blocked every tenant-subdomain request had it not been caught
  before first browser test — worth remembering for any future Vite config
  change, since the failure mode (a blank 403 page) doesn't obviously point
  at this setting.

## 2026-09-08

**Asked**: Apply the settled visual design (published earlier as a design
canvas artifact — forest-green anchor for `client/`, navy anchor for
`admin/`, warm pearl background, no separate accent hue, Heebo/Frank Ruhl
Libre, 10/16/20px radius scale, soft-shadow cards) to both real frontends,
then build the first real feature screens on top of it: Cases list + Cases
detail in `client/`, wired to the actual `client_api` endpoints. New branch
`feature/client-case-screens`. Explicitly out of scope: admin's own
case-management screens, and any backend changes.

**Blocker surfaced and resolved before writing any UI**: read the actual
`Case` model/`CaseResponse` schema and `client_api`'s router list before
building anything, rather than assuming the design mockup's data was all
real. Found two gaps between the mockup and reality: (1) `Cases` only has
`id`/`tenant_id`/`title`/`status`/`created_at` — no practice-area or
progress field the mockup showed; (2) `client_api` only has `auth`/`cases`
routers — no `/documents` or `/work-logs` endpoints exist yet, even though
the task asked for a document-folders section and a work-hours summary on
the case detail screen. Asked the user rather than guessing (per this
session's explicit instruction): confirmed dropping the fabricated list
columns entirely (no fake progress-from-status mapping), and building the
document/hours sections as honest static "coming soon" placeholders in the
real layout rather than either faking data or skipping the sections.

**Changed**:
- `client/src/index.css` and `admin/src/index.css`: full token rewrite —
  `oklch()` color values matching the design artifact exactly (client:
  `--color-primary: oklch(38% 0.08 155)` / sidebar `oklch(27% 0.06 155)`;
  admin: `--color-primary: oklch(30% 0.13 258)`), a three-tier radius scale
  (`--radius-control: 10px`, `--radius-card: 16px`, `--radius-modal: 20px`,
  with `--radius` kept as an alias to `-control` so existing component CSS
  using `var(--radius)` picked up the right tier with zero changes), and
  semantic status tokens (`--color-success`/`-info`/`-warn`/`-gray`, each
  with a `-bg` tint) for status pills — conventional traffic-light colors,
  not derived from the anchor hue, same as the design artifact itself does;
  the "no separate accent hue" rule reads as applying to brand/action colors
  (buttons, highlights, progress bars), not to semantic status indicators.
  Added Heebo/Frank Ruhl Libre via Google Fonts `<link>` in both
  `index.html`s (`.wordmark` class reserves the serif for the brand name
  only, per the rule).
- `Modal.css` (both apps): radius/shadow switched to the new `-modal` tier
  tokens.
- `client/src/components/AppShell.jsx` (new) + `.css`: the sidebar shell
  every authenticated screen now renders inside — resolves `/auth/me` once
  (redirects to `/login` on failure) and renders the 232px forest sidebar +
  topbar (user initials/name + logout) + content area around whatever page
  is passed in. Nav has three items (`תיקים`/`מסמכים`/`שעות עבודה`) matching
  the mockup, but only `תיקים` is a real link — the other two render as
  visually-styled but inert (`disabled`, non-clickable) items rather than
  linking to screens that don't exist yet, so the shell matches the settled
  design without shipping dead routes.
- `client/src/components/Layout.jsx`'s existing CSS (kept, not replaced) got
  the gradient background + wordmark-font brand treatment from the login
  mockup — still used for `/login`/`/register` only, which stay outside
  `AppShell` (no sidebar on unauthenticated screens, matching the mockup).
- `client/src/components/DataTable.jsx`: added an `onRowClick` prop (row
  → click handler) — extended rather than duplicated, since both new Cases
  screens need clickable rows and this is the one reusable table component
  in the app.
- `client/src/api/cases.js` (new): `listMyCases()` (single call at
  `page_size=200`, the API's max — a lawyer/client's own assigned-case count
  realistically never exceeds that, so this covers the whole list without
  building real pagination UI on top of it yet, noted as a simplification
  rather than silently skipped), `getMyCase(id)`.
- `client/src/api/session.js` (new) + `auth.js` edit: `login()`'s response
  already carries `role` (per `client_api`'s `SessionResponse`), but
  `/auth/me` (used on every page reload) doesn't — so `role` is stashed in
  `sessionStorage` on login and cleared on logout, purely so the case-detail
  screen knows whether to show the internal-documents tab. Documented inline
  as a UI-only convenience, never a security boundary — real enforcement
  will live server-side once `/documents` exists.
- `client/src/utils/caseStatus.js` + `format.js` (new): status label/color
  mapping and date/avatar-initial formatting, extracted immediately since
  both the list and detail screens needed the same status pill and both
  needed a date formatter — not left duplicated waiting for a third
  caller.
- `client/src/pages/CasesListPage.jsx` + `.css` (new): sidebar nav "תיקים",
  a title, then either an error banner, a loading message, an empty-state
  card ("אין לך תיקים משויכים כרגע"), or (once cases exist) four real stat
  cards (counts per `CaseStatus` value — open/in_progress/on_hold/closed,
  the only stats actually backed by real data) + a status-tab-filterable
  table (avatar-initial + title + case-number, opened date, status pill),
  rows clickable through to the detail screen via `DataTable`'s new
  `onRowClick`.
- `client/src/pages/CaseDetailPage.jsx` + `.css` (new): back link, title +
  status pill + case-number chip + opened date, then a two-column layout —
  a documents card (client-folder tab always shown; internal-folder tab only
  if the stored role is `lawyer`) and a work-hours card, both rendering the
  agreed "coming soon" placeholder text instead of calling endpoints that
  don't exist. Loading/error states cover the whole screen (a 403 on an
  unassigned case renders the server's own message in the error state).
- `client/src/App.jsx`: routes restructured — `/login`/`/register` still
  wrapped in `Layout`; `/cases` and `/cases/:caseId` render directly (they
  wrap themselves in `AppShell`); `/` now redirects to `/cases` instead of
  rendering the old scaffold `LandingPage`.
- Deleted `client/src/pages/LandingPage.jsx` — it was explicitly a
  placeholder from the prior auth-shell session ("the actual proof this
  session sets out to give"), fully superseded now that `CasesListPage` is
  the real authenticated home; left as dead code otherwise.

**Verified in a real browser** (Playwright/Chromium — not previously set up
on this machine this session, installed via `pip install playwright` +
`playwright install chromium`, since no `chromium-cli` was available here;
worth a `/run-skill-generator` follow-up so a future session doesn't
re-solve this): created throwaway test data through the real running apps,
not fixtures — registered a `lior.lawyer@example.com` identity via
`client_api`, added as `lawyer` at the `demo` tenant and created/assigned
four cases (one per `CaseStatus` value) via `admin_api` (as the seeded
office_manager), all through real HTTP calls against `demo.lvh.me`. Then,
against the actual Vite dev servers:
- Demo client (`client@casehub.example.com`) sees exactly the 2 cases they
  were assigned (open + in_progress), correct stat counts, forest sidebar,
  Heebo/rounded-card styling; case detail shows exactly 1 document tab
  (client-visible only).
- Demo lawyer sees all 4 cases including the closed one, correct per-status
  stat counts; case detail on the closed case shows 2 document tabs
  (client + internal) — confirms the role-gating actually branches, not
  just present in one screenshot.
- Error state: navigating a client to a case they're not assigned to
  renders the 403 message in the error banner, shell (sidebar/topbar) still
  intact.
- True empty state: a freshly-registered client with zero assignments sees
  the "אין לך תיקים משויכים כרגע" card, no stat row, no table.
- Admin login screen confirmed rendering the navy anchor (`oklch(30% 0.13
  258)`), independently of the client login's forest anchor — the two-app
  color-token fix verified side by side, not just read from the CSS.
- Zero browser console errors across every step (`page.on('console')`/
  `pageerror` both checked, not just visual inspection).
- Backend error strings surfaced in the UI (e.g. "You are not assigned to
  this case") are still raw English from the API, same known gap noted in
  the 2026-09-07 entry — not addressed this session, frontend-only scope.

**Learned / decided**:
- Read the actual `Case` model and router list before writing any UI code,
  rather than trusting the design mockup's fields — the mockup was drawn
  before the document/work-log backend slices existed, so it necessarily
  showed data that doesn't exist yet. Asking before guessing here avoided
  either fabricating fake progress/practice-area data or silently building
  UI that calls endpoints that don't exist and would 500/404 in the demo.
- `role` is a genuine gap in `/auth/me` (only `login` returns it) — worked
  around client-side via `sessionStorage` rather than touching
  `client_api/schemas/auth.py`, since backend changes were explicitly out of
  scope this session. Worth a small follow-up to add `role` to
  `IdentityResponse` so a page refresh doesn't rely on a same-tab-only
  stash.
- The `--radius`-as-alias-to-`--radius-control` token trick let every
  existing input/button CSS rule (written before this session, referencing
  `var(--radius)`) automatically land on the correct tier without editing
  those files — only `.modal` needed an explicit override to the `-modal`
  tier, since it's the one component that intentionally uses a different
  radius than the default alias.
- Test data (the `lior.lawyer@example.com` identity, four demo cases, and
  one zero-assignment client) was created directly against the running dev
  containers via `curl`, not added to `db/seed.sql` — it exists only in the
  local Docker volume on this machine, not committed, since CLAUDE.md's
  seed-data spec names exactly two required demo users and doesn't call for
  case/assignment seed data.

## 2026-09-08 (2) — RTL header/logo bug fix

**Asked**: The brand wordmark in the auth-pages header (`Layout.jsx`,
`/login`/`/register` in both apps) was rendering on the left instead of the
right. New branch `fix/rtl-header-logo` off `master` (after pulling in the
now-merged previous PR), same branch+PR discipline as any Phase 2 change.
Investigate the actual cause before touching anything — check for
hardcoded directional CSS (`margin-left`, `float: left`, explicit
`left:`/`right:`) instead of flexbox/logical properties, and confirm
`dir="rtl"` is actually scoped onto the component — rather than assuming.

**Investigated first** (Playwright against the real running dev servers,
not just reading the CSS): confirmed `<html dir="rtl">` is set and
inherited with no override anywhere in either app (`grep`'d both `src/`
trees for `dir=`, `direction:`, `float:`, `margin-left`/`-right`,
`left:`/`right:` — zero hardcoded directional properties exist in the
whole frontend). `getComputedStyle(.app-header).direction` was already
`"rtl"`, `display` was `"flex"`, and every positional computed property on
`.app-brand` (`float`, `marginLeft`, `marginRight`, `position`, `left`,
`right`) was a no-op default (`none`/`0px`/`static`/`auto`). So this was
**not** a directional-CSS-property bug and **not** a `dir`-scoping bug —
flexbox's `justify-content: space-between` was already correctly
auto-reversing under RTL. The actual cause: `<nav>` (the "About" link) was
the *first* DOM child in `Layout.jsx`'s `<header>`, landing at the RTL
"start" (right) edge, with the brand `<div>` second, landing at the "end"
(left) edge — a deliberate DOM-order choice from the frontend-auth-shell
session (documented in that file's own comment at the time), now
superseded by the design direction that the brand belongs at the
start/right, matching `AppShell`'s sidebar (where the brand is already the
first child and correctly sits top-right — confirmed by the same
measurement approach as a sanity baseline).

**Changed**:
- `client/src/components/Layout.jsx` and `admin/src/components/Layout.jsx`
  (identical structure, differ only in copy — confirmed via `diff` before
  fixing both): swapped the `<header>`'s child order so `.app-brand` is
  first (right) and `<nav>` is second (left). Updated the stale comment to
  describe the new order and note it now matches `AppShell`'s sidebar
  convention. No CSS changes needed — flexbox already did the right thing
  once DOM order was corrected.
- Checked for the same pattern elsewhere in header/topbar components before
  calling this done: `AppShell.jsx`'s `.content-topbar` has no brand at all
  (just user info + logout, DOM order there was never wrong), and its
  sidebar brand was already first-child/correct — so the fix is fully
  scoped to the two `Layout.jsx` files, nothing else needed touching.

**Verified**: re-ran the same Playwright bounding-rect measurement after
the fix — brand now renders at `x≈1182–1245` (right edge of a 1400px
viewport) and nav at `x=24` (left edge), reversed from before. Screenshots
confirm both apps' login/register headers now show the wordmark top-right,
"About" top-left; the already-correct `AppShell`-based Cases screen (not
touched by this fix) re-verified rendering identically to before, zero
console errors.

**Learned / decided**:
- A "logo on the wrong side" bug in an RTL layout isn't always a missing
  `dir` attribute or a leftover `margin-left`/`float:left` — flexbox with
  `justify-content: space-between` auto-reverses correctly under `dir=rtl`
  precisely *because* it has no built-in concept of "left"/"right", only
  DOM order and start/end. That means the bug can be purely which element
  comes first in the DOM, with the CSS itself already textbook-correct —
  worth checking DOM order specifically, not just scanning for
  directional CSS properties, when a flex-based RTL layout looks mirrored
  from what's intended.
- Verifying the "before" state with real computed-style measurements (not
  just eyeballing a screenshot) both confirmed the diagnosis precisely and
  gave a before/after pair worth re-running after the fix — cheap
  insurance against "looks right" being wrong at a specific breakpoint or
  in a specific browser.

## 2026-09-08 (3) — investigated a reported color "regression"; found none; two real design tuning requests instead

**Asked**: A follow-up report claimed the DOM-order fix above caused the
header's color to look "slightly off," with a specific hypothesis to check
first: a positional selector (`:first-child`/`:last-child`/`:nth-child`/an
adjacent-sibling `+`) styling the brand or nav instead of a class name,
which reordering the DOM would silently misapply. Told explicitly not to
force that explanation if it turned out to be something else, and not to
just patch a color back by hand without finding the actual cause.

**Investigated, found no regression at all**: grepped both apps' entire
`src/` trees for `:first-child`, `:last-child`, `:nth-child`,
`:nth-of-type`, and sibling combinators (`+`, `~`) — zero matches anywhere;
every header-related rule is a plain class selector. Re-read the exact diff
of the prior commit: both `className` attributes stayed correctly bound to
their original elements, only DOM position changed. Then verified this
empirically three ways rather than stopping at static reading: (1)
`getComputedStyle(.app-brand).color` on the live pages resolved to exactly
`var(--color-primary-hover)` (client) / `var(--color-primary)` (admin) —
precisely the values `Layout.css` specifies; (2) pixel-diffed (installed
Pillow for this) the brand-text region between the screenshot taken right
after the DOM-order fix and a fresh screenshot taken just now — **0 of
7200 pixels differed**, on both apps; (3) confirmed no child-combinator or
cascade-order mechanism exists anywhere that could make sibling order
matter, and that `.app-header` has no background of its own (so no
gradient positioned elsewhere could bleed through differently based on
child order). Reported this evidence back rather than fabricating a "fix"
for a bug that didn't reproduce — the user then clarified: not a bug,
two actual design tuning requests.

**Changed** (still `fix/rtl-header-logo`, since PR #4 hadn't been merged
yet — per instruction, one more commit on the same branch rather than a
new one, kept separate from the RTL commit so the two changes stay
distinguishable in history):
- `client/src/components/Layout.css` and `admin/src/components/Layout.css`:
  `.app-header` gained `background: var(--color-surface)` (white, the same
  token cards already use) and a subtle two-layer `box-shadow` in the same
  formula/hue as the existing `--shadow-card` token, so the header now
  reads as a distinct elevated surface above the pearl page background
  instead of blending into it — applied identically to both apps'
  otherwise-identical `Layout.css` files.
- `client/src/components/Layout.css`'s `.app-main` background: the second
  `radial-gradient` layer's hue was hardcoded at `38` (orange/coral family)
  — confirmed via `grep` before touching anything (the only hue-38 hit in
  either app's entire CSS; admin's own single gradient layer was already
  hue `258`/navy-family, untouched). Left over from before the
  accent-color cleanup in the design-system session (which fixed the named
  CSS variables — buttons/badges — but missed this hardcoded inline value
  in a gradient stop). Changed `oklch(93% 0.03 38 / 0.3)` →
  `oklch(93% 0.03 155 / 0.3)` — same lightness/chroma/alpha, hue shifted to
  155 (client's own forest anchor family), rather than introducing a new
  arbitrary color.

**Verified**: `getComputedStyle` confirms both headers now render
`background-color: rgb(255, 255, 255)` with the intended box-shadow, on
both apps. Sampled pixels in the login page's bottom-right gradient corner
(previously the orange stop's territory): `rgb(240, 245, 239)` — green
channel dominant, a subtle warm-*green* tint, not orange. Re-confirmed the
RTL fix from the earlier commit is still intact (`brand.x > nav.x` on the
admin login page). Re-checked the `AppShell`-based Cases screen (which has
no gradient and a different header entirely — `.content-topbar`, not
`.app-header`) renders identically, confirming neither change leaked
scope. Zero console errors throughout.

**Learned / decided**:
- A user-reported "regression" tied to a very specific, plausible-sounding
  hypothesis is still worth disproving with hard evidence (computed styles
  + pixel diff) rather than either blindly trusting the hypothesis or
  dismissing the report — in this case the hypothesis was wrong, no code
  regression existed, but the underlying concern (the header not reading
  as a distinct element) was a legitimate design gap once reframed as a
  tuning request rather than a bug.
- The hardcoded `oklch(... 38 ...)` gradient stop is a good example of why
  a "replace the named token, done" cleanup can leave a real leftover: the
  accent-color removal fixed `--color-primary`/badge/button colors (named
  variables), but a raw color value typed directly into a `background:`
  gradient declaration isn't reachable by a token rename — worth a
  one-time `grep -r "oklch("` sweep across both apps' CSS if another
  color-family cleanup happens later, rather than trusting that all colors
  route through named tokens.

## 2026-09-08 (4) — office_manager Cases screens in `admin/` (branch `feature/admin-case-screens`)

**Asked**: Build the office_manager-facing Cases screens in `admin/` — list
(paginated, status filter, "new case"), create-case modal, and a
detail/edit view (title edit, status change including reopen, assign/
unassign lawyers and clients) — wired to the real, already-tested
`admin_api` case endpoints. Told to extend `admin/`'s existing Members and
Dashboard screens' look (navy anchor, sidebar, DataTable/chip/card
conventions, "add member" modal pattern) since no design canvas exists for
this screen, and to stop and ask rather than guess on anything ambiguous.

**Found before writing any code**: neither a Members nor a Dashboard
screen actually exists yet in `admin/` — the app only had Login/Signup/a
placeholder Landing page, behind a plain header (`Layout.jsx`), no sidebar.
The navy design tokens, `DataTable`, `Modal`, and `Form` components did
exist and were reusable as-is; the sidebar-shell and "add member modal"
patterns the brief pointed to only exist in `client/`'s `AppShell`
(forest-themed). Separately, `admin_api` had no `GET /members` — only
`POST /members` (add-by-email) — so an assign-from-existing-members picker
had no data source. Flagged both gaps and asked rather than guessing:
confirmed introducing an admin `AppShell` (navy recolor of `client/`'s)
now, and adding a minimal `GET /members`, both following existing
conventions exactly.

**Changed — backend** (`server/admin_api`):
- `routers/members.py`: added `GET /members` (tenant-scoped, paginated,
  `active = true` only, optional `role` filter) returning a new
  `MemberResponse` schema (`schemas/auth.py`) that joins `Identity` for
  name/email — same join pattern `cases.py`'s assignments endpoint already
  uses. Needed for the assignment picker to list real lawyers/clients
  instead of free text.
- `routers/cases.py`: added an optional `status` query param to
  `GET /cases` (backward-compatible — existing calls without it are
  unaffected) so the admin case list can offer a real, server-paginated
  status filter instead of only ever filtering whichever single page of up
  to 200 happened to be fetched (the shortcut `client/`'s "my cases" list
  uses, which doesn't hold up once a list is genuinely paginated at 50/page
  with a firm-wide case count that can exceed that).
- `tests/test_members_admin.py` (new) and additions to
  `tests/test_cases_admin.py`: role filtering, `active=false` exclusion,
  role-guard (403 for lawyer), tenant isolation for the new members list,
  and the new status-filter behavior. Full suite (32 tests) passes against
  the real `casehub_test` MySQL database via the running `admin_api`
  container.

**Changed — frontend** (`admin/src`):
- `index.css`: added `--color-sidebar`/`-active`/`-text` and
  `--color-avatar1/2/3(-bg)` tokens in the navy hue (258) — `client/`'s
  `AppShell`/avatar CSS references these var *names*, so the port only
  needed navy values, no selector changes.
- `components/AppShell.jsx`/`.css` (new): sidebar shell ported from
  `client/`'s, recolored — nav items are Cases (active), plus Members and
  Dashboard rendered as disabled "coming soon" placeholders, same
  convention `client/`'s AppShell uses for its own not-yet-built sections.
- `components/NewCaseModal.jsx` and `components/AssignMemberModal.jsx`
  (+ `.css`) (new): create-case and assign-to-case flows, both the existing
  `Modal` + `FormField`/`FormError` pattern. The assign modal has
  lawyer/client tabs and a real picker list (radio-style rows) sourced from
  `GET /members`, filtered to exclude already-assigned membership ids —
  never free text.
- `api/cases.js`, `api/members.js` (new): thin wrappers, same shape as
  `client/`'s `api/cases.js`.
- `utils/caseStatus.js`, `utils/format.js` (ported from `client/`, same
  status-color/avatar-tone logic — CSS var *names* already matched between
  the two apps' design systems, only the underlying navy values differ).
- `pages/CasesListPage.jsx`/`.css`, `pages/CaseDetailPage.jsx`/`.css`
  (new): list page has real page/page_size=50 pagination plus the new
  server-side status filter tabs; detail page has inline title editing, a
  status `<select>` (all four statuses always enabled, including reopening
  a closed case, per CLAUDE.md's no-timing-restriction rule), and two
  assignment columns (lawyers/clients) with per-row "remove" (native
  `window.confirm` before unassigning, since CLAUDE.md calls unassignment
  an immediate, full loss of access).
- `App.jsx`: added `/cases` and `/cases/:caseId` routes; root now redirects
  to `/cases` instead of rendering the old identity-dump Landing page —
  removed `pages/LandingPage.jsx`, mirroring what `client/` already did
  when its own Cases screens superseded its landing page.
- `components/DataTable.css`: added the clickable-row hover style
  `client/`'s copy already had (`onRowClick` support existed on the
  component already; the CSS for it didn't).

**Verified in a real browser** (no project `run` skill existed yet for
this repo, and `chromium-cli` wasn't available in this Windows
environment — used `puppeteer-core` pointed at the system-installed Chrome
instead, scripted from `scratchpad/browsercheck/check.js`): logged in as
the seeded `office_manager@casehub.example.com` demo account at
`demo.lvh.me:5174` against the real running `admin_api`/MySQL dev stack
(not mocks), then drove the full flow — status-filter tabs, created a real
case via the modal, edited its title, cycled its status including
closed→reopened, opened the assign modal, assigned the seeded demo lawyer
("Lior Lawyer"), unassigned them (confirm dialog auto-accepted), reloaded
the page to confirm the title/status changes actually persisted
server-side rather than only in local state, and confirmed the new case
appears back in the list. Zero console errors throughout. (Note: this left
two real "בדיקת דפדפן" test cases in the shared demo tenant's dev
database — there's no case-delete feature to clean them up with, by
design, since cases are treated as permanent records; flagged to the user
rather than reaching for a raw DB delete.)

**Learned / decided**:
- Don't trust a task brief's description of "existing" UI to extend
  without checking the actual files first — the brief's mental model of
  the app (Members/Dashboard screens, an "add member" modal) had drifted
  from what was actually built. Checking first and asking about the two
  real gaps (no admin sidebar shell, no members-list endpoint) up front
  avoided guessing wrong on a screen with no design-canvas reference to
  fall back on.
- Porting a themed component between the two apps is easy specifically
  because both design systems were built with the *same CSS variable
  names* and different values (per the earlier design-system session) —
  copying `client/`'s `AppShell.jsx`/`.css` verbatim and only adding
  navy-valued tokens with matching names in `admin/`'s `index.css` was
  enough; no selector or markup changes were needed.
- A list endpoint that's genuinely paginated (not the "fetch up to 200 and
  slice in the browser" shortcut used for a bounded per-person list) can't
  also support a client-side-only filter without breaking pagination math
  — surfaced by actually trying to build the status filter tabs against
  real page/page_size, not just by reading the requirement. Adding a
  small, backward-compatible optional query param to an already-tested
  endpoint (covered by a new test) was the correct fix, not a workaround.
- No Playwright/`chromium-cli` browser automation was preinstalled in this
  Windows dev environment; `puppeteer-core` against the already-installed
  system Chrome worked as a lightweight substitute (no ~150MB browser
  download) for driving a real verification pass. Worth recommending
  `/run-skill-generator` if browser verification becomes a recurring need
  in this repo, so the setup doesn't get re-derived each time.

## 2026-09-08 (5) — case permanent-delete, per the new CLAUDE.md deletion policy (same branch)

**Asked**: CLAUDE.md's Cases section had just been updated with a deletion
policy (office_manager can permanently delete a case, but only if it has
zero `WorkLogs`/`Documents` attached — otherwise rejected outright, close
the case instead, no override). Told to first commit the already-finished
Cases-screens work as its own commit (done in the prior session — commit
`8860be9`), then add this as a new feature on the same branch: a
`DELETE /cases/{id}` in `admin_api`, a confirm-then-delete action on
`CaseDetailPage` that surfaces the backend's rejection clearly, verify both
the happy path and the guard in a real browser, and use the happy-path
verification to clean up the two leftover test cases (#8/#9) from the
previous session's browser testing.

**Changed — backend** (`server/admin_api/routers/cases.py`):
- `DELETE /cases/{case_id}` — office_manager-only, looks the case up via
  the existing `get_tenant_scoped` (same as every other case route). Checks
  for any `WorkLog`/`Document` row referencing the case; if either exists,
  rejects with `400` and the message "This case has work logs or documents
  attached and can't be deleted — close it instead" (surfaces verbatim
  through the shared `{"error": ...}` response shape, same as every other
  endpoint). Otherwise deletes the case's `CaseAssignment` rows first (not
  "content" under the policy, just access grants — same reasoning
  `unassign` already uses) then the `Case` row itself, in one transaction.
- `server/tests/conftest.py`: added `make_work_log`/`make_document` fixture
  helpers (no route creates either yet — Phase 3/2 add-ons not built — so
  tests construct rows directly, same as every other fixture helper here).
- `server/tests/test_cases_admin.py`: empty-case delete succeeds and is
  actually gone (`404` on re-fetch); deleting a case with an assignment
  also succeeds (assignments aren't blocking content); a case with a
  `WorkLog` or a `Document` is rejected with `400` and stays fully intact
  (`200` on re-fetch); a lawyer gets `403`. `server/tests/
  test_tenant_isolation.py`: added the delete-across-tenants case (`404`,
  case B untouched). Full suite: 38/38 passing against the real
  `casehub_test` MySQL database.

**Changed — frontend** (`admin/src`):
- `api/cases.js`: added `deleteCase(caseId)`.
- `pages/CaseDetailPage.jsx`/`.css`: a "מחיקת תיק" danger-styled button
  (red outline, same `--color-error` token used elsewhere) in the detail
  header area. Click → `window.confirm` naming the case and stating the
  action is irreversible and content-gated (same confirmation mechanism
  already used for unassign, kept consistent rather than introducing a new
  pattern for one button) → on confirm, calls the endpoint and navigates
  back to `/cases` on success, or renders the backend's exact rejection
  text in the existing `FormError` banner and leaves the page untouched on
  failure.

**Verified in a real browser** (same `puppeteer-core` + system Chrome setup
as the previous session), against the live `demo.lvh.me` tenant, logged in
as the seeded office_manager:
- Happy path *and* cleanup in one motion: navigated to the two leftover
  test cases from last session (#8, #9 — both had zero work logs/documents
  by construction, since no upload/log-entry feature exists yet to have
  put anything on them), deleted each through the real UI, confirmed both
  redirect to `/cases` and are gone from the list (final count back to the
  original 7 seeded cases).
- Guard path: created a fresh case through the UI, then — since no
  work-log/document creation endpoint exists yet in either backend to do
  this through the app itself — inserted one `WorkLogs` row directly into
  the dev database via `mysql` in the `db` container (tenant/case ids read
  from the running app's own data first, not guessed). Clicked delete in
  the browser: the request came back `400`, the page stayed put, and the
  exact backend message rendered in the error banner. Then removed that
  one `WorkLogs` row the same way and deleted the case through the UI
  again — this time it succeeded, proving the guard reopens once the
  blocker is actually gone rather than being stuck permanently. Confirmed
  via direct DB query afterward that `work_logs` is empty and the case
  list is back to exactly the original 7 seeded cases — no test artifacts
  left behind on either side of this session's work.

**Learned / decided**:
- `CaseAssignment` has a plain (non-cascading) foreign key to `cases.id`,
  so a case with active assignments would fail at the database level on a
  bare `DELETE` — confirmed by reading the model rather than discovering
  it by trial and error, and handled by explicitly deleting the case's
  assignment rows first, consistent with the policy treating assignments
  as access grants rather than blocking "content."
- Verifying a rejection guard for a feature with no creation UI yet
  (work-log entry / document upload are both unbuilt Phase 3 items) still
  doesn't require waiting for those features — inserting one row directly
  against the real dev database (not the test database) to set up the
  precondition, then driving the actual guarded action through the real
  browser/API, tests the thing that's actually being built (the delete
  guard) without needing to fake or skip the verification.

## 2026-09-09 — Documents feature (full vertical slice, both backends, both frontends)

**Asked**: Build the complete Documents feature in one pass per CLAUDE.md's
already-fully-specified Documents section: local-disk storage abstraction,
upload with magic-byte file-type validation and a storage-quota plan guard,
folder-visibility-aware list/download, the two-stage trash (archive/restore/
permanent-delete) with its per-role authority matrix, folder reclassify,
same-filename replace-prompt, plus real screens in both `client/` and
`admin/`. New branch `feature/documents`.

**Blocker surfaced before writing code**: `feature/admin-case-screens`
(previous session's finished work) was pushed but had no PR and wasn't
merged into `master` — `gh pr create` even failed with "no commits between"
because local `master` itself was 3 commits behind `origin/master` (PR #5
had already merged it on GitHub, local git just hadn't fetched). Fixed by
fast-forwarding local `master` to `origin/master`, confirmed the 3 commits
were the already-merged PR, then branched `feature/documents` from a clean,
up-to-date `master` — flagged to the user rather than assuming either "needs
a new PR" or "definitely already merged."

**Decision surfaced before writing code**: where should the new
`storage.py`/`plan_limits.py` modules live — duplicated per app (matching
the existing pagination.py/errors.py precedent) or in `/server/shared`
(CLAUDE.md's stated scope for that package is narrower: table definitions +
tenant/auth logic only)? Asked the user; chose `/server/shared` — both are
genuine cross-app invariants (storage key format, plan limit numbers) rather
than per-app presentation choices, unlike pagination. Documented as a
deliberate, narrow extension in CLAUDE.md's Code quality section rather than
silently deviating from its literal text.

**Changed — schema/migration**:
- `shared/models/document.py`: dropped `visible_to` (CLAUDE.md: never had a
  defined purpose once `CaseAssignments` existed); added `archived_at`
  (two-stage trash), `file_size`/`original_filename`/`content_type` (storage
  quota, same-filename detection, correct download headers — implementation
  necessities the schema list didn't spell out column-by-column), `created_at`.
- Written as a **real incremental Alembic migration**
  (`a1b2c3d4e5f6_documents_archive_and_metadata.py`), not the project's
  earlier "wipe the DB and regenerate from scratch" pattern — that pattern
  only ever held because no real data existed yet; the demo tenant now has
  real case/assignment history worth preserving. Applied against the live
  dev DB via the host `.venv`'s Alembic, verified via `mysqldump --no-data`,
  `db/schema.sql` regenerated from the actual live schema (column order and
  all) rather than hand-typed.
- `tests/conftest.py`'s `make_document` extended with the new required
  columns (folder_type/original_filename/file_size/archived_at params,
  sensible defaults) — every existing caller (case-delete-guard tests) kept
  working unchanged.

**Changed — backend, `shared/`**:
- `storage.py`: `save_file`/`get_file_url`/`delete_file`, local disk under
  `STORAGE_ROOT/tenant_id/case_id/<uuid><ext>` — the original filename is
  never used in the path (collision/traversal safety), only stored as a
  column for display. `get_file_url` returns an absolute path today (used
  directly in `FileResponse`); a cloud backend swap would only touch this
  one function's return value.
- `plan_limits.py`: `check_plan_limit(tenant_id, resource_type, db,
  additional=0)`, currently wired up for `"storage_bytes"` only (extensible
  to a future lawyer-count check without touching call sites). Hardcoded
  Free/Pro/Enterprise GB caps (1/20/100GB — CLAUDE.md didn't specify exact
  numbers, picked reasonable defaults). Archived documents still count
  against quota (sums every `Document.file_size` regardless of
  `archived_at`) — only a permanent delete actually frees it.

**Changed — backend, `client_api`** (primary owner of upload/lawyer/client
document interaction):
- `core/file_validation.py`: `detect_file_type()` — stdlib-only magic-byte
  sniffing (no `python-magic`/`filetype` dependency): fixed signatures for
  PDF/PNG/JPEG, and for DOCX (a zip file, so a bare `PK\x03\x04` signature
  alone can't distinguish it from any other zip) actually opens the archive
  and checks for `word/document.xml`. 50MB per-file cap.
  `python-multipart==0.0.20` added to `requirements.txt` (needed for
  FastAPI's `File`/`Form`).
- `routers/documents.py`: `POST /cases/{id}/documents` (upload — role/folder
  permission check, closed-case block, size/type validation, plan-quota
  check, same-filename-conflict 409 unless `confirm_replace=true`, in which
  case the old active document is archived and the new upload becomes
  active), `GET` (list, folder-visibility-filtered — client forced to the
  client folder, 403 if they explicitly ask for internal; client also 403'd
  from `archived=true`), `GET /{id}/download` (client 404s on internal or
  archived docs — indistinguishable from "doesn't exist" rather than a
  403, so an unauthorized client can't even confirm such a document exists),
  `POST /{id}/archive` (client: own uploads only; lawyer: any document on
  the case), `POST /{id}/restore` (lawyer-only), `PATCH /{id}` (reclassify,
  lawyer-only). Every route resolves the case through the same
  `_get_assigned_case` helper `cases.py` already established (tenant-scoped
  lookup, then explicit `CaseAssignment` check) — no bare id lookups.
  `AuditLogs` written on upload/archive/restore, matching CLAUDE.md's list
  of logged actions exactly (not on download or reclassify, which aren't in
  that list).

**Changed — backend, `admin_api`** (office_manager oversight):
- `routers/documents.py`: same list/download/archive/restore/reclassify
  shape, but no `CaseAssignment` check (office_manager has automatic
  tenant-wide case access) and no folder restriction (sees both folders
  always). Added `DELETE /{id}` — permanent delete, `office_manager`-only,
  400s unless the document is already archived (CLAUDE.md: only reachable
  *from inside* the archive), erases both the DB row and the on-disk file
  via `storage.delete_file`, logs `document_permanently_deleted`.

**Changed — frontend, `client/`**:
- `api/client.js`: added `apiUpload` (multipart, no JSON `Content-Type` so
  the browser sets its own boundary) and `apiDownload` (reads the real
  filename off `Content-Disposition` rather than guessing it from the URL).
- `api/documents.js`, `components/DocumentsPanel.jsx`/`.css` (new): replaces
  the "coming soon" placeholder on `CaseDetailPage`. Client-folder tab
  always shown, internal tab lawyer-only (display convenience — real
  enforcement is 100% server-side per the routes above). Upload via a
  hidden file input; same-filename 409 surfaces as a native `window.confirm`
  (matching the existing unassign/delete confirmation pattern elsewhere in
  this app rather than inventing a new modal), confirming resubmits with
  `confirm_replace=true`. Archive button shown to clients on every row
  (not just their own) — ownership is enforced server-side with a clear
  inline error on a 403, the same pattern already used for case-level 403s,
  rather than the frontend trying to fragile-match "is this my own upload"
  without an owned-membership-id anywhere in its session state.
- `utils/format.js`: added `formatFileSize`.

**Changed — frontend, `admin/`**:
- `api/documents.js`, `components/DocumentsPanel.jsx`/`.css` (new): office
  manager's oversight panel on `CaseDetailPage` — folder filter chips
  (הכל/לקוח/פנימי), archive toggle, and from inside the archive: restore
  and a red "מחיקה לצמיתות" (permanent delete) button gated behind
  `window.confirm`, matching the case-delete confirmation pattern already
  established on this same page. No upload UI here — that's the
  lawyer/client portal's job.
- `utils/format.js`: added `formatFileSize`.

**Environment fix, unrelated to app code**: `npm run build`/`npm run dev`
were both failing on this machine with Windows Smart App Control rejecting
Vite 8's native Rolldown bundler binary as unsigned (confirmed via the
`Microsoft-Windows-CodeIntegrity/Operational` event log — Event ID 3077).
Asked the user how to proceed rather than either silently working around it
or blocking on it; chosen fix: downgraded `vite` (`^8.2.2` → `^7.1.12`) and
`@vitejs/plugin-react` (`^6.1.0` → `^4.7.0`, the last major line that
doesn't require Vite 8's Rolldown-oriented peer deps) in both `client/` and
`admin/`, reinstalled `node_modules`. Pure tooling downgrade, zero app-code
changes; both apps build and run cleanly afterward regardless of Smart App
Control's state.

**Bug found and fixed via real-browser verification (not caught by pytest
or a build)**: the client-side download flow's real filename ("scan.png")
was coming back as the fallback "download" (browser then guessed an
extension from the blob's MIME type, e.g. "download.png") instead of the
real name. Cause: `Content-Disposition` isn't one of the small set of
"safe" response headers browsers expose to `fetch()`'s JS by default —
CORS has to explicitly list it via `expose_headers`. Added
`expose_headers=["Content-Disposition"]` to both apps' `CORSMiddleware`
config. This is exactly the class of bug the "verify in a real browser, not
just curl/pytest" rule exists to catch — curl sees every response header
unconditionally, so this would never have surfaced through the API tests
alone.

**Verified**: full pytest suite (66/66 — 28 new document tests across
`test_documents_client.py`/`test_documents_admin.py`, plus 4 new document
cases added to `test_tenant_isolation.py`: cross-tenant upload, list,
archive all rejected with 404). Real-browser pass (Playwright/Chromium,
reusing the cached browser binary from a prior session's Playwright
install; installed the `playwright` Python package fresh into `.venv`)
against the actual running Docker stack and `demo.lvh.me`, driving three
real sessions back-to-back:
- **Lawyer** (a throwaway `test.lawyer.docs@example.com` account, added and
  assigned to a real demo case via real API calls, not fixtures — cleaned
  up afterward): uploaded a real PDF to internal and a real PNG to client,
  downloaded the PNG (confirmed the exact right filename after the CORS
  fix), archived it, viewed the archive, restored it, reclassified it to
  internal, then the same-filename-replace flow end-to-end (409 on the
  first re-upload, native confirm dialog with the exact server message,
  `confirm_replace=true` resubmission succeeding and the old file landing
  in the archive).
- **Client** (the seeded demo client, already assigned to this case):
  confirmed by direct DOM query that the internal tab and archive-toggle
  button are both absent (count 0), uploaded their own document, archived
  it successfully.
- **Office manager** (seeded demo account): saw both folders' documents
  with no assignment needed, archived one, viewed the archive (folder
  chips, restore/permanent-delete buttons), permanently deleted one with
  the confirm dialog, confirmed the row count dropped and it's actually
  gone.
- Zero console errors throughout except one expected, benign one (a logged
  409 network response for the intentional same-filename-conflict request,
  not a JS exception).
- All throwaway test data (the extra lawyer identity/membership/assignment,
  every test document row and its on-disk file, the audit log rows)
  cleaned up directly against the dev DB afterward — the demo tenant is
  back to exactly its pre-session state.

**Learned / decided**:
- `office_manager` restore authority: CLAUDE.md's Documents section text
  said "any lawyer assigned to the case can restore" without mentioning
  office_manager, but this task's brief explicitly said "restore
  (lawyer/office_manager only)" — went with the brief (broader authority,
  consistent with office_manager's archive/permanent-delete authority
  already being the broadest of the three roles) and updated CLAUDE.md's
  text to match, rather than silently building one and documenting the
  other.
- Closed-case blocking was scoped narrowly to uploads only, per CLAUDE.md's
  literal text ("blocks new Documents/WorkLogs from being *added*") —
  archive/restore/reclassify/permanent-delete on a closed case's existing
  documents are all still allowed. `WorkLogs`' stricter "locked entirely
  once closed" rule doesn't have an equivalent stated for Documents, so it
  wasn't invented by analogy.
- A client's archive button is shown for every document in their own
  folder view, not just ones the frontend can prove they own — there's no
  membership id anywhere in the client's session state to compare against
  (`/auth/me` only returns identity fields), and CLAUDE.md is explicit that
  frontend checks are UX convenience only. Simpler and equally correct to
  let the real 403 do the work and surface it inline, same as the existing
  case-level 403 handling elsewhere in this app.
- The Smart App Control / Rolldown build failure was a genuine, unplanned
  environment regression discovered mid-session (this exact machine had
  `npm run build` working cleanly as of the 2026-09-07 session) — worth
  remembering that a previously-green build/dev command on this machine
  isn't guaranteed to stay green between sessions if Windows security
  policy changes underneath it.

## 2026-09-09

**Asked**: Set up the missing `/docs` deliverables (OpenAPI export, Postman
Collection, ERD) as a repeatable, re-runnable process rather than a one-off
manual export, since these need to be regenerated after every future feature.
Branch `feature/docs-export`.

**Changed**:
- `server/scripts/export_openapi.py` — imports `client_api.main:app` and
  `admin_api.main:app` directly and calls `.openapi()` on each; writes
  `docs/openapi_client.json` / `docs/openapi_admin.json`. No server needs to
  be running and no live DB connection is made (SQLAlchemy's `create_engine`
  is lazy), so it works identically with Docker up or down.
- `server/scripts/generate_erd.py` — imports `shared.models` (populates
  `Base.metadata` via the real `ForeignKey` columns already on every model)
  and feeds it straight to `eralchemy2.render_er()`; writes `docs/erd.png`
  and a text-diffable `docs/erd.mmd.md` (Mermaid ER syntax).
- `server/scripts/generate_postman.sh` — converts both OpenAPI files into
  Postman collections via Postman's own official `openapi-to-postmanv2`
  npm CLI (pinned `6.3.3`, run through `npx` so no permanent install is
  needed); writes `docs/postman_collection_client.json` /
  `docs/postman_collection_admin.json`.
- `server/scripts/export_docs.sh` — one-command orchestrator running all
  three in order.
- `server/scripts/requirements-docs.txt` — `eralchemy2`/`pygraphviz` pinned,
  kept separate from `server/requirements.txt` since neither app needs them
  at runtime, only doc generation does.
- README: new "Regenerating /docs" section documenting the one-time setup
  and the single re-run command, so a future session doesn't need this
  conversation's context to refresh these files.
- Generated the actual files into `/docs` for the current codebase state
  (13 client_api paths, 18 admin_api paths, ERD covering all 11 tables).

**Learned / decided**:
- `eralchemy2` (SQLAlchemy 2.0-compatible fork of the original `eralchemy`)
  needs Graphviz's `dot` engine to render an image, but its `pygraphviz`
  dependency shipped a wheel with `dot` bundled for this
  platform/Python version — no separate system-level Graphviz install was
  needed. Worth re-checking if this ever breaks on a different machine/OS;
  the fallback is installing Graphviz separately and ensuring `dot` is on
  PATH.
- Passed `Base.metadata` (a `MetaData` instance) directly into
  `eralchemy2.render_er()` in-process, rather than driving it via its CLI's
  `-i` flag (which expects a DB URI or an `.er` file) — the CLI has no clean
  way to point at "a SQLAlchemy declarative Base living in a Python module,"
  so the reusable, code-importable path is a plain script, same pattern
  already used for the OpenAPI export.
- Chose `openapi-to-postmanv2` (Postman's own official converter, high
  download count, actively maintained) over the Postman desktop app's manual
  import/export UI specifically because it's scriptable — the whole point of
  this task was making the export re-runnable without a human driving a GUI.

## 2026-09-09 (continued)

**Asked**: Build the full WorkLogs feature — backend and frontend, both
apps — in one pass, sized like the Documents session. Branch
`feature/worklogs`. Manual entry, list, edit, delete on `client_api`
(lawyer-only, any lawyer assigned to the case can edit/delete any entry,
every edit/delete audited, locked once the case is closed); `admin_api` gets
the same edit/delete authority plus read access for oversight; frontend
panels on both apps' case-detail screens, replacing `client/`'s "coming
soon" placeholder; confirm a client account sees no trace of the feature.
Re-run the `/docs` export as a standard last step.

**Changed — backend, shared**:
- No new model needed — `WorkLog` already existed (Phase 1's "create every
  table upfront" rule) with exactly the columns CLAUDE.md specifies
  (`tenant_id`, `lawyer_id`, `case_id`, `date`, `hours` as `Numeric(6,2)`,
  `description`, `source`).
- `client_api/core/case_access.py` (new): extracted `get_assigned_case()` out
  of `documents.py`'s private `_get_assigned_case` — work_logs.py needed the
  exact same "resolve tenant-scoped, then require an explicit
  CaseAssignment" check, so this was the second real caller CLAUDE.md's
  "extract before a third copy" rule is about. `documents.py` now imports it
  too instead of keeping its own copy.

**Changed — backend, `client_api`**:
- `schemas/work_logs.py`, `routers/work_logs.py` (new), registered in
  `main.py`. `POST`/`GET`/`PATCH`/`DELETE` all gated
  `require_role(UserRole.LAWYER)` only — no `CLIENT` in the allowed-roles
  list at all, the literal enforcement of "WorkLogs are never client-visible,
  no route should expose them to a client role." Create/edit/delete all
  check `case.status == CaseStatus.CLOSED` and reject with 400 — "locked
  entirely once the case is closed" applies to all three mutations, not just
  creation (a stricter rule than Documents, which only blocks new uploads on
  a closed case, not archive/restore/reclassify of existing ones — CLAUDE.md
  states this WorkLogs rule explicitly, so it wasn't invented by analogy).
  Edit/delete both write an `AuditLog` row (`work_log_edited`/
  `work_log_deleted`, target `work_log:<id>`) — action happened + who + when
  only, no before/after value tracking, per CLAUDE.md's explicit scope for
  this log.
- Every lawyer assigned to the case can edit/delete any entry on it, not
  just their own — same broad, collaborative authority `Documents` already
  established, re-used rather than re-derived.

**Changed — backend, `admin_api`**:
- `schemas/work_logs.py`, `routers/work_logs.py` (new), registered in
  `main.py`. `GET` (list, `office_manager`-only, no `CaseAssignment` check —
  same automatic-access oversight pattern as `admin_api`'s Documents list)
  plus `PATCH`/`DELETE` with the identical closed-case lock and audit-log
  write as the lawyer-facing route. No `POST` — manual entry stays the
  lawyer/client portal's job, `admin_api` is oversight only, per this
  session's own scope (CLAUDE.md's text doesn't explicitly rule out
  office_manager creating entries, but the task narrowed it to "edit/delete
  ... plus read access," so no create endpoint was built here).

**Changed — tests**:
- `tests/test_work_logs_client.py` (11 tests), `tests/test_work_logs_admin.py`
  (5 tests): manual creation (success, client-403, unassigned-lawyer-403,
  closed-case-400, non-positive-hours-422), lawyer-edits-colleague's-entry
  (+ audit row asserted), edit/delete blocked on a closed case,
  lawyer-deletes-colleague's-entry (+ audit row), office_manager
  list-without-assignment, office_manager edits/deletes any entry (+ audit
  row with the right `user_id`), lawyer 403'd off the admin route.
- `tests/test_tenant_isolation.py`: two more cases —
  lawyer-cannot-create-work-log-on-another-tenant's-case (404, the case_id
  itself resolves through `get_tenant_scoped` before assignment logic runs)
  and office_manager-cannot-list-another-tenant's-work-logs (404).
- Fixed 3 initial test-assertion failures against the real running suite
  (not assumed passing): `hours` comes back as `"4.00"`/`"3.50"`/`"6.00"`
  from MySQL's `Numeric(6,2)`, not `"4"`/`"3.5"`/`"6"` — my first draft
  assumed Python `Decimal`'s default string form, forgetting the column's
  actual scale. Full suite: 83/83 passing after the fix (up from 66 before
  this session, +17 for WorkLogs).

**Changed — frontend, `client/`**:
- `api/work_logs.js` (new): `listWorkLogs`/`createWorkLog`/`updateWorkLog`/
  `deleteWorkLog`, same single-page-covers-it `page_size=200` shortcut
  `documents.js` already uses for one case's list.
- `components/WorkHoursPanel.jsx` + `.css` (new): total-hours summary,
  an inline "+ רישום שעות" create form (date/hours/description), and a list
  with per-row inline edit (swaps the row into its own small form) and
  delete (native `confirm()`, matching the existing
  unassign/delete-case/archive confirmation pattern already used elsewhere
  in this app). Both create and every row's edit/delete are hidden (not just
  disabled) when the case is closed, with the same `documents-closed-note`
  banner style Documents already uses for its own closed-case messaging.
- `pages/CaseDetailPage.jsx`: replaced the static "מעקב שעות בקרוב" (coming
  soon) placeholder with `{canSeeWorkHours() && <WorkHoursPanel ... />}` — a
  second `getStoredRole() === 'lawyer'` check, deliberately separate from
  `canSeeInternalFolder()` even though today they'd always agree, since
  they're gating two independently-specified things (which document folder
  vs. whether the section exists at all) and CLAUDE.md is explicit that
  WorkLogs get a *stronger* rule than Documents (not rendered at all, vs.
  Documents' folder-level tab hiding) — collapsing them into one shared
  check would have obscured that the two are different guarantees that only
  happen to currently produce the same boolean. This is still UX-only, same
  disclaimer as `canSeeInternalFolder()`: a client hitting the API directly
  gets a real 403, enforced by `require_role` never listing `CLIENT` at all
  for this router.

**Changed — frontend, `admin/`**:
- `api/work_logs.js` (new): same shape as `client/`'s, minus `createWorkLog`
  (no create UI here, oversight only).
- `components/WorkHoursPanel.jsx` + `.css` (new): office_manager's oversight
  panel on `CaseDetailPage` — every work log on the case with no assignment
  needed, total-hours summary, inline edit/delete reusing the same row/form
  markup pattern as `client/`'s panel (kept as two independent
  implementations per CLAUDE.md's "not shared across the two frontends"
  rule, not a copy-paste accident). No create button, matching this
  session's scoped authority.

**Bug found and fixed via real-browser verification (not caught by pytest or
a build)**: the hours `<input type="number">` had `min="0.01" step="0.25"`.
HTML5's step-mismatch validation computes valid values from `min` as the
step base, not from 0 — so with `min="0.01"`, the only browser-accepted
values are 0.01, 0.26, 0.51, 0.76, … (never a clean number like 3.5),
silently blocking every real submission with a native "the two nearest
valid values are 3.26 and 3.51" tooltip and no network request ever firing.
Fixed by changing `min` to `"0.25"` (a real multiple of the 0.25 step) in
both apps' create and inline-edit hour inputs. `curl`/pytest never exercise
HTML5 constraint validation at all (it's a browser-only gate before the
`fetch()` call is even made), so this is exactly the class of bug the
"verify in a real browser" rule exists to catch — the backend's own
`gt=0, le=24` Pydantic validation was always correct and never saw this
input rejected.

**Verified**: full pytest suite (83/83). Real-browser pass (Playwright/
Chromium, reusing the already-installed browser binary) against the actual
running Docker stack and `demo.lvh.me`, driving three real sessions against
a shared demo case (case #4, already assigned to the seeded demo client from
prior session data):
- **Lawyer** (a throwaway `test.lawyer.wh@example.com` account, registered,
  added, and assigned to the case via real API calls, not fixtures):
  created a real entry, inline-edited its hours, deleted it (confirm-dialog
  handled), then created a second entry left in place for the
  office_manager check.
- **Client** (the seeded demo client, already assigned to this same case):
  confirmed by DOM query for the panel's own `.detail-hours-card` class
  (not a plain text search — the sidebar's disabled "שעות עבודה" nav label
  shares the same text and would have been a false positive; caught this
  mid-verification and fixed the check rather than trusting the first,
  wrong "count=1" result) that the panel is not rendered at all — count 0.
- **Office manager** (seeded demo account): saw the lawyer's entry on the
  case with no assignment of their own, edited its hours, deleted it,
  confirming the empty state afterward.
- Zero console/page errors across every step.
- All throwaway data (the extra lawyer identity/membership/assignment, every
  test work-log row) cleaned up directly against the dev DB afterward.

**Learned / decided**:
- CLAUDE.md's WorkLogs closed-case rule ("locked entirely once the case is
  closed") is textually stronger than its Documents rule ("blocks new
  Documents ... from being added") — read literally rather than by analogy,
  since the two features' text actually differs on this point and Documents'
  archive/restore/reclassify staying open on a closed case was itself a
  deliberate decision from the prior session, not an oversight to copy.
- Extracting `get_assigned_case()` into `client_api/core/case_access.py` now
  (rather than leaving `work_logs.py` with its own copy) was judged as
  exactly the "if a pattern appears twice, extract before a third" case from
  CLAUDE.md's Code quality section — `documents.py` was the first copy,
  `work_logs.py` would have been an identical second, so extracting now
  rather than waiting for an unlikely third caller.
- The `min`/`step` HTML5-validation bug is worth remembering for any other
  numeric input added later with a non-1 `step`: `min` must itself be a
  multiple of `step`, or the browser's implied valid-value sequence starts
  from the wrong base and silently rejects otherwise-sane input.

## 2026-09-09 (later) — office_manager admin gaps: members lifecycle, branding, subscription/plan

**Asked**: Build the remaining Phase 2 office_manager administrative
features called out in CLAUDE.md's Build status gap list: completing member
management (deactivate, reactivate-on-re-add, hand password reset), a
branding settings screen (direct `Tenants` columns), and a subscription/plan
view with usage vs. plan limits plus a self-service plan switch. Backend and
frontend together, on a new `feature/office-admin` branch, same shape as the
prior WorkLogs/Documents sessions.

**Changed**:
- `shared/membership.py`'s `get_current_membership` now filters on
  `Membership.active.is_(True)` — previously a deactivated membership was
  invisible to list views but still fully functional for every route gated
  by `require_role`, which would have made "deactivate a member" cosmetic
  rather than a real access revocation. Also added the same `active` filter
  to both `client_api`'s and `admin_api`'s `/auth/login` membership lookups,
  so a deactivated person is rejected at login too, not just after.
- `shared/plan_limits.py`: added `PLAN_LAWYER_LIMITS` (Free 3 / Pro 15 /
  Enterprise 50) alongside the existing storage table, a `"lawyer_count"`
  branch in `check_plan_limit`, and a new `get_plan_usage(tenant_id, db)`
  returning everything the subscription screen needs (plan + both
  used/limit pairs) — kept in `shared` (not admin_api) specifically so the
  screen's displayed numbers can never drift from what `check_plan_limit`
  actually enforces, same one-source-of-truth reasoning already documented
  there for storage.
- `admin_api/routers/members.py`: `GET /members` gained an `include_inactive`
  query param (default off, so every existing caller/picker is unaffected);
  `POST /members` now checks for an existing *inactive* row by
  identity+tenant before inserting and reactivates it in place (setting the
  new role) instead of racing the unique constraint with a fresh insert —
  this is what makes "re-add a removed person by email" work per CLAUDE.md's
  Memberships note; added `POST /members/{id}/deactivate` (blocks
  self-deactivation, logs an `AuditLog` row) and
  `POST /members/{id}/reset-password` (hashes the new password, bumps
  `token_version` so old sessions actually die, logs an `AuditLog` row).
  Adding/reactivating a `LAWYER` role now runs through
  `check_plan_limit(..., "lawyer_count", ..., additional=1)` first.
- New `admin_api/routers/tenant.py` (`GET`/`PATCH /tenant`) for branding —
  direct `name`/`logo_url`/`primary_color` columns, `subdomain`/`active`
  deliberately not editable here (subdomain is fixed at signup, `active` is
  the super_admin-only lockout switch).
- New `admin_api/routers/subscriptions.py` (`GET /subscription`,
  `POST /subscription/plan`) — the former just calls `get_plan_usage`; the
  latter deactivates the current active `Subscription` row (`end_date` =
  today) and inserts a new active one for the chosen plan, no payment step,
  matching CLAUDE.md's "resource gate, not a commerce system." Rejects
  switching to the plan already active.
- Frontend (`admin/`): new `MembersPage` (role tabs + a "show also removed"
  toggle reusing the existing tabs/card visual language, `AddMemberModal`,
  `ResetPasswordModal` — both built on the existing `Modal`/`FormField`
  pattern), new `BrandingPage` (form + live preview card) and
  `SubscriptionPage` (usage bars + a 3-plan switch grid), both under a new
  shared `SettingsTabs` sub-nav rather than two separate sidebar entries.
  Enabled the previously-disabled "אנשי צוות" sidebar item and added a new
  "הגדרות משרד" one. Extended `Form.css` to style `<select>` the same as
  `<input>` (only inputs were styled before, and the new Add-Member/plan
  forms are the first to need a select), and `formatFileSize` to add a GB
  tier (previously topped out at MB, fine for per-file sizes but not a
  100GB-cap storage-quota display).
- Added 22 new pytest tests (`test_members_admin.py` additions,
  `test_tenant_admin.py`, `test_subscriptions_admin.py`) covering:
  deactivate excludes-from-list/blocks-self/actually-revokes-login-access;
  re-add-reactivates-same-row-not-a-new-insert; lawyer-count plan-limit
  rejection; password-reset-changes-what-future-logins-accept (verified via
  a real `client_api` login call, old password now rejected); branding
  get/update/tenant-isolation/role-guard/invalid-color-422; subscription
  usage numbers, plan switch old-row-deactivated-new-row-active,
  reject-same-plan, and the explicit "downgrade doesn't touch existing
  lawyers" grandfathering behavior. Full suite (121 tests) green.
- Re-ran `server/scripts/export_docs.sh` (OpenAPI ×2, ERD, Postman ×2) —
  `admin_api` grew from 20 to 25 documented paths.
- Browser-verified end-to-end as the seeded office_manager (Playwright
  driving the already-running Vite dev servers, since `chromium-cli` wasn't
  available in this environment): add member (incl. the expected
  already-a-member 400), deactivate, toggle "show removed", re-add-by-email
  reactivation, password reset, branding edit + reload-persists, and a full
  Free→Pro→Free plan switch with usage bars updating live.

**Learned / decided**:
- Found and fixed a real bug during browser verification, not just a test
  gap: `check_plan_limit(tenant.id, "lawyer_count", db)` was called without
  `additional=1` at the one call site, so the count comparison always
  compared *pre*-insert usage against the limit — a 4th lawyer add on Free
  compared 3 (already added) against a limit of 3 and passed, when it
  should have compared 3+1. The existing `storage_bytes` call site already
  passed `additional=len(content)` correctly; this was a copy-paste gap in
  the new call, not a design flaw in `check_plan_limit` itself. Caught by
  the `test_add_member_rejects_lawyer_over_plan_limit` test, not the
  browser — worth noting since it's exactly the kind of off-by-one a
  resource-gate helper needs a test for, not just eyeballing.
- Also found, only via the actual browser screenshot (no automated test
  would have caught this): the subscription usage bars rendered as `"3 / 1"`
  instead of `"1 / 3"`, and storage as `"B / 1.00 GB 0"` — a Unicode
  bidi-reordering bug, not a logic bug. Plain digits and `/` have no strong
  directional character, so left inside the page's `dir="rtl"` root they
  silently reorder to match paragraph direction. Fixed by wrapping the
  fraction in an explicit `<span dir="ltr">`. General lesson for the rest of
  this RTL app: any place a raw "X / Y" or "X of Y" number pair gets
  rendered needs the same explicit `dir="ltr"` treatment, not just numbers
  mixed with Hebrew words (Hebrew words are themselves strong-RTL and
  anchor the direction correctly; it's specifically weak/neutral runs like
  bare numbers and slashes that are at risk). Also wrapped an interpolated
  Latin name inside a Hebrew success message in `<bdi>` for the same class
  of defensive reason, though that particular instance wasn't confirmed
  broken in the screenshot.
- Deliberately did not build a `super_admin` override for one tenant's plan
  limits (CLAUDE.md explicitly says this is "reasonable to mention if it
  comes up, but isn't built as a feature") — out of scope here.
- Deliberately kept branding/subscription as two routes (`/settings/branding`,
  `/settings/subscription`) under one new `SettingsTabs` sub-nav component
  rather than either two separate sidebar items or one page with internal
  tab state — matches the sidebar's existing one-item-per-concept density
  without needing a third top-level nav slot for what's really one "office
  settings" concern.

## 2026-09-09 (later still) — full super_admin role, backend + frontend (branch `feature/super-admin`)

**Asked**: Build the entire `super_admin` experience in one pass — the last
entirely-unbuilt role. Cross-tenant firm list with per-firm plan/status/
lawyer-count/case-count, suspend/reactivate, platform-wide aggregate stats,
and the `admin/` frontend's hostname-based branching between the tenant CMS
and the platform dashboard. Confirm in a real browser that suspending a
tenant locks it out and that `super_admin` can never reach case/document
data.

**Changed**:
- `shared/platform.py` (new): `require_super_admin`, a `get_current_identity`
  -based dependency checking `Identities.is_super_admin` directly — no
  `Memberships` row involved at all, since `super_admin` can't be one (per
  CLAUDE.md's Multi-tenancy architecture). This is the one gate every
  platform route sits behind.
- `admin_api/routers/platform.py` (new, prefix `/platform`): `GET /tenants`
  (every `Tenant` — deliberately *not* filtered to `active = True`, since a
  super_admin has to see suspended firms to reactivate them — each row
  joined with its active `Subscription.plan`, active-lawyer count, and case
  count), `POST /tenants/{id}/suspend` / `/reactivate` (flip `Tenants.active`
  — suspend relies on `get_current_tenant`'s existing `active = True` filter
  to do the actual lockout, no new enforcement needed), and `GET /stats`
  (platform-wide totals: tenants, active tenants, lawyers, cases). None of
  this goes through `get_current_tenant`/`get_tenant_scoped` — both assume
  exactly one tenant in request scope, which doesn't apply here — plain
  `db.query(Tenant)...` is the "clearly separate, explicitly named code
  path" CLAUDE.md calls for. Auth routes (`/auth/platform-login`) and the
  `platform.<BASE_DOMAIN>` host check already existed from the Phase 1 auth
  work, so this session was purely the query/CRUD layer plus the frontend.
- Registered the new router in `admin_api/main.py`.
- `server/tests/test_platform_admin.py` (new, 8 tests): platform-login host/
  role gating, an `office_manager` getting 403 on every `/platform/*` route,
  the tenant list's per-firm aggregate numbers (including that a suspended
  tenant still appears in the list), suspend/reactivate round-trip, **the
  actual lockout mechanism** — suspending a tenant makes its own
  `office_manager`'s `GET /tenant` 404 immediately — aggregate stats
  correctness, and an OpenAPI-introspection check that no `/platform/*` path
  mentions `case` or `document`. Also added an optional `is_super_admin`
  param to `conftest.make_identity` (defaults `False`, so every existing
  call site is unaffected).
- `admin/src/utils/host.js` (new): `isPlatformHost()` — the frontend's
  mirror of the backend's `PLATFORM_HOST` check, just comparing
  `window.location.hostname`'s first label to `"platform"`.
- `admin/src/App.jsx`: the route tree now branches on `isPlatformHost()` at
  the top level into two disjoint sets of routes — platform gets
  `/login` (→ `PlatformLoginPage`) and `/dashboard` only; every other
  hostname keeps the existing office_manager routes unchanged. Nobody
  cross-logs into the other's routes, matching CLAUDE.md's "each role logs
  into exactly one frontend app" — here that boundary is hostname, not role.
- `admin/src/pages/PlatformLoginPage.jsx` (new): mirrors `LoginPage.jsx`
  but posts to the new `platformLogin()` call and has no signup link (no
  self-service platform-staff signup, per CLAUDE.md).
- `admin/src/components/PlatformAppShell.jsx` (new): structurally identical
  to `AppShell.jsx` (same `AppShell.css` classes, reused as-is rather than
  duplicated) but with a single "לוח בקרה" nav item instead of
  cases/members/settings — `super_admin` only ever has the one screen.
- `admin/src/pages/PlatformDashboardPage.jsx` + `.css` (new): a stat-card
  row (total/active tenants, total lawyers, total cases) above a
  paginated `DataTable` of every firm (plan chip, lawyer/case counts,
  active/suspended chip, suspend-or-reactivate button per row) — reused
  `DataTable`'s built-in Loading/Error/Empty handling and the existing
  `cases-*`/`member-*` CSS classes (table card, pagination, chips) rather
  than inventing new ones, plus one new chip class
  (`.tenant-status-suspended`, error-toned — a suspension is a full,
  intentional lockout, so it reads as more severe than a member's plain
  "inactive" gray) and a `.platform-stats-grid` card row.
- `admin/src/api/platform.js` + `auth.js`'s new `platformLogin()` (new):
  thin wrappers over the five new/existing endpoints, same shape as every
  other `api/*.js` file.
- Re-ran `server/scripts/export_docs.sh` — `docs/openapi_admin.json` picked
  up the 5 new `/platform/*` + existing `/auth/platform-login` paths (29
  total now), both Postman collections regenerated from it.

**Verified in browser** (Playwright against the already-running dev
servers/containers, `platform.lvh.me:5174` and a scratch tenant): logged in
as the seeded `super@casehub.example.com` super_admin at the platform
address — dashboard renders real stats and the full firm list including the
`Demo Firm`/`Office One` tenants created in earlier sessions. Signed up a
brand-new firm as a control, confirmed its `office_manager` could reach
`/cases` normally, then suspended that same tenant from the platform
dashboard — the office_manager's page immediately broke with "Tenant not
found" on reload (`GET /tenant` → 404, confirming `get_current_tenant`'s
existing `active = True` filter is doing the actual lockout, not just a UI
flag) — reactivating restored access on the next reload. Separately, reused
the super_admin's own session cookie (scoped to `.lvh.me`, so the browser
sends it to any tenant subdomain) to hit `demo.lvh.me:8001/cases` and
`/documents` directly, bypassing the UI entirely: `403`
("You don't have access to this firm") and `404` respectively — confirmed
`super_admin` has no path to case/document content anywhere in `admin_api`,
not just that the frontend doesn't offer one.

**Learned / decided**:
- The heaviest-looking part of this feature — the platform-vs-tenant login
  split, the `PLATFORM_HOST` check, `Identities.is_super_admin`, and the
  seed.sql bootstrap row — turned out to already exist from the Phase 1 auth
  work. This session was genuinely just the query/CRUD layer
  (`/platform/*`) plus the frontend; worth remembering next time a role
  feels "entirely unbuilt" that its auth plumbing may already be half-built
  as a side effect of an earlier phase.
- Confirmed the suspend mechanism needs zero new enforcement code: because
  `get_current_tenant` already filters `Tenant.active.is_(True)` for every
  tenant-scoped request (Phase 1), flipping the flag from `/platform/*` is
  sufficient on its own — no separate "is this tenant suspended" check
  needed anywhere else in either backend. This is exactly the "single
  source of truth" pattern CLAUDE.md already argues for elsewhere
  (`Tenants` has no `plan` column for the same reason), just showing up
  again for free here.
- `/platform/tenants` deliberately omits the `active = True` filter that
  every other tenant query in the codebase applies — the one legitimate
  exception to "always filter by tenant status," since the whole point of
  the list is to be able to find and reactivate a suspended firm.

## 2026-09-09 (later still, again) — office_manager's own dashboard + CMS data export (branch `feature/admin-dashboard-export`)

**Asked**: Build office_manager's own per-firm dashboard with real data
(replacing the still-unbuilt "בקרוב" placeholder nav item) and a CMS data
export, backend and frontend together, in one pass. Explicit call-out from
CLAUDE.md to route the export through the same tenant-scoped query path as
everything else, since export queries are exactly the kind most likely to
accidentally skip `tenant_id` filtering. Verify in a real browser against
the demo tenant's actual case/member data, not just that it renders.

**Changed**:
- `server/admin_api/routers/dashboard.py` (new), `schemas/dashboard.py`
  (new): `GET /dashboard/stats` and `GET /dashboard/export?resource=cases|
  members`, both `require_role(UserRole.OFFICE_MANAGER)` and both resolving
  the tenant the normal way via `get_current_tenant` — a clearly separate
  path from `routers/platform.py`'s cross-tenant super_admin stats, same
  distinction CLAUDE.md draws in Roles (office_manager: own tenant only;
  super_admin: firm-level/aggregate only, never case content). Stats:
  active/total/closed case counts, lawyer/client counts (reusing
  `plan_limits.count_active_lawyers`), plan + storage usage (reusing
  `plan_limits.get_plan_usage`, the same helper `check_plan_limit` enforces
  against and `SubscriptionPage` already reads, so this can never show a
  different number than what's actually gated), and a 6-month new-case
  trend grouped in Python rather than a DB date-trunc function (case volume
  per tenant is small enough that this was simpler than a dialect-specific
  query). Export: CSV via `csv`/`io.StringIO`, `Content-Disposition:
  attachment` — every query in both branches filters `Case.tenant_id`/
  `Membership.tenant_id` against `tenant.id` from `get_current_tenant`
  explicitly, the same way every other route in this codebase does, per
  CLAUDE.md's warning above.
- `server/tests/test_dashboard_admin.py` (new): tenant-isolation coverage
  for both endpoints (a second tenant's cases/lawyers never leak into the
  numbers or the CSV rows), storage-usage correctness, role-gating
  (lawyer gets 403 on both), and an unknown `resource` value getting
  rejected by Pydantic (422) before it ever reaches a query.
- `admin/package.json`: added `recharts`, per CLAUDE.md's tech stack
  ("stats dashboard (recharts)") — not previously installed, since no
  chart existed yet anywhere in `admin/`.
- `admin/src/pages/DashboardPage.jsx` + `.css` (new): four stat cards, a
  storage usage bar (same pattern as `SubscriptionPage`'s `UsageBar`, kept
  as its own copy rather than extracted — CLAUDE.md's per-app "not shared"
  rule plus only two occurrences so far), a `recharts` `BarChart` for the
  monthly trend, and two CSV export buttons reusing `DocumentsPanel`'s
  existing `triggerBrowserDownload` pattern (blob + a synthetic `<a
  download>` click). Loading/Error states plus an explicit Empty state
  (no cases/lawyers/clients at all) and a chart-specific empty note
  (no cases yet, so no trend to show).
- `admin/src/api/dashboard.js` (new): thin wrapper, same shape as every
  other `api/*.js` file.
- `admin/src/components/AppShell.jsx`: gave the `dashboard` nav item its
  `path` (it was the one remaining disabled "בקרוב" placeholder) and
  trimmed the now-stale comment about it not being built yet.
- `admin/src/App.jsx`: registered the `/dashboard` route.
- `admin/src/utils/format.js`: added `formatMonthLabel` (localized short
  month label for the chart's x-axis).
- Re-ran `server/scripts/export_docs.sh` — `docs/openapi_admin.json` picked
  up the 2 new `/dashboard/*` paths (31 total now), both Postman
  collections and the ERD regenerated from it.

**Verified in browser** (Playwright against the already-running admin dev
server at `demo.lvh.me:5174` and the already-running `admin_api` container,
which auto-reloaded on the new router): logged in as the seeded demo
office_manager (`office_manager@casehub.example.com`). The demo tenant
already had real data from earlier sessions (7 cases: 4 open/1 in_progress/
1 on_hold/1 closed, 1 lawyer, 2 clients, Free plan, 0 bytes stored) —
cross-checked directly against the database first. The rendered stat cards
showed exactly 6 active / 7 total cases, 1 lawyer, 2 clients; the monthly
chart showed a single bar in the current month at height 7, matching every
case's `created_at`. Clicked both export buttons: `demo-cases.csv` and
`demo-members.csv` downloaded correctly, row counts and values matching the
database (including a case title containing an embedded `"` that
`csv.writer` quoted correctly). Zero browser console errors throughout.

**Learned / decided**:
- The chart's single bar was briefly hard to eyeball as "present" in a
  fullpage screenshot — recharts renders `<path>` elements for bars (not
  `<rect>`), so a first pass querying for `rect` elements found only the
  cartesian-grid clip rect and wrongly looked empty. Cropping the
  screenshot to the bar's actual `getBoundingClientRect()` confirmed it was
  there and correctly colored the whole time — a reminder to check the
  DOM/computed style before concluding a rendered chart is broken, since a
  full-page screenshot can make a single-bar chart genuinely easy to miss
  at a glance.
- Recharts' `fill="var(--color-primary)"` on the SVG presentation attribute
  does get resolved by the browser (confirmed via `getComputedStyle` ->
  `oklch(0.3 0.13 258)`) — presentation attributes go through the same CSS
  cascade/`var()` resolution as a `style` attribute would, so the app's
  design-token CSS variables work directly in chart fills with no extra
  plumbing needed.

## 2026-09-09

**Asked**: Build the public firm homepage — the last remaining Phase 2 item
per CLAUDE.md: an unauthenticated tenant landing page (name/logo/color/about)
with a sign-in link, plus letting office_manager set the "about" blurb from
the existing Branding screen.

**Changed**:
- `server/shared/settings.py` (new): `get_setting`/`set_setting` helpers plus
  an `ABOUT_KEY = "about"` constant. Added here rather than duplicated per
  backend — both `admin_api` (writes it) and `client_api` (reads it) need the
  exact same `Settings.key` convention against the same table, which is
  exactly the kind of genuine cross-app invariant CLAUDE.md's Code quality
  section calls out (same reasoning as `shared/storage.py`/`plan_limits.py`).
- `server/admin_api/schemas/tenant.py` / `routers/tenant.py`: added
  `about: Optional[str]` to `TenantResponse`/`UpdateTenantRequest`. `about`
  goes through `Setting(tenant_id, key="about")` via the new helper;
  name/logo_url/primary_color stay direct `Tenants` columns, unchanged.
  `GET`/`PATCH /tenant` now build the response manually (`_to_response`)
  since `about` isn't a `Tenant` attribute FastAPI can serialize by just
  returning the ORM object.
- `server/client_api/schemas/public.py` + `routers/public.py` (new):
  `GET /public/profile`, depends only on `get_current_tenant` (no auth
  dependency chained on top) — same unauthenticated-but-tenant-scoped shape
  `POST /auth/login` already uses. Response schema (`PublicTenantProfile`) is
  a hard whitelist of exactly 4 fields (name/logo_url/primary_color/about) —
  no case/document/member data is reachable through this route, even
  indirectly, since it never touches those tables at all. Registered in
  `client_api/main.py`.
- `client/src/api/public.js` (new): `getPublicProfile()`, `redirectOn401:
  false` (a 401 here would be unexpected server behavior, not "please log
  in" — this route never requires auth).
- `client/src/pages/PublicHomePage.jsx` + `.css` (new): unauthenticated
  landing page — logo/placeholder, name and sign-in button tinted with the
  firm's `primary_color`, about text (or a fallback line if unset), Loading/
  Error/Empty states.
- `client/src/App.jsx`: added a `RootRoute` component at `/` that calls
  `apiFetch('/auth/me', { redirectOn401: false })` directly (not `api/auth`'s
  `me()`, which redirects to `/login` on 401 by design for protected pages —
  wrong here, since a 401 at `/` is exactly the "show the public page" case)
  and renders `<PublicHomePage />` if unauthenticated or redirects to
  `/cases` if a session already exists. Login's existing `navigate('/')`
  therefore still lands logged-in users on their cases, unchanged.
- `admin/src/api/tenant.js`, `admin/src/pages/BrandingPage.jsx`: added an
  `about` textarea to the existing Branding form (state, load, save,
  revert-on-save-response). `admin/src/components/Form.css`: extended the
  shared `.form-field` input styling to also cover `textarea` (previously
  only `input`/`select`) — a real third input type for this reusable
  building block, not a one-off.
- Re-ran `server/scripts/export_openapi.py` and
  `server/scripts/generate_postman.sh`; `docs/openapi_client.json` now has
  16 paths (was 15), `docs/openapi_admin.json` unchanged at 31 (the `/tenant`
  schema change doesn't add a path). Both Postman collections regenerated.

**Verified in a real browser** (Python Playwright, headless Chromium, driven
against the already-running dev servers — `client_api`:8000/`admin_api`:8001
Docker containers with `--reload`, and the already-running Vite dev servers
on 5173/5174 — no new servers started):
- Set the demo tenant's about text via `PATCH /tenant` (curl, first attempt
  via an inline shell string got mangled to literal `?` characters — a
  Git-Bash/Windows console encoding artifact, not an app bug; a file-based
  UTF-8 payload confirmed the real request/response round-trips Hebrew text
  correctly, byte-for-byte, through both `admin_api` and `client_api`).
- `http://demo.lvh.me:5173/` with **zero cookies** (fresh browser context)
  returned HTTP 200 and rendered "Demo Firm Updated", the saved Hebrew about
  text, and a "כניסה לפורטל" (sign in) button — confirming the route is
  genuinely reachable unauthenticated, not just "doesn't redirect in this
  one browser tab". Clicking it navigated to `/login` as expected.
- Confirmed `GET /public/profile` returns only the 4 whitelisted fields —
  checked the raw JSON response directly, no case/document/user fields
  present at all.
- Logged into `http://demo.lvh.me:5174/` as the seeded office_manager,
  opened Settings → Branding: the new "about" textarea was pre-filled with
  the exact saved text, editing it and clicking "שמירת שינויים" showed the
  existing save-success banner and persisted, confirmed by re-fetching
  `GET /tenant`. Reverted the demo tenant's about text back afterward.
- Zero browser console errors from either app's own code (the console did
  log expected 401s from the client app's own `/auth/me` probe while logged
  out, and one `ERR_NAME_NOT_RESOLVED` from the deliberately-fake
  `https://example.com/logo.png` seed logo URL — neither is a regression).

**Learned / decided**:
- FastAPI/Pydantic v2 response models here have no `from_attributes`
  config anywhere in the codebase, yet existing routes freely `return` ORM
  objects — FastAPI's own response serialization passes `from_attributes=True`
  itself when validating against `response_model`, regardless of the model's
  own config. That only works when the response model's fields are a subset
  of the ORM object's actual attributes, though — adding `about` to
  `TenantResponse` (not a real `Tenant` column) broke that assumption, hence
  `_to_response` building the Pydantic model explicitly instead of returning
  `tenant` directly.
- Kept the Settings-lookup helper in `shared/` rather than inlining the same
  query twice (once per backend) — this is a deliberate, narrow addition to
  shared's scope in the same spirit as `storage.py`/`plan_limits.py`, not a
  drift back toward "share everything," since it's the exact key/table pair
  both apps must agree on.
- The root route needed its own unauthenticated `/auth/me` check rather than
  reusing `AppShell`'s or `api/auth.js`'s `me()` — both of those treat a 401
  as "redirect to login," which is the right behavior for a protected page
  but the opposite of what "/" needs to do (show the public page instead).

## 2026-09-09 (later still, yet again) — Narrative generation + PDF export, built as one connected flow (branch `feature/narratives`)

**Asked**: Build CLAUDE.md's Phase 3 items 2+3 together — fixed-template
narrative generation from a case's WorkLogs, and PDF export that files the
result as a real internal `Document` on the case, per CLAUDE.md's explicit
"narratives are never directly client-visible; sharing one is just the
existing Documents reclassify-to-client-folder action" design.

**Changed**:
- `server/client_api/core/narratives.py` (new): `HOURLY_RATE = 450.00`
  (flat-rate stand-in — CLAUDE.md: "no real AI/LLM needed, this is
  intentionally simple"), `compute_case_totals()` (sums every `WorkLog.hours`
  on the case into `total_hours`, derives `total_fee` at the flat rate),
  `generate_narrative_text()` (fixed-template body, no LLM call), and
  `build_narrative_pdf()` (plain `reportlab` canvas drawing — case title,
  narrative id/date, totals, then the wrapped narrative body; paginates if
  the text overflows one page).
- `server/client_api/routers/narratives.py` (new), mounted at
  `/cases/{case_id}/narratives`, mirroring `work_logs.py`'s shape:
  - `POST ""` — generates and inserts a new `Narrative` row (never edits an
    existing one — same "rows accumulate, newest wins" pattern as
    `Subscriptions`). Lawyer-only via `require_role(LAWYER)`, same as
    `work_logs.py` — any lawyer assigned to the case, not
    office_manager-gated, per CLAUDE.md, even though it produces a fee
    figure. No case-status restriction: unlike WorkLogs/Documents, a closed
    case doesn't block generating or exporting a narrative — closing a case
    is what CLAUDE.md says protects billing integrity *after* a case has
    been narrated/invoiced, which implies the narrative/export step needs to
    keep working on (or after) close, not get blocked by it.
  - `GET ""` — full history, paginated, newest first (the first row returned
    is always the current/authoritative narrative).
  - `POST "/{narrative_id}/export-pdf"` — renders the PDF, runs it through
    the existing `check_plan_limit("storage_bytes", ...)` gate (a PDF is
    real bytes on disk, same quota as any other upload), saves it via the
    existing `shared.storage.save_file()`, and inserts a real `Document` row
    (`folder_type=internal`) plus an `AuditLog` row
    (`action="narrative_pdf_exported"`) — returns the same `DocumentResponse`
    shape `documents.py` already returns, so the frontend's existing
    Documents panel needs zero new response-parsing logic. No new
    visibility mechanism built for narratives at all, exactly as scoped —
    sharing one with the client is the pre-existing reclassify-to-`client`
    action, verified working end-to-end below.
  - `_get_case_narrative()` 404s if the narrative exists but belongs to a
    *different* case at the same tenant (not just a different tenant) —
    covered by `test_export_pdf_rejects_narrative_from_other_case`.
- `server/client_api/schemas/narratives.py` (new): `NarrativeResponse`
  (id, case_id, generated_text, total_hours, total_fee, created_at).
- `server/client_api/main.py`: registered the new router.
- `server/requirements.txt`: added `reportlab==4.2.5`.
- `server/tests/test_narratives_client.py` (new, 9 tests): generate from
  real WorkLogs (asserts the exact computed hours/fee), lawyer-only
  generate/list/export (client 403s on all three), unassigned-lawyer 403,
  generating twice keeps both rows with newest-first ordering, export-pdf
  creates the internal Document + AuditLog row, export-pdf rejects a
  narrative id that belongs to a different case, and the full
  reclassify-then-client-sees-it chain (asserts `total == 0` for the client
  before reclassifying, `total == 1` with the right document id after).
- `client/src/api/narratives.js` (new): `listNarratives`/`generateNarrative`/
  `exportNarrativePdf`, same shape/PAGE_SIZE convention as `work_logs.js`.
- `client/src/components/NarrativesPanel.jsx` + `.css` (new): lawyer-only
  panel (not rendered/mounted at all for a client, same treatment as
  `WorkHoursPanel` — CLAUDE.md: narratives are always firm-internal), mirrors
  its Loading/Error/Empty handling. Shows the current (newest) narrative's
  meta line, full text, and an export button; a collapsible history list
  below it for older rows, each with its own export button (any narrative
  version can be exported, not just the current one).
- `client/src/pages/CaseDetailPage.jsx`: renders `NarrativesPanel` (lawyer
  only, new `canSeeNarratives()` gate, same pattern as
  `canSeeWorkHours()`/`canSeeInternalFolder()`) in its own full-width row
  below the existing Documents/WorkHours columns. Passes
  `onDocumentAdded` → bumps a `documentsRefreshSignal` counter state, so a
  PDF export makes the internal document show up in `DocumentsPanel`
  immediately without a manual page reload.
- `client/src/components/DocumentsPanel.jsx`: accepts an optional
  `refreshSignal` prop, added to its existing `load` effect's dependency
  array — the only change needed to let a sibling panel (Narratives) trigger
  a re-fetch from outside.

**Verified in a real browser** (Playwright/Chromium, same throwaway-real-data
approach as the 2026-09-08 Documents/WorkLogs browser verification — real
HTTP calls against the running `demo.lvh.me` containers, not fixtures):
registered a fresh lawyer + client identity, added both as `demo`-tenant
members via `admin_api` (as the seeded office_manager), created and assigned
a case to both, then logged 5.5 hours (2 entries: 3.5h + 2h) as the lawyer.
Against the real Vite dev server:
- Narratives panel loads on the case-detail page for the lawyer; generating
  shows the correct computed total — **5.50 hours, ₪2,475.00** (5.5 × the
  450 flat rate) — matching the actual logged WorkLogs, not a hardcoded
  number.
- Exporting to PDF, then switching to the internal Documents tab, shows
  `narrative-1.pdf` there immediately (no manual reload) — confirms the
  `onDocumentAdded`/`refreshSignal` wiring actually works, not just that the
  backend created the row.
- Reclassifying that document to the client folder (existing action, no new
  code), then logging in as the assigned client: the client's Documents
  panel goes from 0 documents to 1 — `narrative-1.pdf` — confirming the
  narrative's real end-to-end reachability path (generate → export → file as
  internal Document → reclassify → client sees it) with zero new visibility
  code, exactly as CLAUDE.md specifies.
- Zero browser console/page errors across every step, both the lawyer and
  client sessions.
- Full backend suite (124 tests, all apps) still green after the change.

**Learned / decided**:
- Confirmed via direct DB inspection (`STORAGE_ROOT` doubling — see below)
  that no case-status restriction was needed on either narratives route
  before writing the tests, rather than defaulting to copying WorkLogs'
  "closed blocks new rows" rule out of habit — CLAUDE.md's own reasoning for
  that rule ("protect billing integrity once a case has been
  narrated/invoiced") only makes sense if narrating/exporting is expected to
  still work right up to (and arguably after) the close, so blocking it
  there would have been the wrong default.
- **Discovered, not caused by this session's changes, and not fixed here
  (out of scope for a narratives feature)**: `STORAGE_ROOT=./server/storage`
  in `.env` resolves inside the `client_api`/`admin_api` containers relative
  to their `WORKDIR /app`, which is itself the *host's* `./server` directory
  (bind-mounted per `docker-compose.yml`) — so every file ever uploaded
  through the real running containers has actually been landing on the host
  at `server/server/storage/...`, one level deeper than `.gitignore`'s
  `server/storage/` pattern covers, meaning every previously-uploaded demo
  file has been an untracked-but-uncommitted directory this whole time
  (`git status` just never happened to surface it until this session wrote
  a new file there). Left untouched/unstaged deliberately rather than
  silently fixing `STORAGE_ROOT` or the Dockerfile `WORKDIR` as a drive-by —
  flagged to the user instead, since fixing it is either a `.env` value
  change or a `.gitignore` pattern fix, either way a call for whoever owns
  that decision, not an unrelated narratives PR.

## 2026-09-09 (later still, once more) — Fixed the STORAGE_ROOT double-resolution bug (branch `fix/storage-root-path`)

**Asked**: Fix the `STORAGE_ROOT` bug flagged during the narratives session —
find the actual mechanism first, don't guess at a fix; on its own branch off
latest `master`, unrelated to narratives; decide explicitly whether to
migrate the files already sitting at the wrong path; add the corrected
nested path to `.gitignore` as a safety net; verify for real (rebuild
containers, fresh upload, download it back, confirm pre-existing files still
resolve); log it here; ask before commit/push/PR.

**Confirmed mechanism** (via `docker compose exec client_api pwd` +
resolving the env var live inside the running container, not by reading
code and guessing):
- `docker-compose.yml` bind-mounts this repo's `./server` directory onto
  `/app` inside both the `client_api` and `admin_api` containers
  (`volumes: - ./server:/app`), and each container's `WORKDIR` is `/app`.
- `.env`'s `STORAGE_ROOT=./server/storage` is read by
  `shared/storage.py`'s `Path(os.getenv("STORAGE_ROOT", ...)).resolve()` —
  which resolves relative to whatever process's cwd actually is. Inside the
  containers that's `/app`, so `./server/storage` resolves to
  `/app/server/storage`, which — because `/app` **is** the host's
  `./server` — lands on the host's disk at `./server/server/storage`, one
  level nested deeper than intended.
- Confirmed `shared/storage.py` is the *only* runtime consumer of
  `STORAGE_ROOT` (grepped for it repo-wide) — `server/tests/conftest.py`
  always monkeypatches it to a pytest `tmp_path` before any test runs, so
  the buggy default was never hit there; the containers are the only place
  it was ever actually exercised, which is exactly why it went unnoticed as
  "consistently wrong" rather than surfacing as flaky.

**Changed**:
- `.env` / `.env.example`: `STORAGE_ROOT=./server/storage` →
  `STORAGE_ROOT=./storage`, with a comment explaining it's relative to the
  containers' `WORKDIR`/bind-mount (`./server` on the host), not the repo
  root — so it now resolves to `/app/storage` inside the containers, i.e.
  the host's `./server/storage`, matching what `.gitignore` already
  expected.
- **Migrated existing files, did not leave them behind**: the buggy path
  held exactly one file on disk (`server/server/storage/3/11/<uuid>.pdf`),
  matching the *only* `Documents` row in the dev DB (`id=7`, the narrative
  PDF exported during the narratives session's browser verification —
  earlier Documents/WorkLogs browser-testing sessions' demo data, per the
  2026-09-08 log entries, evidently didn't persist across a DB reset since
  then). Moved it to `server/storage/3/11/<uuid>.pdf` with a plain `mv`,
  then removed the now-empty `server/server/` tree. **Chose migration over
  "leave pre-existing files where they are"** because: (1) it was one file,
  zero risk; (2) `Documents.file_url` stores the storage key as a path
  *relative to* `STORAGE_ROOT` (e.g. `"3/11/<uuid>.pdf"`), never a path that
  embeds `STORAGE_ROOT` itself, so the move needed no DB update — the
  existing row's `file_url` already resolves correctly once the file sits
  under the corrected root; and (3) leaving it split across two roots would
  have meant `shared/storage.py` (a single, simple path-join function by
  design) needing to know about a second legacy root forever, which is
  exactly the kind of special-case creep the module was built to avoid.
- `.gitignore`: added `server/server/` as an explicit safety-net pattern
  alongside the existing `server/storage/`/`server/uploads/` entries — nothing
  was ever tracked there (confirmed via `git status`/`git log` before this
  fix), but there's no reason to leave that nested depth uncovered if a
  stale `.env` (an old checkout, a forgotten local override) ever
  regenerates it.

**Verified for real** (not just re-reading the code — rebuilt containers and
exercised the real HTTP paths):
- `docker compose up -d --force-recreate client_api admin_api`, then
  `docker compose exec client_api python -c "...Path(os.getenv('STORAGE_ROOT')).resolve()..."`
  printed `/app/storage` (was `/app/server/storage` before the fix) —
  confirmed the env change actually took effect inside the container, not
  just in the file.
- Downloaded the pre-existing narrative PDF (`document id 7`, moved during
  migration) via the real `GET /cases/11/documents/7/download` route as the
  assigned lawyer — `200`, full byte count, confirming the migrated file
  resolves correctly through the actual download code path, not just "the
  file exists on disk somewhere."
- Uploaded a brand-new file via the real `POST /cases/11/documents` route —
  landed on the host filesystem at `server/storage/3/11/<new-uuid>.pdf`
  (confirmed with `find`), *not* a regenerated `server/server/`, then
  downloaded it back via `GET .../download` and diffed the bytes against
  the original upload — identical.
- Full backend suite re-run after the fix — **124 passed** (tests never
  actually exercised the buggy path, since `conftest.py` monkeypatches
  `STORAGE_ROOT` per-test regardless, but re-ran anyway as a sanity check
  that nothing else references the old value). One earlier run showed
  spurious failures (`sqlalchemy` errors across many unrelated tests) —
  traced to a second pytest invocation launched in parallel against the
  *same* `TEST_DATABASE_URL`, both racing on `conftest.py`'s per-test
  `Base.metadata.drop_all`/`create_all`; not a real regression, confirmed
  by re-running the suite alone.

**Learned / decided**:
- "Find the mechanism first" was worth doing literally, not just as due
  diligence — the fix is a one-line env value change (`./server/storage` →
  `./storage`), but getting that line wrong in either direction (e.g.
  changing the Dockerfile `WORKDIR` instead, or making the path absolute)
  would have either not fixed anything or broken the bind-mount's whole
  point (host and container agreeing on where uploaded files live for
  `docker compose down`/`up` persistence across container recreation).
  Resolving the env var live inside the actual running container (rather
  than reasoning about it from the Dockerfile + compose file alone) is what
  turned "should resolve to X" into "does resolve to X, confirmed."

## 2026-09-09

**Asked**: Build two Phase 3 reporting add-ons together: an audit-log
browsing screen (`admin_api`, office_manager-only, read-only) and a
billable-hours-over-time chart on the office_manager dashboard, distinct
from the existing monthly case-activity chart.

**Changed**:
- `server/admin_api/schemas/audit_log.py` + `routers/audit_log.py`: new
  `GET /audit-log` — tenant-scoped, paginated (reuses `PageParams`/`paginate`
  exactly like `members.py`/`cases.py`), optional `action` filter, newest
  first, `office_manager`-only via `require_role`. Purely a read path — no
  new writer added; it joins the existing `AuditLog` rows against
  `Membership`+`Identity` for a display name/email.
- `server/admin_api/schemas/dashboard.py` + `routers/dashboard.py`: added
  `monthly_billable_hours` to `DashboardStatsResponse`, computed by a new
  `_monthly_billable_hours()` that mirrors the existing
  `_monthly_case_activity()`'s trailing-6-month/Python-bucketing approach
  (same portability reasoning documented on that function) — sums
  `WorkLog.hours` by `(year, month)` instead of counting `Case.created_at`.
- `admin/src/api/audit_log.js`, `admin/src/pages/AuditLogPage.jsx`: new
  screen, built on the existing `DataTable` component and the
  `CasesListPage`-style tab-filter + prev/next pagination pattern (action
  tabs, not status tabs). Added `formatDateTime` to `utils/format.js`.
  Wired into `App.jsx`'s tenant-CMS route branch and `AppShell.jsx`'s
  `NAV_ITEMS` (new "יומן פעולות" sidebar entry).
- `admin/src/pages/DashboardPage.jsx`: added a second chart card ("שעות
  חיוב לפי חודש") using a Recharts `LineChart` (deliberately a different
  chart type than the existing case-activity `BarChart`, so the two are
  visually distinguishable at a glance), with its own empty-state check
  (`hasBillableHours`) independent of the page-level empty state.
- Tests: `server/tests/test_audit_log_admin.py` (new — tenant isolation,
  action filter, newest-first ordering, lawyer-403) and an added case in
  `test_dashboard_admin.py` for `monthly_billable_hours` tenant isolation.
  Full suite: **124 -> 129 passed**.
- Re-ran `bash server/scripts/export_docs.sh` — `docs/openapi_admin.json`
  gained the `/audit-log` path and `DashboardStatsResponse.monthly_billable_hours`;
  regenerated `docs/postman_collection_{admin,client}.json` and
  `docs/erd.mmd.md`/`erd.png` (ERD content unchanged — the audit_logs table
  and its relationships already existed from Phase 1's "create all tables
  now" rule; the client-side Postman diff and a couple of relationship-line
  reorderings in `erd.mmd.md` are just the generators' own non-deterministic
  UUID/ordering output, not real content changes).

**Verified for real** (against the already-running `docker compose` stack,
not just re-reading code):
- Logged in via `POST /auth/login` as the demo tenant's real
  `office_manager@casehub.example.com` and hit `GET /audit-log` directly —
  returned 7 real entries already sitting in the demo tenant's `AuditLogs`
  table from prior sessions' document/narrative/member testing (document
  upload, narrative PDF export, member password resets, member
  deactivation, work log edit/delete) — confirms the "no excel-import writer
  exists yet" finding from research (that action string never appears) and
  that the join to `Membership`/`Identity` resolves real names/emails.
  `GET /dashboard/stats` on the same session returned real
  `monthly_billable_hours` (4.5 hours in the current month, from real
  `WorkLogs`).
- Drove the actual `admin/` dev server with Playwright (already available
  via the backend venv) at `demo.lvh.me:5174`: logged in, screenshotted
  `/audit-log` (real rows, action-filter tabs, pagination footer, RTL
  layout, sidebar item highlighted) and `/dashboard` (both chart cards
  present and visually distinct — bar vs. line — with real trailing-month
  data). Zero browser console errors on either screen.
- Full backend test suite re-run clean before adding new tests (124 passed,
  confirming no regression from the schema/router changes), then again with
  the new tests included (129 passed).

**Learned / decided**:
- The schema doc's "Excel import (work logs)" (Phase 3 item 1) hasn't
  actually been built yet, even though `WorkLogSource.EXCEL_IMPORT` exists
  as an enum value — so the audit-log screen's action-label map only covers
  the 9 actions real code currently writes, not the full aspirational list
  in CLAUDE.md's `AuditLogs` section; it can gain an `excel_import`-related
  label later without any other change once that feature lands.
- Kept the two dashboard charts' empty-states independent of each other
  (`hasBillableHours` vs. the existing `stats.total_case_count === 0`
  check) rather than combining them into the page-level `isEmpty` — a firm
  can have cases but zero logged hours yet (or vice versa), and collapsing
  them would hide a legitimately-empty chart behind a "no activity at all"
  message that isn't true.

## 2026-09-09 (later still, one more time) — Excel import for work logs (branch `feature/worklog-excel-import`)

**Asked**: Phase 3 item 1 — Excel import for work logs, following CLAUDE.md's
"Excel import (work logs)" paragraph and the `WorkLogs` data-model section
exactly: a downloadable template restricted to the lawyer's own
assigned+open cases, an office_manager bulk variant with a lawyer-email
column, whole-file validation (any bad row rejects the entire file), and
`AuditLogs` recording who triggered an on-someone-else's-behalf import.

**Changed**:
- `server/shared/worklog_import.py` (new) — a **third** narrow extension to
  `server/shared`, alongside `storage.py`/`plan_limits.py` (added with the
  user's explicit sign-off first, since CLAUDE.md previously named exactly
  two): `build_template_workbook()` (openpyxl, a hidden `Cases` sheet +
  `DataValidation` dropdown on the visible `Case` column — not a hardcoded
  comma-list formula, which has a ~255-char cap) and
  `parse_and_validate_import()` (the row rules: lawyer resolved either as
  the fixed self-membership or by email+tenant+role=LAWYER+active=true,
  must be `CaseAssignment`-assigned to the row's case, case not `CLOSED`,
  hours `0 < h <= 24` matching `CreateWorkLogRequest`'s existing bound, a
  real `YYYY-MM-DD` date). Returns `(results, errors)` — any error empties
  `results` entirely, enforcing "reject the whole file, no partial imports"
  at the one place both callers share.
- `server/client_api/routers/work_log_import.py` + `schemas/work_log_import.py`
  (new): `GET /work-logs/import/template` (lawyer's own assigned, non-closed
  cases) and `POST /work-logs/import` (self-import, `source=EXCEL_IMPORT`,
  no `AuditLog` — CLAUDE.md's audit requirement is specifically for
  on-someone-else's-behalf imports). Deliberately **not** nested under
  `/cases/{case_id}` like the manual work-logs router — one uploaded file
  can carry rows for more than one of the lawyer's cases.
- `server/admin_api/routers/work_log_import.py` + `schemas/work_log_import.py`
  (new): same shape, office_manager-only, template adds every non-closed
  case at the tenant (can't scope the dropdown per-lawyer in a single static
  sheet) plus a Lawyer Email column; import resolves the lawyer per-row by
  email and writes **one** `AuditLog` row per batch (`action:
  "work_log_excel_imported"`, `target` = row count + filename) — same
  one-row-per-action granularity as `document_uploaded`, not one row per
  imported entry.
- `client_api/core/file_validation.py`: added `is_xlsx_file()` (same
  zip-signature + inner-file-check pattern already used for DOCX, checking
  for `xl/workbook.xml`) and `MAX_IMPORT_FILE_SIZE_BYTES` (5MB, separate
  from Documents' 50MB cap — an Excel import file is inherently small).
  `admin_api/core/file_validation.py` (new) — its own small duplicate of the
  same check, since this app now receives its own upload (the bulk import)
  for the first time; kept per-app rather than promoted to `shared/`, unlike
  the row-validation logic, since it doesn't need to be byte-identical
  across apps, just "is this really .xlsx" answered the same way twice.
- `client/src/pages/WorkLogImportPage.jsx` + `.css` (new), wired into
  `App.jsx` and `AppShell.jsx`'s previously-disabled "שעות עבודה" nav slot
  (now "ייבוא שעות מאקסל", real path, lawyer-only — computed from
  `getStoredRole()` per-render via `useMemo`, not a module-level constant,
  so a role change mid-session isn't stale). Its own top-level screen, not
  inside `WorkHoursPanel`/`CaseDetailPage`, since one file's rows can span
  multiple cases. Three real Loading/Error/Empty states: the page's own
  "your assigned open cases" list (via `listMyCases`, filtered non-closed —
  doubles as a lawyer-facing sanity check of what the dropdown will offer),
  the template-download button/error, and the upload button/error
  (including a per-row error list rendered from the 422 response body).
- `admin/src/pages/WorkLogImportPage.jsx` + `.css` (new), same structure,
  wired into `App.jsx` and a new `AppShell.jsx` sidebar item. `admin/src/api/client.js`
  gained `apiUpload()` (didn't exist there before — Documents uploads are
  `client_api`-only, so this is admin_api's first real file upload).
- `client/src/api/client.js` + `admin/src/api/client.js`: `ApiError` gained
  an optional `rowErrors` field, populated from the 422 response's
  `row_errors` array — both apps' `apiFetch`/`apiUpload` now pass
  `data?.row_errors` through unchanged.
- `admin/src/pages/AuditLogPage.jsx`: added the
  `work_log_excel_imported: 'ייבוא שעות מאקסל'` label — closes the gap this
  file itself flagged as pending two sessions ago (see the "Learned /
  decided" note right above this entry).
- `server/requirements.txt`: added `openpyxl==3.1.5` (neither pandas nor
  openpyxl was present before; openpyxl alone was enough for
  parsing+writing xlsx with data-validation dropdowns, no need for pandas'
  extra weight for a single-sheet feature like this).
- `CLAUDE.md`'s Code quality section: documented the third `shared/`
  extension (see above) — the user was asked first via a clarifying
  question, since it changes an explicit "two extensions" statement in the
  doc, and chose the shared-module option over per-app duplication, citing
  the same "must stay identical across apps" reasoning already established
  for `storage.py`/`plan_limits.py`.
- Tests: `server/tests/test_work_logs_import_client.py` (9 tests — template
  scoping, successful self-import with `source=excel_import`, whole-file
  rejection with correct row numbering, unassigned-case/closed-case/
  non-positive-hours rejections, non-xlsx rejection, client-role 403) and
  `test_work_logs_import_admin.py` (6 tests — template's email column +
  full-tenant case list, successful bulk import + its `AuditLog` row,
  unknown-email/cross-tenant-email/inactive-lawyer rejections, lawyer-role
  403 on the admin route). Full suite: **129 -> 143 passed**.
- Re-ran `bash server/scripts/export_docs.sh` — `docs/openapi_client.json`
  gained the client-side `/work-logs/import` + `/work-logs/import/template`
  paths (20 total), `docs/openapi_admin.json` gained the admin-side
  equivalents (34 total); regenerated both Postman collections and
  `docs/erd.mmd.md`/`erd.png` (ERD content unchanged — no new tables, Excel
  import only adds routes/logic on top of the existing `WorkLogs`/
  `AuditLogs` tables).

**Verified for real** (rebuilt and restarted the `client_api`/`admin_api`
Docker images first — `openpyxl` is a new dependency, so the previously
-running containers didn't have it yet; confirmed with a failing
`import openpyxl` inside the old container before rebuilding):
- Registered a fresh `verify.lawyer@example.com` identity through the real
  running `client_api`, added as `lawyer` at the `demo` tenant and assigned
  to two real open cases (one Hebrew-titled) via the real `admin_api`, all
  through actual HTTP calls against `demo.lvh.me` — not fixtures.
- Downloaded the self-import template as that lawyer: confirmed via
  `openpyxl.load_workbook` on the real response bytes that the hidden
  `Cases` sheet listed exactly those two assigned cases and no others (a
  third, unassigned case at the same tenant was absent).
- Uploaded a real 2-row `.xlsx` (built with real `openpyxl`, not a fixture
  helper) — got `{"imported_count": 2}`, then confirmed via `GET
  /cases/{id}/work-logs` that both rows landed with `source: "excel_import"`
  alongside the case's pre-existing `manual` entries.
- Uploaded a real 2-row file with one bad date — got HTTP 422 with
  `row_errors: [{"row": 3, "message": "..."}]` (row 3 = header + good row +
  bad row), then confirmed via the same list endpoint that the *good* row
  from that rejected file was never persisted either — true whole-file
  rejection, not best-effort.
- Uploaded a plain `.txt` file renamed with a fake content-type — got HTTP
  400 "Unsupported file type," confirming the magic-byte check (not the
  claimed `Content-Type` header) is what actually gates this.
- Downloaded the office_manager bulk template as the real seeded
  `office_manager@casehub.example.com` — confirmed the `Lawyer Email` column
  and all 7 non-closed cases at the tenant (both Hebrew- and English-titled)
  in the hidden `Cases` sheet.
- Uploaded a real bulk-import row for `verify.lawyer@example.com` as the
  office_manager — got `{"imported_count": 1}`; confirmed via `GET
  /audit-log` a real `work_log_excel_imported` entry attributed to `Noa
  Manager` (who triggered it), and via `GET /cases/{id}/work-logs` that the
  created `WorkLog.lawyer_id` resolved to the *lawyer*, not the manager —
  the who-triggered-it/whose-hours-they-are separation CLAUDE.md calls for.
  Also confirmed a real 422 for an unknown lawyer email on the same
  endpoint.
- Full backend test suite re-run clean before adding the new test files
  (129 passed), then again with them included (143 passed).
- Cleaned up every piece of throwaway verification data afterward (deleted
  the 3 real `WorkLog` rows created above, unassigned the test lawyer from
  both cases, deactivated their membership) so the `demo` tenant's data is
  back to its pre-verification state.
- `npm run build` succeeded in both `client/` and `admin/` with the new
  pages/components included (no new build errors; admin's pre-existing
  >500KB chunk-size warning is unrelated to this change).

**Learned / decided**:
- A hardcoded Excel `DataValidation` list formula (`formula1='"a,b,c"'`) has
  a real ~255-character cap — discovered while designing the template, not
  from a bug report. Used a hidden second sheet + range reference instead
  (`Cases!$A$1:$A$N`), which scales to however many cases a real firm has.
- `admin_api` receiving its own file upload for the first time (the bulk
  import) meant CLAUDE.md's blanket "admin_api never receives an upload"
  line was no longer accurate — it was only ever true for Documents.
  Narrowed the wording in CLAUDE.md's Code quality section rather than
  silently contradicting it in code while the doc still read as absolute.
- Self-import writes no `AuditLog` row at all — only the office_manager's
  on-someone-else's-behalf bulk import does. CLAUDE.md's `AuditLogs`
  section specifically calls out "an admin-driven Excel import performed on
  someone else's behalf," which reads as scoped to that case, not blanket
  "any Excel import" — a lawyer importing their own hours is functionally
  equivalent to a manual entry (which also writes no audit row on create,
  only on later edit/delete) rather than an oversight action worth logging.

## 2026-09-09 (later still, one more time again) — Demo client login credential drift, found and fixed

**Asked**: while verifying the search/filtering feature (committed
separately, right after this) in a real browser,
`client@casehub.example.com` / `Client123!` — the demo *client* credentials
`db/seed.sql`'s comments document as one of the two required demo users —
failed to log in against the real running `client_api`. The user asked to
reconcile this properly: either reset the live account's password back to
what `db/seed.sql` documents, or, if that original password truly wasn't
recoverable, update `db/seed.sql` to match reality — whichever was
actually true — and confirm by logging in.

**Investigated**: `git log -- db/seed.sql` showed the file's `Dor Client`
row has never been touched since it was added — so if the seed file's own
bcrypt hash was wrong, it's always been wrong. Checked directly with
`bcrypt.checkpw(b"Client123!", <the exact hash stored in db/seed.sql>)` —
**`True`**. So `db/seed.sql` was correct all along; the *live* dev
database's password had drifted away from it, almost certainly via the
office_manager password-reset feature being used on this account by an
earlier manual-testing session (the same mechanism this session itself
used minutes earlier on an unrelated, non-seeded lawyer identity) and never
reset back.

**Fixed**: no code or `db/seed.sql` change needed, since the seed file was
already correct — reset the live account's password back to the documented
value via the real running `admin_api`, logged in as the real seeded
`office_manager`, calling the existing `POST
/members/{membership_id}/reset-password` route (the same feature an
office_manager uses by hand) against `client@casehub.example.com`'s real
membership. Confirmed with a real login call against `client_api`:
`POST /auth/login` with `client@casehub.example.com` / `Client123!` now
returns 200. This is a data-only fix against the shared dev database, not a
file change — recorded here per CLAUDE.md's "log AI usage as you go," and
committed on its own per the user's request so it's not mixed with the
unrelated search/filtering diff.

**Learned / decided**: a password-reset action taken against the shared
demo tenant during manual verification (in this or an earlier session) is
easy to forget to revert, and silently breaks the *documented* demo login
for whoever hits it next — worth treating "did I change a demo account's
password for testing" as something to always revert, or reset back to the
seed-documented value, before ending a verification pass. This session's
own use of the same reset-password feature on a non-seeded lawyer identity
(`lior.lawyer@example.com`, used later in this same session for the
search/filtering feature's browser verification) was left as-is
deliberately, since that identity was never a documented demo credential.

## 2026-09-09 (later still, one more time again, again) — Search/filtering for cases and documents, the last Phase 3 item (branch `feature/search-filtering`)

**Asked**: the final Phase 3 add-on — server-side search by title (cases) /
filename (documents), status filter (cases), folder-type + archived filter
(documents), in both `client/` and `admin/`, respecting existing pagination
(50/page default, 200 cap) and tenant-scoping, with indexes added for any
newly-searched/filtered column not already indexed.

**Changed**:
- Checked the existing schema first per CLAUDE.md's instruction not to
  assume an index is missing: `cases.status` and `cases.tenant_id` were
  already indexed (from the initial migration); `cases.title`,
  `documents.original_filename`, `documents.folder_type`, and
  `documents.archived_at` were not. Added all four as new `Index(...)`
  entries on the `Case`/`Document` models plus a real incremental Alembic
  migration (`35968b0ff2b2_search_and_filter_indexes_on_cases_and_.py`,
  autogenerated then applied with `alembic upgrade head` against the real
  local DB) — following the project's post-Documents-migration rule of
  incremental migrations, not drop-and-regenerate. `db/schema.sql` hand-edited
  to match (it's a curated reference snapshot, not mysqldump output verbatim).
- `server/client_api/routers/cases.py` + `admin_api/routers/cases.py`:
  added `search` (title, `ILIKE '%...%'`) to both list-cases routes —
  `admin_api`'s already had a `status` filter from Phase 2, `client_api`'s
  (lawyer/client's own assigned cases) had neither and got both.
- `server/client_api/routers/documents.py` + `admin_api/routers/documents.py`:
  added `search` (filename, `ILIKE`) alongside the pre-existing
  `folder_type`/`archived` filters on both list-documents routes.
- Frontend (`client/`, `admin/` — kept separate per CLAUDE.md's "no shared
  design system" rule, each app got its own debounced search input wired
  the same way): `CasesListPage.jsx` in both apps gained a search box next
  to the status tabs (300ms debounce, resets to page 1). `client/`'s case
  list previously filtered by status **client-side** after a single
  bounded fetch (a documented pre-existing shortcut, since a lawyer/client's
  assigned-case count realistically stays under the 200-cap single page) —
  this got restructured to push both search *and* status server-side like
  `admin/` already did, since "stays server-side, don't fetch-then-filter"
  was explicit in the ask; a small separate unfiltered fetch remains, used
  only to drive the status-tab counts and to distinguish "no cases assigned
  at all" from "no results for this search/filter" in the empty state.
  `DocumentsPanel.jsx` in both apps gained the same debounced search input
  next to the existing folder/archive controls, with the empty-state message
  distinguishing a real search miss from a genuinely empty folder/archive.
- Frontend `api/cases.js` and `api/documents.js` in both `client/` and
  `admin/` updated to pass the new `search` param through to the backend.
- Backend tests added to the existing files (`test_cases_admin.py`,
  `test_cases_client.py`, `test_documents_admin.py`,
  `test_documents_client.py`) covering: title search (partial match),
  search+status combined, search respecting pagination, folder/archived
  filtering, and (client-side role) a client's search staying scoped to
  their own visible folder. Full suite: 152 passed (was 128 before this
  branch).
- Re-ran `server/scripts/export_openapi.py` and
  `server/scripts/generate_postman.sh` — `docs/openapi_client.json`,
  `docs/openapi_admin.json`, and both `docs/postman_collection_*.json`
  regenerated with the new `search` query params.

**Verified against real running containers/demo data, not just pytest**:
- Backend, via `curl` against the real `demo.lvh.me:8001`/`:8000` (not
  fixtures): title search, status filter, search+status combined, and
  pagination (`page_size=3` across two pages, `total` stable) all against
  the real 8-case demo tenant; document search + folder/archived filtering
  against the real 2-document `Narrative Verification Case` (id 11).
- Frontend, via a real headless-Chromium session (Playwright, installed for
  this session since `chromium-cli` wasn't available on this Windows
  machine) driving the actual Vite dev servers at `demo.lvh.me:5174`
  (admin) and `:5173` (client) — logged in as the real seeded
  `office_manager`, typed into the real search box, and confirmed the
  table actually re-filtered (screenshot before/after). **This caught a
  real bug**: `admin/src/api/cases.js`'s `listCases()` wrapper had been
  left un-updated (only the page/JSX got a search box; the API function
  never forwarded `search` to the querystring), so admin's case search
  silently did nothing — invisible to `npm run build` and to the backend
  test suite, only caught by actually typing into the real running UI and
  watching the network request. Fixed, then re-verified with the same
  script showing the request now carrying `?search=...` and the table
  correctly narrowing to one row.
- Also verified the client app's UI as a real lawyer. The seeded demo
  *client* account's login was broken at the time (see the separate
  credential-fix entry above, on its own commit) — used a pre-existing,
  non-seeded lawyer identity in the demo tenant's dev DB
  (`lior.lawyer@example.com`, "Lior Lawyer") instead, reset via the
  office_manager password-reset feature to a known test password for
  headless login. Confirmed case search, the status tabs, and document
  search on a case's client/internal folder tabs all working, including
  the "no results" vs "folder genuinely empty" distinction. Cleaned up the
  one piece of throwaway test data added for this (a temporary case
  assignment).

**Learned / decided**:
- A frontend bug in a query-param wrapper function (as opposed to the page
  component that visibly renders a search box) is invisible to build
  tooling and to backend tests — it only surfaces by actually driving the
  running UI and inspecting the real network request. Worth remembering as
  a category of bug this project's test suite structurally can't catch on
  its own.
- `client/`'s original single-bounded-fetch-then-filter-locally pattern for
  cases (documented, deliberate, and fine for status alone) stopped being
  fine once server-side search was required by this task's explicit
  instruction — a good example of a previously-correct simplification that
  a later requirement can invalidate; worth re-reading past "documented
  shortcut" comments when a new requirement touches the same code, rather
  than assuming they still hold.

## 2026-09-10

**Asked**: Bring `README.md` up to CLAUDE.md's Git/documentation requirements
— it had no screenshots at all, and the status banner still said "Phase 2 in
progress" despite Phase 3's final add-on (search/filtering) already merged.
Take real screenshots against the actual running app (not mockups) and embed
them in the relevant sections; verify install/run steps and demo credentials
are still accurate; fix anything stale. Docs-only, no feature code.

**Changed**:
- Found the Docker backend containers (`client_api`, `admin_api`, MySQL,
  Redis) and both Vite dev servers already running from an earlier session —
  used them directly rather than starting anything fresh.
- Installed Playwright + Chromium standalone into the scratchpad directory
  (not added to either app's `package.json` — this was a one-off capture
  tool, not a project dependency) and wrote a script driving the real app at
  `demo.lvh.me` to capture six screenshots: the public firm homepage
  (logged out), client login, a client's case detail (documents panel —
  uploaded one sample PDF as part of the same run, since the client's
  assigned cases had no client-visible documents yet), the office_manager
  dashboard with the billable-hours-by-month chart populated, the admin
  cases list with a status tab and a search term both active, and the
  audit-log browsing screen. Saved under `docs/screenshots/`.
- Embedded all six in `README.md`'s existing Screenshots section (grouped by
  what each demonstrates, not just dumped as a bare list), and updated the
  top status banner to reflect Phase 1 + 2 + 3 all being done.
- Verified the rest of `README.md` against the current app: demo credentials
  in the table match `db/seed.sql` exactly for both seeded users (client
  password was fixed to `Client123!` in the prior day's session — confirmed
  here; office_manager's `OfficeManager123!` was already correct and didn't
  need a change), and the install/run steps (`.env.example` copy targets,
  `docker-compose.yml` port mapping, `alembic upgrade head` + seed command)
  still match the current `docker-compose.yml`/`.env.example` files exactly
  — no drift found there, so no edits needed beyond the status banner and
  screenshots.

**Learned / decided**:
- Client role never renders a WorkHoursPanel or NarrativesPanel at all (not
  just hidden by CSS — not mounted, per `client/src/pages/CaseDetailPage.jsx`),
  so a "client case detail (documents + work logs)" screenshot request
  actually only has a documents panel to show for that role — work logs are
  lawyer-only by design. Captured what the client role genuinely sees rather
  than forcing a work-logs element into a screenshot that wouldn't match
  reality.
- Kept Playwright as a throwaway scratchpad tool rather than adding it to
  the repo (no `package.json`/lockfile change, no new committed tooling) —
  this was a one-time capture task, not a recurring test-authoring need; if
  visual regression testing becomes a real project requirement later, it
  should be added deliberately as its own decision, not smuggled in as a
  side effect of a docs task.

## 2026-09-13

**Asked**: Build the "lobby" (`www.<BASE_DOMAIN>`) signup/multi-firm-login
address just documented in CLAUDE.md's Multi-tenancy architecture section —
`admin/`'s lobby gets signup (moved to be reachable there) plus a new
office_manager multi-firm login; `client/`'s lobby gets the lawyer/client
equivalent. `platform.lvh.me` untouched.

**Changed**:
- Backend: added `POST /auth/lobby-login` to both `admin_api` and
  `client_api` (`routers/auth.py` + `schemas/auth.py` in each). Both reuse
  `shared.security.verify_password` for the password check (no
  reimplementation) and differ only in which roles they resolve
  (`admin_api`: `office_manager`; `client_api`: `lawyer`/`client`) and that
  `client_api`'s response includes each match's `role` (needed by the
  frontend nav, which differs lawyer vs. client — `admin_api` has no such
  branching so it doesn't need to carry role). Both exclude inactive
  memberships and suspended tenants, matching every other tenant-scoped
  query's existing `active` filtering.
- Frontend (`admin/`): added `isLobbyHost()`/`redirectToTenant()`/
  `lobbySignupUrl()` to `utils/host.js`; `App.jsx` now branches three ways
  on hostname (platform / lobby / tenant) instead of two — `/signup` moved
  out of the tenant branch entirely (founding a firm from an existing
  tenant subdomain never made sense; it was only ever reachable there
  because the lobby didn't exist yet) and into the new lobby branch
  alongside a new `LobbyLoginPage.jsx`. The tenant `LoginPage`'s "found a
  firm" link now points at the lobby's `/signup` via a plain `<a>` (cross-
  origin, so not a router `Link`).
- Frontend (`client/`): added the same `isLobbyHost()`/`redirectToTenant()`
  pair to a new `utils/host.js` (client/ has no platform host case, so no
  `lobbySignupUrl()` — there's no client-side firm founding). `App.jsx`
  branches lobby vs. tenant; new `LobbyLoginPage.jsx` mirrors admin's but
  redirects with `?role=<role>` in the URL and picker button, since a
  lobby-login redirect crosses origins (lobby → tenant subdomain) and
  `sessionStorage` (where role normally lives, see `api/session.js`) is
  per-origin — added a small bootstrap in `App.jsx` that reads `?role=` on
  mount, calls the existing `setStoredRole()`, and strips the param via
  `history.replaceState`.
- Both `LobbyLoginPage`s render three states (form / submitting / picker or
  inline error) — no separate fetch-on-mount, so no loading spinner is
  needed beyond the existing submit-button "…" state already used
  elsewhere; the zero-match case reuses the existing `FormError` component.
- Tests: `server/tests/test_auth_lobby.py`, 11 cases covering both apps —
  wrong password, unknown email, zero matches (wrong-app role, e.g. a
  lawyer at the admin lobby), single match (redirect), multiple matches
  (picker), inactive membership excluded, suspended tenant excluded, and
  (client_api only) that role is correctly reported per tenant including a
  mixed lawyer-at-one-firm/client-at-another identity.
- Re-ran `server/scripts/export_docs.sh` (OpenAPI + Postman + ERD) before
  committing — `docs/openapi_{admin,client}.json` and both Postman
  collections now include the two new `/auth/lobby-login` routes.

**Verified manually** (Playwright script against the already-running Docker
backend + Vite dev servers, screenshots in scratchpad, not committed):
founded a brand-new firm at `www.lvh.me:5174/signup` and landed logged into
its own subdomain's CMS with no second login; logged in at the admin lobby
with an identity holding two office_manager memberships and got the picker,
clicked one and landed there logged in; logged in at the admin lobby with an
identity holding zero office_manager memberships (a client account) and got
a clear inline error, not a crash; logged in at the client lobby with a
single-membership client identity and landed on that tenant's `/cases` with
the correct (client, not lawyer) nav state, confirming the `?role=` bootstrap
actually works end-to-end; confirmed the existing per-tenant admin login
(`demo.lvh.me:5174/login`) still works unchanged. Cleaned up the two test
tenants created during this (`secondfirm`, `browsertest1`) from the dev DB
afterward.

**Learned / decided**:
- The role-across-origins problem (client/'s nav needs to know lawyer vs.
  client, but a lobby→tenant redirect is a hard navigation to a different
  origin, so nothing client-side survives it) doesn't have a clean answer
  within "cookie-based session, no bearer token" — went with a one-time
  `?role=` query param read once on mount and immediately stripped, rather
  than reaching for something heavier (e.g. baking role into the JWT, which
  CLAUDE.md already explicitly rejected for the same-identity-different-
  role-per-firm reason). `admin_api` doesn't have this problem at all since
  `office_manager` is its only lobby-relevant role.
- `SignupPage.jsx`'s hard-redirect-to-new-subdomain and the 401→refresh-
  retry logic in both apps' `api/client.js` were already sitting uncommitted
  in the working tree from a prior session when this one started — kept
  them (they're consistent with, and partly prerequisite to, this feature)
  and built on top rather than reverting.

## 2026-09-13

**Asked**: CLAUDE.md's Roles/Build order/Data model sections were updated
first (by the user, before this session) to remove office_manager's
admin-driven "reset a member's password by hand" and replace it with a real
self-service change-password + forgot-password flow (`PasswordResetTokens`).
Session scope: (1) remove the old admin-driven reset entirely, confirm
office_manager's member screens only ever touch Membership fields, add
self-service change-password for every role; (2) build the real
forgot-password flow (token table/migration, `/auth/forgot-password`,
`/auth/reset-password`, dev-only outbox standing in for real email); (3) a
batch of small UI fixes found during an earlier walkthrough (tracked in this
session's own scratch memory, not this file): admin cases list rows not
clickable, admin header missing firm branding, logout button not
discoverable, header/table spacing too tight, Excel import template not
RTL/Hebrew. Branch: `feature/self-service-password-reset`.

**Changed** (7 commits, each scoped to one fix per the user's explicit ask):

1. **Removed the admin-driven password reset** — deleted
   `POST /members/{id}/reset-password` (route + schema) from `admin_api`,
   deleted `admin/src/components/ResetPasswordModal.jsx` and its wiring in
   `MembersPage.jsx`/`api/members.js`. Rewrote the corresponding test to
   assert the route is gone (404) and the member's own password is
   untouched. Confirmed (no code change needed) that `MembersPage.jsx`/
   `AddMemberModal.jsx` already only ever touch `Membership` fields
   (role/active), never `Identity` fields.
2. **Self-service change-password + real forgot-password flow.** New
   `server/shared/password_reset.py` (a 4th narrow `server/shared`
   extension, alongside `storage.py`/`plan_limits.py`/`worklog_import.py`):
   `change_password()`, `create_reset_token()`, `redeem_reset_token()`.
   New `PasswordResetTokens` table + migration
   (`b2c3d4e5f6a7_password_reset_tokens.py`) — tenant-less, hashed token,
   single-use, 30-minute expiry, exactly per CLAUDE.md's Data model spec.
   `shared/dev_outbox.py` stands in for real email: writes/reads a
   gitignored `server/dev_outbox.jsonl` (both containers share it — same
   `WORKDIR /app` bind-mount that caused the earlier `STORAGE_ROOT`
   double-resolution bug works in this module's favor here, since both
   apps need to see the same file). Both `admin_api` and `client_api` get
   their own thin routes on top of the shared logic:
   `POST /auth/change-password`, `POST /auth/forgot-password`,
   `POST /auth/reset-password`, `GET /auth/dev-outbox`. Frontend:
   `ForgotPasswordPage`/`ResetPasswordPage`/`DevOutboxPage` on both apps'
   lobbies, linked from each `LobbyLoginPage`; self-service
   change-password screens for every role — `admin/`'s `ProfilePage`
   (office_manager, new "פרופיל אישי" settings tab) and
   `PlatformProfilePage` (super_admin, new platform sidebar item),
   `client/`'s `ProfilePage` (lawyer/client, new nav item). 8 new backend
   tests (`test_auth_self_service.py`).
3. **Fixed admin cases list rows not being clickable** — `DataTable.css`
   already had `.data-table-row-clickable` styles defined and
   `CasesListPage.jsx` already passed `onRowClick`, but `DataTable.jsx`
   never accepted the prop or wired it to the `<tr>`. One-line-ish fix.
4. **Added tenant branding to the admin header** — `AppShell.jsx` now
   fetches the tenant via the existing `GET /tenant` route and shows its
   logo (falling back to initials if the logo URL fails to load) plus its
   name in the topbar, since an office_manager's Identity can hold a
   Membership at more than one firm and the chrome gave no indication of
   which one you were in.
5. **Made the logout button actually discoverable** — it was plain,
   borderless text in the muted/secondary gray token, low-contrast enough
   against the page background to be easy to miss entirely. Gave it real
   button styling (border, background, icon, red hover state).
6. **Fixed header/table spacing** — `.cases-header` (shared by
   `CasesListPage` and `MembersPage`) had no `margin-bottom`, so the
   "add case"/"add lawyer" button sat flush against the card beneath it.
7. **Made the Excel work-log import template RTL/Hebrew** —
   `sheet.sheet_view.rightToLeft = True`, Hebrew column headers (parsing
   stays keyed by column *position*, never header text, so this doesn't
   touch validation logic), bolded + frozen header row, and real
   `yyyy-mm-dd`/`0.##` number formats on the Date/Hours columns instead of
   plain unformatted cells.

**Verified live**, not just via tests — against the already-running Docker
stack + Vite dev servers, using a one-off Playwright script (not committed;
`playwright-core` installed to the scratchpad dir, not the project):
- Screenshotted the admin cases list, confirmed row click navigates to
  `/cases/:caseId`, screenshotted the header (tenant name + logo fallback
  chip visible, logout button now visible with real contrast), and the
  members list (spacing, and confirmed no reset-password button remains).
- Screenshotted the client app (cases list + new profile page) to confirm
  no regression from the admin-only changes.
- Downloaded the *real* Excel template from the running `admin_api`,
  inspected it programmatically (`rightToLeft=True`, `freeze_panes='A2'`,
  Hebrew headers in order, bold, correct number formats), filled in a real
  row for a real lawyer/case pair from the dev DB, and imported it through
  the actual running endpoint (201, `imported_count: 1`) — then deleted
  that test WorkLog + AuditLog row afterward to keep the dev DB clean.
- Triggered a real `/auth/forgot-password` request for the seeded demo
  client, found the link in the dev outbox, redeemed it via
  `/auth/reset-password`, confirmed login worked with the new password and
  that a session token minted before the reset was invalidated — then
  reset the password back to the documented demo credential (`Client123!`)
  afterward so the required demo login still works.
- Full backend suite: 171/171 passed (run serially — an earlier attempt
  where two full-suite runs were accidentally kicked off in parallel
  produced flaky, non-reproducible failures from both processes
  resetting/dropping the same test database at once; not a real
  regression, confirmed by immediately re-running serially).
- Both `admin/` and `client/` production builds (`npm run build`) succeed
  with no errors after every change.

**Learned / decided**:
- The user caught that an early summary of this session's work covered
  only the password-reset pieces and omitted the small-UI-fixes item
  entirely, and separately asked to confirm (not assume) whether the
  per-tenant `/login` page and logout/expired-session redirect target had
  changed — they hadn't, and were never asked to; that pre-existing
  behavior (per-tenant login stays as a direct-URL entry point, lobby is
  an *additional* one, per the already-merged lobby-login feature) was
  confirmed directly from the code (`grep` on the actual redirect calls)
  rather than assumed from memory, and reported as unchanged rather than
  silently left ambiguous.
- No project-level "run" skill existed for driving this app in a browser;
  used the generic Playwright/chromium-cli pattern from Claude Code's
  bundled `run` skill instead, adapted for `playwright-core` (no
  `chromium-cli` binary available on this Windows machine) since Chromium
  was already installed locally from a prior `npx playwright install`.
- Split the `AppShell.jsx`/`AppShell.css` diff into two separate commits
  (tenant branding vs. logout-button styling) by temporarily reverting one
  half, committing, then reapplying the other — `git add -p` couldn't
  cleanly split them since both edits landed in the same contiguous JSX
  hunk.

## 2026-09-13

**Asked**: Product rename CaseHub → Caser across the whole codebase (CLAUDE.md
was already renamed in a prior session); plus four other items queued from the
punch-list (password-change-logs-out bug, confirm-password fields, membership
invite/accept flow, public-page team section) — worked on the branch
`feature/identity-auth-rebrand`, one commit per numbered item.

**Changed (item 1, rename)**:
- `grep -ri casehub` across the repo to find every remaining instance, then
  renamed: README title + demo email domains, both frontend `<title>` tags and
  wordmarks (`admin/`+`client/` `AppShell.jsx`/`Layout.jsx`/`PlatformAppShell.jsx`/
  `PlatformLoginPage.jsx`), `db/schema.sql`/`db/seed.sql` header comments and demo
  email domains, both FastAPI app titles, the ERD title
  (`server/scripts/generate_erd.py`), the session cookie names
  (`casehub_access`/`casehub_refresh` → `caser_access`/`caser_refresh` in
  `server/shared/security.py`), the structlog logger name, the `Identities`
  model docstring, the frontend `localStorage` role key
  (`client/src/api/session.js`), and the hardcoded test literals in
  `test_platform_admin.py`/`test_auth_lobby.py` that depended on the old
  cookie name/test emails.
- Regenerated `docs/openapi_*.json`, `docs/postman_collection_*.json`, and
  `docs/erd.{png,mmd.md}` via `server/scripts/export_docs.sh` rather than
  hand-editing the generated JSON, so they pick up the renamed FastAPI titles
  from source.

**Learned / decided**:
- Left the actual local MySQL database name (`casehub`, in `.env`/`.env.example`)
  unchanged — renaming a live local database is an infra action (drop/recreate
  or `RENAME DATABASE`), not a text substitution, and out of scope for a
  cosmetic product rename. Flagged in README with a one-line note next to the
  seed command so it doesn't read as an oversight.
- Left historical entries in this file (`docs/ai_usage.md`) referencing
  "CaseHub"/`casehub.example.com` untouched — they're an accurate record of
  what happened in past sessions, not something to retroactively rewrite.
- Ran the full backend suite after the rename (cookie-name change is the one
  edit here with real behavioral surface, since it affects every authenticated
  request) — all 171 existing tests passed unchanged.

**Investigated and fixed (item 2, super_admin password-change bug)**:
- Reproduced live with a Playwright-driven headless Chromium session against
  the real running `docker-compose` stack (`platform.lvh.me:5174` /
  `:8001`), capturing the full request/response/cookie trace — static code
  reading alone hadn't found it in a prior session.
- First reproduction attempt (correct current password, single click)
  succeeded cleanly with no logout — ruled out a cookie-domain/scoping issue
  on `platform.lvh.me` specifically, and ruled out the race hypothesis (no
  other request fires around the change-password call on this page).
- Root cause found by then deliberately submitting a *wrong* current
  password and watching the trace: `POST /auth/change-password` correctly
  rejects it, but with **HTTP 401** (`server/admin_api/routers/auth.py` and
  `server/client_api/routers/auth.py`, both wrapping the shared
  `WrongPasswordError`). Both frontends' `apiFetch` treats *any* 401 as
  "session expired" — it calls `POST /auth/refresh` (which succeeds, since
  the real session is still valid), retries the original request once, gets
  401 again (still the wrong password), and — since it's already retried —
  falls through to `window.location.assign(loginRedirectUrl())`. The user
  is bounced straight to `/login` with no visible error message, which
  looks exactly like being logged out. A correctly-typed current password
  was never actually broken; the bug only shows up on a typo, which is
  presumably what happened during the original walkthrough.
- Fix: changed both routes' `WrongPasswordError` handler from
  `HTTPException(401, ...)` to `HTTPException(400, ...)` — a wrong-password
  value on an already-authenticated request is a form-validation error, not
  an auth/session failure, so it shouldn't be able to trigger the generic
  401-means-expired-session handling at all. Updated
  `test_auth_self_service.py`'s assertion to match (400, not 401).
  Re-verified live: the same wrong-password submission now shows "Current
  password is incorrect" inline and stays on `/profile`.
- Also reset the already-seeded `super_admin` row's password back to the
  documented demo credential (`SuperAdmin123!`) and `token_version` to 0,
  and its display name to "Caser Platform" — both were left in a
  post-testing state by this same debugging session (password changed
  mid-repro; name was seeded before the rename and the already-existing DB
  row doesn't pick up a `seed.sql` text change retroactively).
- Per the user's follow-up ask, audited every other route for the same
  "401 used for something that isn't an expired session" mistake before
  committing: login routes (`/auth/login`, `/auth/lobby-login`,
  `/auth/platform-login`) also return 401 for wrong credentials, but are
  safe because the frontend calls them with `redirectOn401: false` — the
  generic refresh-and-redirect logic never applies. Confirmed live (a wrong
  lobby-login password shows an inline error and stays on `/login`, no
  redirect loop). The forgot/reset-password route already correctly used
  400 for an invalid/expired/used token. Invite accept/decline routes don't
  exist yet (item 4, not built this session) — noted to get this right
  (400/404, not 401) when they're built.

**Changed (item 3, confirm-password field everywhere a new password is
typed)**:
- New shared component per app — `admin/src/components/PasswordConfirmFields.jsx`
  and `client/src/components/PasswordConfirmFields.jsx` (not shared across
  apps, per CLAUDE.md's frontend-code-quality rule) — rendering the new-
  password field plus a second "אימות סיסמה" (confirm password) field, an
  inline mismatch message, and an exported `passwordsValid(password,
  confirmPassword)` helper each page's submit button is gated on. Extracted
  as a component rather than repeated inline, since it's used 4 times in
  `admin/` and 3 times in `client/` (CLAUDE.md's "extract before a third
  copy" rule).
- Wired into every password-entry screen: `admin/`'s
  `ProfilePage`/`PlatformProfilePage` (change-password, office_manager and
  super_admin), `ResetPasswordPage` (forgot-password flow), `SignupPage`
  (founding a firm); `client/`'s `ProfilePage` (change-password),
  `ResetPasswordPage`, `RegisterPage` (accepting an invite/registering).
- Verified live: submit button stays disabled while the two fields
  mismatch (with the inline "הסיסמאות אינן תואמות" message showing), then
  enables once they match; a real change-password submission with matching
  fields still succeeds end-to-end. Screenshotted the signup and register
  forms directly to confirm the confirm-password field renders correctly
  with the right label in both.
- `npx oxlint` on every touched file: clean except one expected
  fast-refresh warning on each `PasswordConfirmFields.jsx` (exporting a
  helper function alongside the component) — not an error, and the
  standard tradeoff for the "extract before a third copy" call above.

**Built (item 4, membership invite/accept flow)**:
- New `MembershipInvites` table (`shared/models/membership_invite.py` +
  Alembic migration `c3d4e5f6a7b8`, applied) and `InviteStatus` enum
  (pending/accepted/declined); `db/schema.sql` snapshot updated too.
- New `shared/invites.py` (fifth narrow `/server/shared` extension,
  alongside storage/plan_limits/worklog_import/password_reset):
  `create_invite` (rejects a duplicate pending invite or an already-active
  membership at the tenant), `accept_invite`/`decline_invite`,
  `resolve_invites_on_register` (a successful registration for an email
  with pending invites *is* the acceptance — resolves every matching
  pending invite, not just one, since the same unregistered person could
  be invited by more than one firm), and `list_pending_invites_for_email`.
- `admin_api`: new `POST /invites` (office_manager, LAWYER/CLIENT only —
  rejects OFFICE_MANAGER with a clear error) replacing the old instant
  `POST /members`; `GET /invites?status=` for the Members screen's
  "pending" tab. An email with no Identity yet gets a dev-outbox link to
  `http://<tenant-subdomain>.<BASE_DOMAIN>:<CLIENT_APP_PORT>/register` —
  new `CLIENT_APP_PORT` env var (admin_api can't build a link into
  client/'s own origin from its own request's Origin header, unlike
  forgot-password's link). `GET /members` changed from an
  `include_inactive` toggle to an exclusive `active` filter, matching the
  new active/removed tabs (a pending invite isn't a Membership row at all,
  so it was never part of this endpoint to begin with).
- `client_api`: new `GET /invites` (the logged-in identity's own pending
  invites, across tenants), `POST /invites/{id}/accept`,
  `POST /invites/{id}/decline` — ownership checked by email match, not
  tenant-scoped (an identity can hold a membership at one firm and a
  pending invite at another). `POST /auth/register` now calls
  `resolve_invites_on_register` after creating the identity.
  `POST /auth/lobby-login`'s response gained `pending_invites` (same
  lookup lobby-login already does for active memberships, per CLAUDE.md:
  "the invite shows up as a pending action for them the next time they
  log in").
- `shared/plan_limits.py`: `check_plan_limit`'s `lawyer_count` branch now
  counts pending LAWYER invites alongside active memberships (new
  `count_pending_lawyer_invites`) — otherwise a firm at its limit could
  invite far past it and have every invite land at once on acceptance.
  Confirmed live: inviting into a tenant already over-limit (found by
  accident — the seeded `demo` tenant already has 5 lawyers against
  Free's limit of 3 from earlier test data) correctly shows "Lawyer limit
  reached for your plan (3)" instead of silently succeeding.
- `admin/`: `AddMemberModal` replaced by `InviteMemberModal` (role fixed
  by which of two new header buttons opened it — "הזמנת עורך/ת דין" /
  "הזמנת לקוח/ה" — not a picker inside one generic modal).
  `MembersPage` reworked with exclusive status tabs (פעילים/ממתינים/הוסרו)
  instead of the old "status column + show-removed toggle" (the status
  column was flagged as redundant on the punch-list once tabs existed);
  the pending tab hides the office_manager role tab (invites are never
  that role) and renders a different column set (email/role/invited-
  by/date, since a pending invite has no Identity to join against yet).
- `client/`: new `api/invites.js`; `LobbyLoginPage` now shows a pending-
  invites section (accept/decline buttons) above the tenant picker,
  never auto-skipped past even when exactly one tenant already exists —
  a pending invite must get a chance to be seen, not silently bypassed by
  the existing "one tenant = auto-redirect" shortcut. `RegisterPage`
  prefills (not locks) `email` from the invite link's `?email=` query
  param — resolution is still purely by email match server-side, so
  editing it before submitting doesn't break anything, it just means
  that particular invite won't auto-resolve.
- Added `server/tests/test_invites_admin.py` (9 tests) and
  `test_invites_client.py` (7 tests): duplicate rejection (both kinds),
  role restriction, plan-limit counting of pending invites, declined
  invites not permanently consuming a seat, RBAC (lawyer can't invite),
  tenant isolation on the list, accept/decline (including rejecting
  someone else's invite or re-acting on an already-resolved one),
  register-time auto-accept across multiple tenants, and lobby-login
  surfacing pending invites. Updated `test_members_admin.py` for the
  `active` filter (removed the two tests that exercised the now-deleted
  instant-add endpoint). Full suite: 185 passed.
- **Bug found and fixed via live testing, not just reasoning about the
  code**: switching the Members page's status tab crashed the whole page
  white (`DataTable`'s `formatDate(row.created_at)` throwing "Invalid time
  value") — a real race between clicking a tab (which changes `statusTab`,
  and therefore which column set renders, in the very next paint) and the
  new tab's fetch actually resolving; for one frame, the new tab's columns
  rendered against the *previous* tab's still-in-state rows (e.g. invite
  columns reading a member row's nonexistent `created_at`). Fixed by
  tracking which tab a given `result` actually belongs to (`resultTab`,
  set atomically with the data itself in the fetch's `.then()`) instead of
  deriving columns from `statusTab` directly, which changes a render
  ahead of the data. Caught by scripting the actual click sequence in a
  live browser (Playwright against the running dev stack) and reading the
  page's own console/pageerror output — reasoning about the code alone had
  missed it.
- Regenerated `docs/openapi_*.json`/Postman/ERD via `export_docs.sh`
  (client_api 25→28 paths, admin_api 38→39).
- Left a few throwaway test identities from live verification in the dev
  `casehub` database (e.g. `brandnewclient@example.com`,
  `existinginvitee@example.com`) — consistent with how this database has
  already accumulated plenty of prior sessions' test data
  (`corstest1@example.com`, `planlaw1@example.com`, etc.); not worth a
  special-case cleanup.

**Before item 5, re-checked the 401-vs-form-error bug class on this
session's item 4 code** (per the user's explicit ask): login routes still
safe (`redirectOn401: false`), forgot/reset-password still 400, and the new
invite accept/decline routes (`client_api/routers/invites.py`) already used
404 for an invalid/already-answered/not-owned invite — nothing to fix.

**Built (item 5, public firm homepage team section + real logo upload)**:
- New `Identities.years_of_experience` column (migration `d4e5f6a7b8c9`,
  applied) — self-reported, same as `bio`.
- New self-service `PATCH /auth/profile` (both apps) — bio/photo_url/
  years_of_experience, identity-level, never a lever another party (an
  office_manager) can pull. Extended `IdentityResponse`/`GET /auth/me` to
  return them. Wired into a new "פרופיל ציבורי" card on both apps'
  `ProfilePage.jsx` (photo URL, years-of-experience number input, bio
  textarea).
- New `PATCH /members/{id}/public-visibility` (admin_api, office_manager
  only) toggling `Membership.show_on_public_page` — rejects a CLIENT
  membership or an inactive one with 400. Decided the "gated on an accepted
  membership" requirement means gated on the Membership row itself being
  active, not a separate cross-check against `MembershipInvites.status`:
  there's no FK link from Membership back to the invite that created it,
  and every Membership row (new ones via `accept_invite`, or pre-existing
  ones seeded before invites existed) already represents a real agreed
  relationship by virtue of existing and being active — a second check
  would be redundant, not more correct. Wired into `MembersPage.jsx`'s
  active tab as a checkbox column, shown only for office_manager/lawyer
  rows.
- `client_api`'s `GET /public/profile` now also returns `team`
  (office_manager/lawyer memberships that are active + show_on_public_page,
  sorted office_managers-first then lawyers, each group by
  years_of_experience descending — nulls sort last via a Python-side sort
  key rather than a fragile cross-DB "nulls last" SQL clause) and
  `has_logo` (a presence flag, replacing the raw `logo_url` in the public
  response — never leak an internal storage key).
- Real file upload for the tenant logo, replacing the URL-only text field:
  `shared/storage.py`'s new `save_tenant_logo`; `admin_api/core/
  file_validation.py`'s new `detect_image_type` (png/jpeg magic bytes, same
  approach as Documents' own check, admin_api's own copy per CLAUDE.md's
  per-app upload-handling rule); `POST /tenant/logo` (office_manager,
  validates content) and `GET /tenant/logo` (authenticated, admin/'s own
  BrandingPage preview) in admin_api; `GET /public/logo` (unauthenticated)
  in client_api for the actual public homepage. `Tenant.logo_url` now
  holds an internal storage key, not a raw URL — `TenantResponse`/
  `PublicTenantProfile` expose only `has_logo`; the frontend builds the
  actual image URL itself via a newly-exported `apiBaseUrl()` (both apps'
  `api/client.js`) pointing at `/tenant/logo` or `/public/logo`.
  `UpdateTenantRequest` dropped `logo_url` entirely (a separate multipart
  request now, not part of the branding PATCH body).
- **Found via live testing, not just reasoning about the code**: the demo
  tenant's `logo_url` already held a raw external URL from before this
  redesign (someone had pasted one through the old text field in an
  earlier session) — under the new "logo_url is an internal storage key"
  meaning, `GET /public/logo` would try to resolve that URL as a local
  disk path and fail. Not a code bug (a fresh upload or a fresh tenant
  works correctly, verified below) — cleared that one stale dev-DB value
  by hand, same as the CaseHub→Caser rename's stale-seed-row cleanup
  earlier in this session, and confirmed a real upload → both the
  BrandingPage preview and the actual public homepage's `<img>` — renders
  correctly end-to-end afterward.
- `PublicHomePage.jsx`: team section below the firm card — a photo-card
  grid for members with `photo_url`, a separate plain name+role list
  underneath for members without one (never a placeholder image in the
  grid, per CLAUDE.md's public homepage note).
- Added `server/tests/test_public_team.py` (role/visibility/active
  filtering, sort order), `test_members_public_visibility.py` (role/active
  gating, RBAC), extended `test_auth_self_service.py` (profile update, both
  apps) and `test_tenant_admin.py` (logo upload/fetch/reject/404, updated
  the branding test for the new `has_logo` shape). Full suite: 197 passed.
- `npx oxlint` on every touched frontend file: clean except two more
  instances of the same pre-existing "setState in effect" warning already
  seen elsewhere in this codebase (data-fetch-on-mount pattern) — not new,
  not an error.
- Regenerated `docs/openapi_*.json`/Postman/ERD (client_api 28→30 paths,
  admin_api 39→42).

## 2026-09-14

**Asked**: Unattended overnight session on `feature/case-billing-superadmin` —
11 items (case tags, narratives language/period + Hebrew PDF, Excel import
polish, split assignment UI, cases-list badge swap, enterprise "unlimited"
display, Hebrew error catalog, audit log cleanup, sidebar font fix, super
admin feature set, admin sidebar/settings polish). Work through all of them
without stopping for approval; commit one item at a time; document any
judgment calls made instead of asking.

**Environment note**: no `chromium-cli` available in this Windows shell (the
`run` skill's default browser driver). Installed Playwright directly
(`npm install playwright` + `npx playwright install chromium`) in a scratch
dir under the session temp folder and drove it with a small Node script per
item instead — same verification bar (real browser, real login, screenshot,
`console --errors` equivalent), just a hand-rolled driver rather than the
packaged CLI. Flagging this so a `/run-skill-generator` pass could capture a
proper project run-skill later; didn't do that myself to stay focused on the
11 items.

**Item 1 — Case practice-area tags**:
- New `case_tags` table (`shared/models/case_tag.py`, migration
  `e5f6a7b8c9d0`), `PracticeArea` enum (traffic/criminal/family/civil/labor/
  real_estate/corporate/immigration — CLAUDE.md calls for "a curated list"
  without naming one; picked 8 common Israeli-practice areas as the
  reasonable default, easy to extend later since it's a real enum + table,
  not scattered string literals).
- `Case.practice_areas` is a Python `@property` over the `tags` relationship
  so both apps' existing `CaseResponse` (already relying on FastAPI's
  automatic ORM-attribute response serialization, no explicit
  `from_attributes` config anywhere else in the codebase either) picks it up
  for free.
- `admin_api`: `PUT /cases/{id}/tags` (office_manager-only, full-replace
  semantics — simpler than add/remove for a small fixed enum), `practice_area`
  query filter on both `GET /cases` list endpoints (admin + client — read
  access to tags/filter given to lawyers/clients too, only *setting* them is
  office_manager-gated, per CLAUDE.md).
- Frontend (admin only, since setting is office_manager-only there):
  `CasesListPage` gets a practice-area filter `<select>` + a new "תחומים" tag
  column; `CaseDetailPage` gets a row of toggle-chip buttons under the
  header, each click PUT-replacing the full tag set.
- Tests: `server/tests/test_case_tags.py` (set/replace, office_manager-only,
  tenant isolation via `get_tenant_scoped`, filter). Full suite: 32 passed
  locally on the touched files; ran the broader relevant subset (`test_cases_admin`,
  `test_cases_client`) alongside it.
- Verified live: logged into the real running dev stack (`demo.lvh.me:5174`,
  seeded office_manager) via the Playwright script above — filter select
  renders, 8 tag toggles render on a case, two toggles activate and survive
  a full page reload (confirms the PUT + refetch round-trip against the real
  DB, not just component state), tag chips show up back on the list page,
  zero console errors. Screenshots kept in the session scratch dir only (not
  committed — this repo doesn't have a convention for storing ad hoc
  verification screenshots, and README screenshots are handled separately
  per CLAUDE.md's delivery requirements).

**Item 2 — Narratives language/period + Hebrew RTL PDF**:
- `Narratives` gains `language` (he/en, default HE) and `period_start`/
  `period_end` columns (migration `f6a7b8c9d0e1` — added nullable, backfilled
  existing rows to `HE` + a period ending at their `created_at`, then made
  NOT NULL, since the dev DB already had narrative rows from before this
  feature). `compute_case_totals` now sums only WorkLogs inside the chosen
  period instead of the case's whole history, per CLAUDE.md.
- **Font sourcing judgment call**: CLAUDE.md asks for "a font that actually
  contains Hebrew glyphs embedded in the PDF" without naming one, and no
  font file existed anywhere in the repo. Fetched Google Fonts' **Alef**
  (SIL Open Font License — legally embeddable/redistributable, unlike
  copying a Windows system font such as Arial) as static Regular+Bold TTFs
  from the `google/fonts` GitHub repo, under `server/shared/fonts/`. Tried
  Noto Sans Hebrew first but it's shipped there only as a variable font,
  which reportlab's `TTFont` doesn't handle correctly — switched to Alef's
  static instances instead of fighting that.
- **RTL layout**: reportlab has no bidi/shaping support at all. Added
  `python-bidi` (small, actively maintained, MIT-licensed) and run every
  line through `get_display()` (the Unicode Bidi Algorithm) immediately
  before drawing — this reorders Hebrew runs right-to-left while leaving
  embedded numbers/dates in their correct reading order, then draws
  right-aligned from the page's right margin. Word-wrapping happens on the
  *logical* (pre-bidi) string; bidi reordering is applied per finished line,
  right before the draw call — doing it any earlier would wrap on the wrong
  (visual) character order.
- Currency is now plain text everywhere it's rendered — `generated_text`,
  the PDF, and the client UI's narrative panel — never the ₪ glyph, per
  CLAUDE.md. Wrote genuinely separate Hebrew and English narrative
  templates (not just a currency-token swap) since CLAUDE.md calls `he`
  "real work, not just template text swapped in" and that reads as
  applying to the wording, not only the font.
- Client UI: `NarrativesPanel` gets an inline generation form (period
  start/end date inputs + a he/en select) in place of the old single-click
  "generate" button.
- Tests: extended `test_narratives_client.py` for the now-required request
  body, added `test_narrative_period_and_language.py` (period filtering,
  currency-text assertions for both languages, a direct unit test on
  `build_narrative_pdf` confirming the Alef font is actually embedded in
  the PDF bytes, not silently falling back to Helvetica).
- **Verified live**: created a throwaway QA lawyer membership directly in
  the dev DB (no seeded lawyer account existed with a known password),
  assigned it to a real demo-tenant case, logged work hours, generated a
  Hebrew narrative through the real UI against the running dev stack,
  exported it to PDF, then pulled the actual PDF file out of the
  `client_api` container's storage volume and rasterized it (PyMuPDF) to
  visually inspect it — real Hebrew glyphs, correct RTL layout, numbers/
  dates staying in correct left-to-right order inside RTL sentences, no ₪
  glyph anywhere. **Found via that check, not by reasoning about the
  code**: the demo case's own title renders as literal `?????` in the PDF —
  traced to the actual bytes in MySQL (`HEX(title)` is literally `3F3F3F…`,
  the ASCII `?` character), meaning that specific case title was already
  corrupted at the byte level before this session touched anything (some
  earlier dev/test insert lost its Hebrew encoding on the way into MySQL).
  Confirmed this isn't a font/rendering bug: my own template text, written
  directly as proper UTF-8 in the Python source, renders with correct
  glyphs throughout the same PDF. Left the stale row as-is (out of this
  session's scope, same call as the earlier stale-`logo_url` cleanup
  logged above) rather than silently "fixing" unrelated dev data.
- **Environment note**: no `chromium-cli` in this shell (see the session
  header above) — used a hand-rolled Playwright script instead, same
  verification bar.

**Item 3 — Excel bulk import polish**:
- Office_manager's bulk-import template gets a real lawyer-email **dropdown**
  (a hidden `Lawyers` sheet + list `DataValidation`, same mechanism the
  existing Case dropdown already uses) sourced from the tenant's currently
  active lawyers — a typo'd or made-up email can no longer even be entered,
  matching the reasoning CLAUDE.md already gives for the Case dropdown.
- Date format switched from `YYYY-MM-DD` to **DD/MM/YYYY** in both the
  template header label, the cell number format, and the parser
  (`_parse_date`) — CLAUDE.md's Israeli-firm context makes DD/MM/YYYY the
  locale-correct choice; updated every existing test's fixture dates to
  match.
- **Exact-duplicate-row detection**, checked two ways: within the same
  file (a `seen_in_file` dict keyed on lawyer+case+date+hours+description,
  keeping the file the sole source of truth for what "the same row" means)
  and against already-persisted `WorkLogs` (a matching DB query on the same
  key). Either match rejects the row with a row-numbered error — consistent
  with CLAUDE.md's existing "reject the whole file, report which row and
  why" rule, just one more validation reason among the existing ones.
- **Frontend spacing bug**: `.form-error-banner` (the shared error-banner
  component both apps' `Form.jsx` render) only ever defined `margin-bottom`,
  never `margin-top` — fine wherever something already provided space above
  it, but on the Excel-import page the banner sits directly under the
  "בחירת קובץ לייבוא" action button with nothing between them. Fixed
  page-locally (`.work-log-import-card .form-error-banner { margin-top }`)
  rather than adding a global top margin to the shared component, since a
  global change risked shifting spacing on every other screen that already
  looks correct today. Same page/CSS file exists in both `admin/` and
  `client/` (each app's own copy, per CLAUDE.md's no-shared-frontend rule) —
  fixed both.
- Tests: new dropdown-content test (active lawyer emails present, inactive
  ones excluded) and duplicate-detection tests (within-file and
  against-existing-WorkLog) added to both the admin bulk-import and
  client self-import test files; every existing test's date literals
  updated to DD/MM/YYYY.
- **Verified live**: as the same QA lawyer, opened `/work-logs/import` in
  the real running client app — page loads, zero console errors. Full
  upload-a-real-.xlsx-and-see-it-import round trip wasn't separately
  screenshotted this item (the underlying parse/validate/persist path is
  the same code exercised end-to-end by the pytest suite above, including
  through the real multipart upload); the visual/DOM check covered what
  pytest can't — the page actually renders with no console errors.

**Item 6 — Enterprise "unlimited" lawyer count**:
- `PLAN_LAWYER_LIMITS[Plan.ENTERPRISE]` raised from 50 to 10,000 —
  `check_plan_limit` is completely untouched, per the task's explicit ask;
  Enterprise still goes through the exact same comparison as every other
  plan, just against a number high enough that no real firm hits it.
  10,000 rather than something like `math.inf`/`None` on purpose: keeping
  it a real, ordinary integer means every existing code path (the usage-bar
  percentage math, the JSON response shape) needs zero special-casing
  anywhere except the one display decision below.
- Frontend: `SubscriptionPage`'s lawyer `UsageBar` takes a new `unlimited`
  flag (true only when `usage.plan === 'enterprise'`) and renders "37 ·
  ללא הגבלה" with no progress track instead of "37 / 10000" — the storage
  usage bar is untouched (Enterprise's storage cap is a real, still-visible
  ceiling per CLAUDE.md, only the lawyer count is framed as unlimited).

**Item 4 — Split the mixed lawyer/client assignment picker**:
- `CaseDetailPage`'s "שיוכים לתיק" card previously had one "+ שיוך" button
  opening one `AssignMemberModal` with an internal lawyer/client tab
  switcher inside it. Replaced with two distinct actions: each
  `AssignmentGroup` column (עורכי דין / לקוחות) now has its own "+ שיוך
  עורך דין" / "+ שיוך לקוח" button, each opening the *same* modal component
  but with a fixed `role` prop and no internal tab — a lawyer and a client
  were never actually interchangeable choices in this flow, so a shared
  entry point with a mode switch was hiding two different actions behind
  one button.
- `AssignMemberModal` simplified accordingly: dropped `roleTab` state and
  the tab buttons, takes `role` directly, title changes per role
  ("שיוך עורך דין לתיק" / "שיוך לקוח לתיק"). Removed the now-dead
  `.assign-tabs`/`.assign-tab` CSS.
- Backend untouched — `POST /cases/{id}/assignments` already resolves the
  membership's actual role server-side and rejects a mismatch; this was a
  frontend-only ask.
- Verified live: both buttons render with distinct labels, each opens the
  correctly-titled modal scoped to that role, zero console errors.

**Item 5 — Cases list: ID badge instead of initials**:
- `CasesListPage`'s title column previously led with a decorative 2-letter
  initials badge (`avatarInitials`/`avatarTone`, purely cosmetic, not
  derived from any real per-row data) and showed the case's actual id only
  as small muted subtitle text ("מס׳ תיק #N"). Replaced the badge with a
  `.case-id-badge` showing "#N" prominently (bold, tinted, `direction: ltr`
  so the digits after `#` don't get bidi-reordered), and dropped the now-
  redundant subtitle line — the id has one clear, prominent home instead of
  two weaker ones.
- Removed the now-fully-unused `avatarInitials`/`avatarTone` helpers from
  `utils/format.js` (verified no other page still imports them) rather than
  leaving dead exports behind.
- Verified live: badge renders as a compact, obviously-a-number blue chip
  next to every case title, zero console errors, zero leftover initials
  elements in the DOM.
