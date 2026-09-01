import re

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.errors import register_error_handlers
from core.logging import RequestLoggingMiddleware, configure_logging
from core.tenant import BASE_DOMAIN
from routers.auth import router as auth_router
from routers.members import router as members_router

load_dotenv()
configure_logging()

app = FastAPI(title="CaseHub API")
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(members_router)

# Every tenant gets a subdomain created dynamically at signup, so a fixed,
# hand-typed allow_origins list can't work here — allow_origin_regex trusts
# every subdomain of BASE_DOMAIN automatically. This only controls whether
# the browser lets a page read a response; tenant isolation itself is still
# entirely enforced by get_current_tenant + tenant_id filtering, not by CORS.
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
