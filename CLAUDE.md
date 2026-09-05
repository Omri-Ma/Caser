# CaseHub — Law Firm Multi-Tenant SaaS

## Project
A multi-tenant SaaS platform for law firms. Each law firm is a tenant with its own
subdomain, branding, and subscription plan. Built for an academic exercise (level 4
difficulty), swapped from the original e-commerce theme — same technical requirements
apply in full.

## Roles
Each role logs into exactly one frontend app — `lawyer`/`client` always use
`client/`, `office_manager`/`super_admin` always use `admin/`. Nobody
cross-logs into the other app (see Multi-tenancy architecture for how
`office_manager` gets case visibility without needing `client/`).

- `super_admin` — cross-tenant visibility over firm-level/aggregate data only
  (firm list, subscription status, usage stats) — **never** case or document
  content within a tenant, even though the role is cross-tenant. Goes through
  its own explicitly separate code path (see Multi-tenancy architecture),
  including at login — it is not a `Memberships` row at all (see below).
- `office_manager` (tenant admin) — manages lawyers/clients, branding, subscription,
  scoped to their own tenant only. Automatically has access to every case at
  their own tenant — no explicit per-case assignment needed, unlike lawyers.
  This case oversight is a Cases section built into the `admin/` CMS itself;
  office managers don't additionally log into `client/` to work cases the way
  a lawyer would.
- `lawyer` — manages assigned cases only (explicitly assigned per case by the
  office manager, not automatic just from having a membership at the firm),
  uploads/downloads documents (including internal-only folders clients cannot
  see), logs work hours. Can be assigned to more than one case, and can hold
  a separate membership (and role) at more than one firm.
- `client` — views/uploads/downloads only documents on cases they're assigned
  to (client-visible folders only). A case can have more than one client. A
  client can likewise hold memberships at more than one firm.

## Tech stack (do not substitute without asking)
- Backend: **two separate FastAPI apps**, `client_api` and `admin_api` (per
  tutor guidance — they never call each other over HTTP, they only meet at
  the shared database), plus a small `/server/shared` package (not a running
  service) holding the one slice too risky to duplicate — table definitions
  and tenant/auth logic. See Multi-tenancy architecture for the full reasoning.
  Pydantic v2, SQLAlchemy (ORM), Alembic (migrations) — same stack, both apps.
- Database: MySQL, single shared database, indexes on all search/filter fields
  (email, subdomain, case status, etc.), not just primary/foreign keys
- Auth: JWT (access + refresh tokens), bcrypt or argon2 password hashing
- Cache: Redis — used for caching (tenant lookups, dashboard stats), not locking
- Frontend: React (or Next.js), two separate apps: `client/` (portal) and
  `admin/` (CMS) — deliberately different designs, no shared design system
  between them (see Code quality) — different audiences, different purposes.
- Infra: Docker Compose (`client_api` + `admin_api` + db + redis), Nginx
  (subdomain routing / reverse proxy — a real-deployment concern, not needed
  for local dev; see Multi-tenancy architecture for local vs. production addressing)
- Testing: pytest + httpx
- Logging: structured logging (e.g. `structlog`) instead of `print()` — always
  include `tenant_id` on request-scoped logs, it's essential for tracing isolation bugs.
  Built as request middleware in Phase 1 (not deferred to whenever a bug needs
  chasing): applied once, every route added afterward gets it automatically,
  and there's a log trail from the start of the Case/Document work — the
  exact area where an isolation bug would actually show up.
- Docs: FastAPI auto OpenAPI at `/docs`, exported Postman Collection in `docs/`
- Supporting libraries (anything not named above, e.g. small utility packages for
  either backend or frontend): free choice, per tutor guidance — just check the
  package has a reasonable download count and star count first, to avoid pulling
  in something unmaintained or with known security vulnerabilities.

## Multi-tenancy architecture (core requirement — this is the graded core, do not deviate)
- Strategy: **shared database, row-level isolation**. Every tenant-scoped table has a
  `tenant_id` column — even ones like `CaseAssignments` where it's technically
  derivable through a join, since this is what makes a single generic
  lookup helper work for every table without per-table join logic. Every
  query touching tenant data MUST filter by `tenant_id`.
  Build one reusable dependency/helper that applies this filter automatically —
  don't hand-write the filter in every route. Concretely: any route that
  accepts a foreign id from the request body (e.g. a `membership_id` to
  assign to a case) MUST look it up through the shared tenant-scoped lookup
  helper (`get_tenant_scoped`), never a bare `.filter(id == ...)` — a bare id
  lookup only proves the row exists *somewhere*, not that it belongs to the
  tenant making the request. This is the actual mechanism that prevents a
  request on subdomain X from ever touching data belonging to subdomain Y.
- Tenant identification: by **subdomain** (e.g. `office1.myapp.com`), read from the
  `Host` header via a FastAPI dependency/middleware that resolves the tenant and
  injects `tenant_id` into request state. Required as specified — do not replace
  with path-based routing. Locally, test subdomains via `lvh.me`
  (e.g. `office1.lvh.me:8000`), which resolves any subdomain to localhost with
  zero config.
- Two backends, two frontends, never merged, never talking to each other
  directly — only through the database:
  - **Backend**: `client_api` and `admin_api` are two independent FastAPI
    processes. Neither calls the other over HTTP. Both connect to the same
    MySQL database and both import the same `/server/shared` package (table
    definitions + tenant/auth logic) — sharing *code*, imported at the
    file-system level into each process, is not "communication" in the sense
    the no-HTTP rule cares about; it's how real systems avoid the one kind of
    duplication that's actually dangerous (see Code quality). Both must read
    the *same* `JWT_SECRET_KEY` and cookie config from a shared `.env` — this
    is what makes one login work across both apps with no second login: a
    cookie is scoped by domain, not by port, so the browser sends it to
    either backend automatically, and a JWT verifies itself (signature +
    `token_version` lookup) without needing to ask the other backend anything.
  - **Frontend**: `client/` and `admin/` are two independent apps. Locally,
    both are reachable at the same tenant subdomain, distinguished by port
    (e.g. `office1.lvh.me:5173` for the portal, `:5174` for the CMS) — zero
    new infrastructure, just how two separate dev servers already behave.
    Deliberately not a path (`office1.lvh.me/admin`): that needs a reverse
    proxy to work at all, makes the CMS trivially guessable by anyone
    appending `/admin` to any known URL (a near-universal habit), and blurs
    "two independent apps" into "one app with a section." In a real
    deployment, this becomes a subdomain **suffix**, not a nested
    sub-subdomain: `acme.casehub.com` (portal) / `acme-admin.casehub.com`
    (CMS) — a nested form (`admin.acme.casehub.com`) would need a separate
    DNS wildcard per tenant, since a wildcard only covers one subdomain level;
    a suffix needs only one wildcard (`*.casehub.com`) to cover every current
    and future tenant, admin included.
  - `super_admin`'s platform-only address (see below) is unaffected by any of
    this — it only ever involves `admin/` + `admin_api`, never `client/` or
    `client_api`, so there's no "which app" ambiguity there, only "which
    login mode within admin."
- Identity vs. membership: a login (`Identities`) is global — one person, one
  account — while tenant + role live on a separate `Memberships` row
  (`identity_id`, `tenant_id`, `role`). This lets one person hold a
  membership at more than one firm (e.g. a client who's worked with two
  separate law firms) without duplicate accounts, while every
  tenant-scoped table still references `memberships.id`, not `identities.id`
  directly, so isolation and role checks work exactly as before. Sessions are
  a cookie scoped to the base domain (e.g. `.lvh.me`), not a bearer token in
  localStorage, since localStorage is locked to one origin and can't be
  shared across tenant subdomains. The JWT stored in the cookie carries only
  `identity_id` + `exp` — `tenant_id`/`role` are resolved fresh on every
  request from `Memberships`, not baked into the token, since the same
  identity's role can differ per tenant. It also carries a `token_version`,
  checked against `Identities.token_version` on every request — JWTs are
  never stored server-side (that's the point of them; verifying one is just
  checking its signature, not a database lookup), so without this there is
  *nothing* to actually invalidate on logout, just a cookie deleted from one
  browser while the underlying token stays technically valid elsewhere for
  its full remaining life. Logout and password changes both bump
  `token_version`, which instantly invalidates every outstanding token for
  that identity regardless of where a copy exists.
- Subdomains have a hardcoded reserved-word blocklist checked at signup
  (`platform`, `www`, `api`, `admin`, `client`, `static`, `mail`, plus
  anything else system-meaningful) — otherwise a real firm could claim the
  exact address reserved for `super_admin`'s platform-only login, or another
  system-meaningful name, causing a real collision rather than a hypothetical one.
  On top of the fixed list, a **pattern** rule: no subdomain may end in
  `-admin`, not just the literal word "admin" — since that suffix is now
  meaningful (see above), a firm registering e.g. `acme-admin` as its own
  subdomain would collide with the real Acme firm's actual CMS address.
  Checked at signup the same way the fixed blocklist is, just as a suffix
  match instead of an exact match.
- Founding a firm with an email that already has an Identity is allowed, not
  rejected: `POST /auth/signup` checks whether the given email already has an
  Identity and, if so, verifies the submitted password against that
  Identity's existing `password_hash` (never creates a second password) and
  attaches a new `office_manager` Membership for the new Tenant to it — the
  same "attach an existing Identity" pattern `POST /members` already uses,
  just self-service. This is what makes "one login, many firms" hold up in
  practice: the same lawyer who's a member of one firm can found their own
  firm without a second account.
- `super_admin` is the only role allowed to query across tenants — this goes
  through a clearly separate, explicitly named code path (never the default
  tenant-filtered query functions), so it can't accidentally leak into normal
  user-facing queries.
- That separation starts at authentication, not just at the query layer.
  `super_admin` cannot be a `Memberships` row — a `Memberships` row means
  "this person belongs to this tenant," and `super_admin` doesn't belong to
  any tenant. Instead it's a flag on the login itself: `Identities.is_super_admin`.
  The `admin/` app has two separate login entry points into the same
  codebase: a fixed, non-tenant platform address (e.g. `platform.lvh.me`,
  not a `Tenant` row, never resolved by `get_current_tenant`) whose login
  route checks `Identities.is_super_admin` directly, and the normal per-firm
  subdomain (e.g. `office1.lvh.me`) that `office_manager` logs into exactly
  like every other role, via `Memberships`. `UserRole` (the `Memberships.role`
  enum) therefore only ever holds `office_manager` / `lawyer` / `client` —
  `super_admin` is never a value there. The first `super_admin` account is a
  fixed row in `db/seed.sql` with a pre-hashed password — no route ever
  creates or promotes one; there's no self-service platform-staff signup in
  this exercise.
- RBAC enforcement happens in BOTH backend (`Depends()` checks, mandatory) and
  frontend (route guards, UX only — never trust the frontend for real security).
- A pytest test proving tenant A cannot retrieve tenant B's data is required —
  write it early (Phase 1), not at the end.

## Data model
Create all tables now, including future add-on tables, even before their features
are built — avoids painful migrations later.

- `Tenants` (id, name, subdomain, logo_url, primary_color, active) — no `plan`
  column: a firm's current plan is whichever `Subscriptions` row for that
  tenant has `active = true`, not a separate cached copy. Two places tracking
  the same value with nothing keeping them in sync is itself a bug waiting to
  happen — a single source of truth removes the sync problem entirely rather
  than just documenting a discipline around it. `active = false` is a full,
  intentional lockout: `get_current_tenant` already filters on it, so a
  suspended firm becomes fully inaccessible to *everyone* at that firm,
  including its own `office_manager` — no self-service path back in, only
  `super_admin` reactivating it. Deliberate, not an oversight: matches how a
  suspended account behaves on most real platforms.
- `Identities` (id, name, email, password_hash, bio, photo_url, is_super_admin,
  token_version) — a person's global login, not tied to any one firm.
  `bio`/`photo_url` are self-reported profile info (mainly for lawyers),
  global to the person since it's "their own page" — whether it's actually
  shown at a given firm is the per-membership `show_on_public_page` toggle
  instead. `is_super_admin`: platform-staff flag, unrelated to `Memberships`
  — see Multi-tenancy architecture for why `super_admin` can't be a
  `Memberships.role` value. `token_version`: bumped on logout/password
  change to actually invalidate outstanding JWTs (see Multi-tenancy
  architecture — JWTs aren't stored server-side, so this is the only way to
  revoke one early).
- `Memberships` (id, identity_id, tenant_id, role, show_on_public_page, active) —
  one person's role (`office_manager` / `lawyer` / `client` only — never
  `super_admin`) at one firm; `identity_id` + `tenant_id` unique together.
  An office manager adds an existing identity to their firm by email
  (`POST /members`) — no new password is created, the person logs in with
  their existing account. `show_on_public_page`: per-firm toggle for whether
  this person's profile (see `Identities.bio`/`photo_url`) appears on this
  firm's public page — mainly meaningful for lawyer memberships. `active`:
  removing someone from a firm is a soft delete (flip `active` to false), not
  a real delete — `Documents`, `WorkLogs`, `AuditLogs`, and `CaseAssignments`
  all reference `memberships.id` with no cascade rule, so a real delete would
  simply fail once that person has any history. Queries for "who currently
  works here" (lawyer/client pickers, plan-limit counts) filter to
  `active = true`; historical records keep resolving correctly regardless.
  Re-adding a previously removed person to the *same* firm reactivates their
  existing (inactive) row instead of inserting a new one — the
  `identity_id`+`tenant_id` unique constraint means a fresh insert would
  fail while the old row still exists, active or not.
- `Cases` (id, tenant_id, title, status, created_at) — `status` is an enum
  (`open` / `in_progress` / `on_hold` / `closed`), not a free string. Who has
  access is NOT a column here — see `CaseAssignments`. Editing case metadata
  (title) is `office_manager`-only too, same reasoning as status — lawyers
  work within a case, office_manager controls its administrative facts.
  Changing status
  (including reopening a `closed` case) is `office_manager`-only — lawyers
  work within whatever status a case currently has (uploading documents,
  logging hours) but never control the status itself. A `closed` case blocks
  new `Documents`/`WorkLogs` from being added to it — status actually means
  something operationally, both so a closed case can't keep silently
  accumulating billable hours, and to protect billing integrity once a case
  has been narrated/invoiced. Reopening (office_manager, no restriction on
  when) is what resumes activity.
- `CaseAssignments` (id, tenant_id, case_id, membership_id) — many-to-many:
  which memberships (lawyers *and* clients alike — a case can have more than
  one of each) can access a case. Whether an assigned membership is a lawyer
  or client comes from `Memberships.role`, not a field on this table. The
  office manager sees every case at their own tenant automatically without
  needing a row here; `super_admin` never gets case-level access at all, only
  firm-level/aggregate data (see Roles). This table is a real (hard) delete
  when someone is unassigned — nothing else references `case_assignments.id`
  as a foreign key, unlike `Memberships`, so there's no history-preservation
  reason to soft-delete it. Unassigning someone is a full, immediate loss of
  access to that case, including documents they personally uploaded and
  hours they personally logged there — same rule as the co-client case
  above: `CaseAssignments` is the one access gate, no per-person carve-outs
  for past involvement.
- `Documents` (id, tenant_id, case_id, uploaded_by, file_url, folder_type,
  archived_at) — `folder_type`: `client` or `internal`. Visibility is fully
  derived from `CaseAssignments` + `folder_type` — internal → assigned
  lawyers/office manager, client → assigned clients — enforce in both the
  query layer and role checks. No separate `visible_to` column: an earlier
  draft had one, but it never had a defined purpose once `CaseAssignments`
  existed, so it was dropped rather than kept as unexplained scaffolding.
  Confirmed: when a case has more than one client, they share one
  client-folder view — a co-client sees every client-visible document on
  that case, not just their own uploads (they're co-represented parties on
  the same case, not adversaries), so there's no per-client scoping to build.
  `uploaded_by` references `memberships.id`.

  `folder_type` is reclassifiable after upload (moving a document between
  `internal`/`client`) — `lawyer`/`office_manager` only, never `client`
  (moving your own upload into `internal` would just make it invisible to
  yourself, so it's meaningless as a client action anyway).

  Deletion is a two-stage trash, not a flat soft-delete, since these are
  potential legal case records, not throwaway attachments:
  - **Archive** (`archived_at` set, file/row untouched, just hidden from
    normal views): `client` can archive only their own uploads; any `lawyer`
    assigned to the case can archive *any* document on it (their own or a
    colleague's); `office_manager` can archive anything at their firm.
  - **Restore** (`archived_at` cleared): any `lawyer` assigned to the case
    can restore. `client` cannot restore anything, even their own — same
    asymmetry as everywhere else, they'd ask a lawyer.
  - **Permanent delete** (the actual file + row erased — irreversible):
    only reachable *from inside the archive*, never as a direct action on an
    active document, and only `office_manager` can do it.
  - **Archive visibility**: `lawyer`/`office_manager` can browse a case's
    archive (you can't restore what you can't see). `client` cannot browse
    the archive at all — once archived, it's out of their hands.
  - **Same-filename upload**: uploading a file with the same name as an
    existing *active* document in that folder prompts "replace this?" —
    confirming archives the old one (not a permanent delete) and the new
    upload becomes active under that name. Gives "fix a wrong upload" as one
    smooth action with no separate versioning system — it's archive-old +
    upload-new, wearing a friendlier prompt.
  - **Storage quota**: archived documents still count against the plan's GB
    quota (the bytes are still on disk) — only a permanent delete actually
    frees space.
- `Subscriptions` (id, tenant_id, plan, start_date, end_date, active) — the
  single source of truth for a firm's plan (see `Tenants`, above); `plan` is
  `free` / `pro` / `enterprise`, and rows accumulate over time as a firm
  changes plans (only one `active = true` row per tenant at a time), which is
  the actual reason this is its own table instead of a column on `Tenants`.
  Keep enforcement simple: one reusable check (e.g.
  `check_plan_limit(tenant_id, resource_type)`) comparing a resource count
  against a hardcoded per-plan limit (e.g. number of lawyers). No billing or
  payment integration needed — this is a resource gate, not a commerce system.
  Downgrades don't retroactively touch existing resources: a firm that drops
  from Pro (say 10 lawyers) to Free (say a 3-lawyer limit) keeps all 10
  working normally — `check_plan_limit` only blocks *new* additions while
  the firm is over its new limit, it never deactivates anyone. Matches how
  real SaaS plans behave (GitHub/Slack don't forcibly remove seats on
  downgrade) and avoids needing a rule for which lawyers get cut.
- `Settings` (id, tenant_id, key, value)
- `WorkLogs` (id, tenant_id, lawyer_id, case_id, date, hours, description, source)
  — `source`: `manual` or `excel_import`. `lawyer_id` references `memberships.id`
  (whose billable hours these are — not necessarily who created the row, see
  below). Entries are editable/deletable after creation (typos happen, and a
  wrong hour count feeds directly into `Narratives.total_fee`): any `lawyer`
  assigned to the case can edit or delete *any* entry on it, not just their
  own — same broad, collaborative authority as `Documents` (more than one
  lawyer often needs to work with the same shared case record).
  `office_manager` can too, as with everything else. Every edit/delete is
  logged in `AuditLogs` (who changed which entry, when) — doesn't need full
  before/after value tracking, just that a change happened, since it affects
  billing. Locked entirely once the case is `closed` — same cutoff as new
  entries, one consistent "closed means frozen" rule rather than two
  separate timing rules to explain.
- `Narratives` (id, tenant_id, case_id, generated_text, total_hours, total_fee, created_at)
  — immutable once generated, never edited in place: correcting a mistake or
  reflecting new work means generating a new `Narrative` row for the same
  case, not editing the old one. The most recently created row for a case is
  the current/authoritative one; older ones stay in history (useful if you
  ever need to show what was originally sent before a correction). Same
  "rows accumulate over time, newest wins" pattern already used for
  `Subscriptions` — not a new mechanism, reused on purpose. This is also why
  `total_hours`/`total_fee` are stored as columns at all rather than computed
  live from `WorkLogs` on every read: they're a fixed snapshot of what a
  specific narrative said, by design. Generating one is any-lawyer-assigned
  authority, same as everything else on a case — not office_manager-gated,
  even though it produces a fee figure.

  Narratives themselves are always firm-internal (never directly client-
  visible) — the `Narrative` row is raw material for the PDF export (Phase 3
  item 3), and *that PDF becomes a real `Document` row* on the case, filed
  in the `internal` folder by default. Sharing it with the client is then
  just the existing Documents reclassify-to-`client`-folder action, already
  fully specified above — no separate visibility mechanism needed for
  Narratives at all. This does mean client-visible narratives depend on the
  PDF-export feature existing, not generation alone, which is fine — it's
  the natural order Phase 3 already lists them in (generate, then export).
- `AuditLogs` (id, tenant_id, user_id, action, target, timestamp) — add-on
  feature. `user_id` references `memberships.id`. Logs deliberate,
  file-changing actions only — document uploaded, archived, restored,
  permanently deleted, an admin-driven Excel import performed on someone
  else's behalf (see Excel import, above) — not downloads or a document
  merely appearing in a list. A document sitting in a folder is assumed seen
  by everyone with access to that folder; the log is a record of who changed
  what, not who looked. The permanent-delete entry matters most here: it's
  the only step in the Documents trash lifecycle that's actually
  irreversible, so it's the one place a durable "who did this and when"
  record is non-negotiable, not just nice to have.

## Folder structure (do not restructure later — this is part of the grade)
```
/client        — client/lawyer-facing React app
/admin         — office manager / super admin CMS
/server        — two independent FastAPI apps + one shared package:
                   /server/shared     — table definitions, tenant/auth logic
                                         (imported by both apps, never a
                                         running service itself)
                   /server/client_api — lawyer/client backend (routers,
                                         schemas, services, deps, core)
                   /server/admin_api  — office_manager/super_admin backend
                                         (routers, schemas, services, deps, core)
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
  A fixed, hand-typed list of exact origins doesn't work here: every tenant
  gets a subdomain created dynamically at signup, and the frontend has to be
  reachable at that same subdomain (so tenant resolution works for a real
  browser, not just curl). Use FastAPI's `allow_origin_regex` — a pattern
  like `https?://[a-z0-9-]+\.lvh\.me(:\d+)?` (swap `lvh\.me` for the real
  domain in production) — instead of a fixed `allow_origins` list, so every
  tenant subdomain is trusted automatically the moment it's created. This
  doesn't weaken tenant isolation: CORS only controls whether the browser
  lets a page *read* a response, not what data the backend returns — that's
  still entirely gated by `get_current_tenant` + `tenant_id` filtering.
  Configured independently in both `client_api` and `admin_api` (each is its
  own FastAPI app) — the same pattern works for both as-is, since it doesn't
  care about port locally or about the `-admin` suffix in production; no need
  to write two different regexes unless you want the extra tidiness of each
  backend only trusting its own frontend's naming pattern specifically.
- Add a basic `/health` endpoint on **each** backend (`client_api` and
  `admin_api` both) so Docker Compose (and the grader) can confirm both apps
  actually started, not just that their containers are running.
- All list endpoints (cases, documents, users, work logs) use pagination — never
  return an entire table in one response. 50 items per page by default — same
  idea as Gmail: nothing is ever unreachable, you just page through (page 2,
  page 3, ...) to reach any item, however far down the list it is. The
  frontend is free to present this as numbered pages or as infinite-scroll
  (auto-fetching the next page on scroll, Gmail-style) — same backend
  mechanism either way, purely a UI choice. Also cap how large a single
  requested page can be (e.g. 200) so a request can't ask for everything in
  one shot and defeat the point of paginating at all.
- All input validated via Pydantic schemas, never manual checks. All error
  responses share one consistent JSON shape across every endpoint
  (e.g. `{"error": "message", "field": "..."}`).
- Every frontend screen that fetches server data explicitly handles three states:
  Loading, Error, and Empty — not just the happy path.
- Concurrency on any insert that relies on a unique constraint (signup
  email/subdomain, adding a member, assigning a case, etc.): check first for
  a fast, friendly error in the common case, AND wrap the actual insert in
  try/except catching the database's unique-constraint violation, converting
  it to that same clean error. The pre-check alone is a race — two requests
  can both pass it before either has written — so the database's rejection is
  the actual guard, not the check. No in-memory locks/queues for this: they
  stop working the moment more than one server process is running.
- A separate, different concurrency question: two lawyers editing the *same*
  existing record (a WorkLog entry, a Document's metadata) at nearly the same
  time — relevant now that any lawyer assigned to a case can edit anything
  shared on it, not just their own. Deliberately kept simple: last write
  wins, no version/conflict checking. An accepted, explicitly-chosen
  simplification (documented here so it reads as a decision, not a gap) —
  the scenario is rare enough in this app's actual usage pattern that the
  extra machinery (a version column, conflict-handling UI) isn't worth it
  for this project.
- Frontend UI is RTL (Hebrew): `dir="rtl"` at the root, right-aligned text,
  navigation on the right, mirrored directional icons.
- Excel import (work logs): reject the whole file if any row fails validation,
  report which row and why, let the user fix and re-upload — no partial imports.
  A downloadable template drives this rather than a blank spreadsheet: a
  lawyer downloads their own template with a case column already restricted
  to (e.g. a dropdown of) the cases they're currently assigned to, so a typo'd
  or unauthorized case ID can't even be entered in the first place. Both
  self-service and admin-driven import are supported: a lawyer's template
  always covers their own hours; `office_manager` can additionally download
  a template with a lawyer-email column and bulk-import hours across
  multiple lawyers at their firm at once (e.g. historical data entry). Row
  validation either way: the named lawyer (self, or whoever the row's email
  resolves to — must be an existing `lawyer` Membership at this tenant) must
  be currently assigned to the referenced case, and the case must not be
  `closed`; hours must be a positive, sane number; date must be a real date.
  When `office_manager` imports on someone else's behalf, that's recorded in
  `AuditLogs` (who actually triggered the import) — `WorkLogs.lawyer_id`
  still records whose billable hours they are, kept separate from who
  performed the import action.
- File storage: local disk for now, behind a small storage abstraction
  (e.g. `save_file()` / `get_file_url()`) so swapping to cloud storage later
  only touches one module. Two separate limits, not one: (1) a per-file sanity
  check applied equally on every plan — an allowlist of real document types
  (PDF/DOCX/common image formats for scans), checked against the file's
  actual content/magic bytes rather than trusting the filename extension
  (trivially fakeable), plus a flat max size per file (e.g. ~50MB); and
  (2) a total-storage quota tied to plan (Free/Pro/Enterprise get different
  GB caps), enforced through the same `check_plan_limit` mechanism as the
  lawyer-count limit, blocking new uploads once a firm is over its plan's
  total — existing files are never deleted on downgrade, matching the
  lawyer-count grandfathering policy above. Enterprise's cap is a hard
  ceiling for self-service, same reasoning as "no billing integration": a
  firm needing more than that is a manual/negotiated case outside this
  product's scope, not a self-serve "buy more storage" flow. `super_admin`
  overriding one tenant's limit by hand is a reasonable escape hatch to
  mention if it comes up, but isn't built as a feature.
- Never hardcode secrets, passwords, or API keys — always `.env`, never
  committed. Every new `.env` variable is mirrored in `.env.example`
  (placeholder value, no real secrets).
- All code — variables, functions, comments — in English, even though the
  product domain and UI copy are Hebrew/RTL.

## Code quality: scalable and reusable by default
- Backend: within each of `client_api`/`admin_api`, shared logic (pagination,
  error responses, file upload handling) lives in that app's own shared
  utilities/dependencies — never copy-pasted per route file. *Across* the two
  apps, only `/server/shared`'s narrow scope (table definitions, tenant/auth
  logic) is actually shared — everything else stays genuinely separate per
  app, on purpose (see Multi-tenancy architecture for why only that one slice
  is worth the shared-code discipline).
- Frontend: within *each* of `client/` and `admin/` — separately, not shared
  between them — one reusable data-table component, one reusable form
  component, one reusable modal/dialog pattern, one reusable
  "list → detail → edit" structure, and colors/spacing/typography as CSS
  variables (which also doubles as that app's per-tenant branding mechanism).
  Not shared *across* the two apps: they're deliberately differently designed
  (see Tech stack), and actually sharing frontend code between two separate
  npm projects needs real tooling (workspaces, or a published package) for a
  benefit that's cosmetic at best here — not worth it for this project, so
  each app defines its own tokens/components independently.
- Favor composition over duplication: if a UI or logic pattern appears twice,
  extract it into a shared component/function before a third copy gets written.
- Keep naming, response shapes, and file/folder conventions consistent across
  the whole codebase.

## Build order — CORE FIRST, add-ons strictly after
Do not start any add-on feature until the core below is fully working and tested.

**Phase 1 — Skeleton (in order, before any feature work)**
1. Repo + folder structure + `.gitignore`
2. `docker-compose.yml` (`client_api` + `admin_api` + MySQL + Redis) — must run
   cleanly with `docker-compose up`
3. Full schema + Alembic migration (all tables above, including add-on tables)
4. Auth: signup/login, JWT issuing, password hashing — built once in
   `/server/shared` (see Multi-tenancy architecture), used by both backends
5. Subdomain-resolution middleware + tenant injection — same: lives in
   `/server/shared`, not duplicated per backend
6. Role-based route protection (backend + frontend) — each backend still
   defines its own routes and its own role checks per route; only the
   underlying "who is this, what tenant, what role" resolution is shared
7. Tenant-isolation pytest test — written against real endpoints (not just
   models), so it necessarily lands with the first Case route in Phase 2
   rather than before any route exists. Still "early" per the rule below —
   ship it with that first slice, don't let it slide further than that.

**Phase 2 — Core features** (one vertical slice at a time: DB model → API route →
frontend form → verified working, before starting the next)
- Whichever of the slices below is built first and touches `Cases` also ships
  the Phase 1 tenant-isolation pytest test (a request on tenant A's subdomain
  cannot retrieve tenant B's case) — do not move on to the next slice without it.
- Office manager: manage lawyers/clients, branding settings, subscription/plan
  view. Includes resetting a member's password by hand (sets a new one they
  must use next login) — the interim stand-in for real password recovery
  until email infrastructure exists (see Future additions), and reuses the
  same "office manager manages their people" authority already established
  for adding members.
- Public firm homepage: each tenant subdomain (e.g. `office1.lvh.me`) has a public,
  unauthenticated landing page showing only non-sensitive firm profile info (name,
  logo, an "about" blurb stored via the existing `Settings` table) with a sign-in
  link into the real portal — mirrors the original store assignment's public
  storefront vs. gated purchase/admin actions split. Reuses the existing subdomain
  tenant-resolution dependency, just without the auth requirement other routes have.
  Never exposes actual tenant data (cases/documents/users) — only firm profile info.
- Lawyer: case list, document upload/download (client + internal folders), manual work log entry
- Client: view/upload/download own documents only
- Super admin: cross-tenant firm list and stats
- Admin CMS: full CRUD per entity, stats dashboard (recharts), data export.
  Export queries are exactly the kind of bulk, hand-written query most likely
  to accidentally skip `tenant_id` filtering — route them through the same
  tenant-scoped query path as everything else, not a separate one-off query
  written just for the export feature.

**Phase 3 — Add-ons** (only after Phase 1 + 2 are fully working and tested)
1. Excel import for work logs (pandas or openpyxl — confirm which is allowed)
2. Narrative generation engine (start with a fixed-template version)
3. PDF export of the narrative (reportlab or weasyprint)
4. Audit log for document access
5. Billable-hours dashboard chart
6. Search/filtering on cases and documents

## Future additions (only if time remains after Phase 1 + 2 + 3 are done)
Real, worthwhile ideas that came up but aren't worth the scope/risk of building
before the core and add-ons above are fully working. Park them here instead of
either building them early or forgetting them — also a ready answer for the
defense's "what would you do with one more week" question.
- Real email-based password reset. Today there's no password-recovery path
  at all and no email-sending infrastructure anywhere in the project; the
  interim answer is `office_manager` (or `super_admin`, one level up)
  manually resetting a member's password by hand, reusing the existing
  "admin manages their people" pattern — no new infrastructure needed for
  that part. A real forgot-password-email flow is the upgrade, once
  everything else is solid.

## Git, documentation, and delivery requirements
- Meaningful commits at least once per work day — never one commit at the end.
- Feature branches, minimum 3 documented Pull Requests. Phase 1 skeleton work
  (repo scaffold, docker-compose, schema, auth, tenant middleware — everything
  up through the tenant-isolation test) is one continuous foundation, not a
  set of discrete features, so it's committed straight to `master` rather
  than forced into artificial branches. Feature branches + PRs start at
  Phase 2's first vertical slice and continue for every feature after that —
  the minimum-3-PRs requirement is met going forward from there, not
  retrofitted right before submission.
- Log AI usage as you go in `docs/ai_usage.md`: what was asked, what was
  changed, what was learned — do not reconstruct this retroactively.
- Keep `/docs` (OpenAPI export, Postman Collection, architecture diagram/ERD)
  updated as endpoints stabilize, not only at submission time.
- Two seed demo users always available for login (the PDF's required pair):
  one regular client, one office_manager. Separately, `db/seed.sql` also
  seeds the one `super_admin` bootstrap account (see Multi-tenancy
  architecture) — that's infrastructure, not one of the two required demo
  users, and it logs in through the separate platform entry point, not a
  tenant subdomain.
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
