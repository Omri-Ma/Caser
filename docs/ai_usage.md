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
