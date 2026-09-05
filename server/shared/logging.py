import logging
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def configure_logging() -> None:
    """Structured (JSON) logging instead of print() — set up once at app
    startup so every route added afterward gets it automatically via the
    middleware below, rather than each route logging by hand.
    """
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )


logger = structlog.get_logger("casehub.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with its resolved tenant_id — essential for
    tracing isolation bugs, per CLAUDE.md's logging requirement.

    tenant_id isn't known at the start of the request (it's resolved by the
    get_current_tenant dependency, which runs after this middleware calls
    into the route). get_current_tenant stashes it on request.state as soon
    as it resolves the tenant; this middleware reads it back after call_next
    returns. Requests that never touch a tenant-scoped route (e.g. /health,
    /auth/register) simply log tenant_id=None.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            tenant_id=getattr(request.state, "tenant_id", None),
        )
        return response
