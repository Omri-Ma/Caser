import os

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from models import Tenant

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


def get_current_tenant(request: Request, db: Session = Depends(get_db)) -> Tenant:
    """Resolve the tenant from the subdomain in the Host header.

    e.g. Host: acme.lvh.me:8000 -> subdomain "acme". This is the one place
    tenant resolution happens; every tenant-scoped route depends on this
    instead of reading the Host header itself.
    """
    hostname = request.headers.get("host", "").split(":")[0]
    suffix = "." + BASE_DOMAIN

    if not hostname.endswith(suffix) or hostname == BASE_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must be made to a tenant subdomain (e.g. acme.lvh.me)",
        )

    subdomain = hostname[: -len(suffix)]

    tenant = (
        db.query(Tenant)
        .filter(Tenant.subdomain == subdomain, Tenant.active.is_(True))
        .first()
    )
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Read by the request-logging middleware after the route finishes, so
    # every tenant-scoped request is traceable to a tenant_id in the logs
    # without every route having to log it itself.
    request.state.tenant_id = tenant.id

    return tenant
