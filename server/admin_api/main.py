import re

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin_api.routers.auth import router as auth_router
from admin_api.routers.members import router as members_router
from shared.errors import register_error_handlers
from shared.logging import RequestLoggingMiddleware, configure_logging
from shared.tenant import BASE_DOMAIN

load_dotenv()
configure_logging()

app = FastAPI(title="CaseHub Admin API")
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(members_router)

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
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok"}
