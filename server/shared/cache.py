import json
import os
from datetime import datetime
from typing import Optional

import redis

# In server/shared on purpose, not duplicated per app (unlike pagination.py/
# errors.py): both backends resolve the same subdomain->Tenant lookup on
# nearly every request (CLAUDE.md's Tech stack / Cache section), so the
# cache-key format and invalidation behavior must be one thing both apps
# agree on, same reasoning as storage.py/plan_limits.py.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Safety-net TTL (CLAUDE.md: "so the common case has zero staleness and the
# TTL only covers whatever invalidation didn't catch") — active invalidation
# below is what actually keeps this correct; the TTL alone would allow up to
# a minute of staleness after a branding update or suspend/reactivate.
TENANT_CACHE_TTL_SECONDS = 60


def _tenant_cache_key(subdomain: str) -> str:
    return f"tenant:subdomain:{subdomain}"


def get_cached_tenant(subdomain: str) -> Optional[dict]:
    """Returns the cached column values for a tenant, or None on a cache
    miss (never cached yet, expired, or invalidated). Caller is responsible
    for falling back to the database on a miss.
    """
    raw = redis_client.get(_tenant_cache_key(subdomain))
    if raw is None:
        return None
    data = json.loads(raw)
    if data.get("created_at") is not None:
        data["created_at"] = datetime.fromisoformat(data["created_at"])
    return data


def set_cached_tenant(subdomain: str, tenant_fields: dict) -> None:
    """tenant_fields is a plain dict of the Tenant row's own columns (see
    shared/tenant.py's _tenant_to_cache_fields) — never the ORM instance
    itself, since that isn't JSON-serializable.
    """
    data = dict(tenant_fields)
    if isinstance(data.get("created_at"), datetime):
        data["created_at"] = data["created_at"].isoformat()
    redis_client.set(_tenant_cache_key(subdomain), json.dumps(data), ex=TENANT_CACHE_TTL_SECONDS)


def invalidate_tenant_cache(subdomain: str) -> None:
    """Called the moment the app itself changes a tenant (branding update,
    super_admin suspend/reactivate) — see CLAUDE.md's Cache section. Safe to
    call even if nothing is cached (e.g. TTL already expired it).
    """
    redis_client.delete(_tenant_cache_key(subdomain))
