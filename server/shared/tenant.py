import os

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, make_transient_to_detached

from shared.cache import get_cached_tenant, set_cached_tenant
from shared.database import get_db
from shared.models import Tenant
from shared import error_messages as E

BASE_DOMAIN = os.getenv("BASE_DOMAIN", "lvh.me")

# Checked at signup so a real firm can never claim a subdomain that's
# reserved for a system-meaningful address — most importantly `platform`,
# the fixed super_admin login entry point (see CLAUDE.md's Multi-tenancy
# architecture), where a collision would be a real security problem, not a
# hypothetical one.
RESERVED_SUBDOMAINS = {
    "platform",
    "www",
    "api",
    "admin",
    "client",
    "static",
    "mail",
    "app",
    "assets",
    "cdn",
    "docs",
    "health",
    "localhost",
}


def is_reserved_subdomain(subdomain: str) -> bool:
    """Checked at signup, alongside the uniqueness check. Two rules: the
    fixed blocklist above, and a pattern rule — no subdomain may *end in*
    `-admin`, since that suffix is meaningful in production (a tenant's CMS
    lives at `<subdomain>-admin.<domain>`, see CLAUDE.md's Multi-tenancy
    architecture) — a firm registering e.g. `acme-admin` would otherwise
    collide with the real Acme firm's own CMS address.
    """
    return subdomain in RESERVED_SUBDOMAINS or subdomain.endswith("-admin")


# Tenant's own columns (see shared/models/tenant.py) — what actually gets
# cached/restored. Kept as an explicit list rather than introspecting the
# model so a future new column doesn't silently start round-tripping through
# Redis (or silently fail to) without a deliberate decision either way.
_TENANT_CACHE_COLUMNS = ("id", "name", "subdomain", "logo_url", "primary_color", "active", "created_at")


def _tenant_to_cache_fields(tenant: Tenant) -> dict:
    return {column: getattr(tenant, column) for column in _TENANT_CACHE_COLUMNS}


def get_current_tenant(request: Request, db: Session = Depends(get_db)) -> Tenant:
    """Resolve the tenant from the subdomain in the Host header.

    e.g. Host: acme.lvh.me:8000 -> subdomain "acme". This is the one place
    tenant resolution happens; every tenant-scoped route depends on this
    instead of reading the Host header itself.

    Redis-backed cache in front of the MySQL lookup (CLAUDE.md's Cache
    section) — this is the one query that runs on nearly every request to
    either backend and rarely changes. On a cache hit, the cached column
    values are merged into the session with load=False so the returned
    Tenant is still a normal, session-attached ORM instance (routes like
    admin_api's PATCH /tenant mutate it and call db.commit()) without
    actually issuing the SELECT the cache exists to avoid. Correctness
    relies on active invalidation (see shared/cache.py's
    invalidate_tenant_cache, called from the branding-update and
    super_admin suspend/reactivate routes) plus a short TTL as a safety net
    for whatever invalidation didn't catch — never on Redis alone.
    """
    hostname = request.headers.get("host", "").split(":")[0]
    suffix = "." + BASE_DOMAIN

    if not hostname.endswith(suffix) or hostname == BASE_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=E.REQUEST_MUST_BE_TO_TENANT_SUBDOMAIN,
        )

    subdomain = hostname[: -len(suffix)]

    cached_fields = get_cached_tenant(subdomain)
    if cached_fields is not None:
        # Building a plain Tenant(**cached_fields) is a *transient* instance
        # as far as SQLAlchemy is concerned (no identity key yet) — merging
        # that with load=False is rejected outright, since load=False means
        # "trust this state, don't check the database," which only makes
        # sense for an instance that already claims to represent a real,
        # persisted row. make_transient_to_detached stamps that identity key
        # on without touching the database either, which is exactly the
        # documented SQLAlchemy pattern for reconstituting an object from an
        # external cache like this one.
        candidate = Tenant(**cached_fields)
        make_transient_to_detached(candidate)
        tenant = db.merge(candidate, load=False)
    else:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.subdomain == subdomain, Tenant.active.is_(True))
            .first()
        )
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=E.TENANT_NOT_FOUND)
        set_cached_tenant(subdomain, _tenant_to_cache_fields(tenant))

    # Read by the request-logging middleware after the route finishes, so
    # every tenant-scoped request is traceable to a tenant_id in the logs
    # without every route having to log it itself.
    request.state.tenant_id = tenant.id

    return tenant
