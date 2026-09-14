import re

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin_api.routers.audit_log import router as audit_log_router
from admin_api.routers.auth import router as auth_router
from admin_api.routers.cases import router as cases_router
from admin_api.routers.dashboard import router as dashboard_router
from admin_api.routers.documents import router as documents_router
from admin_api.routers.invites import router as invites_router
from admin_api.routers.members import router as members_router
from admin_api.routers.narratives import router as narratives_router
from admin_api.routers.platform import router as platform_router
from admin_api.routers.subscriptions import router as subscriptions_router
from admin_api.routers.tenant import router as tenant_router
from admin_api.routers.work_log_import import router as work_log_import_router
from admin_api.routers.work_logs import router as work_logs_router
from shared.errors import register_error_handlers
from shared.logging import RequestLoggingMiddleware, configure_logging
from shared.tenant import BASE_DOMAIN

load_dotenv()
configure_logging()

app = FastAPI(title="Caser Admin API")
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(members_router)
app.include_router(invites_router)
app.include_router(cases_router)
app.include_router(documents_router)
app.include_router(work_logs_router)
app.include_router(work_log_import_router)
app.include_router(narratives_router)
app.include_router(tenant_router)
app.include_router(subscriptions_router)
app.include_router(platform_router)
app.include_router(dashboard_router)
app.include_router(audit_log_router)

# Same allow_origin_regex approach as client_api — see that app for the full
# reasoning. Every tenant subdomain is trusted automatically (both the
# portal's own subdomain and, in production, its -admin suffix), plus the
# fixed platform.<BASE_DOMAIN> address the super_admin login uses.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=rf"https?://[a-z0-9-]+\.{re.escape(BASE_DOMAIN)}(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # See client_api/main.py's identical setting — Content-Disposition isn't
    # exposed to browser JS by default, which would otherwise break the
    # document download flow's real-filename handling.
    expose_headers=["Content-Disposition"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok"}
