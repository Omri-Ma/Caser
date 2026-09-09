import re

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from client_api.routers.auth import router as auth_router
from client_api.routers.cases import router as cases_router
from client_api.routers.documents import router as documents_router
from client_api.routers.public import router as public_router
from client_api.routers.work_logs import router as work_logs_router
from shared.errors import register_error_handlers
from shared.logging import RequestLoggingMiddleware, configure_logging
from shared.tenant import BASE_DOMAIN

load_dotenv()
configure_logging()

app = FastAPI(title="CaseHub Client API")
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(public_router)
app.include_router(cases_router)
app.include_router(documents_router)
app.include_router(work_logs_router)

# Every tenant gets a subdomain created dynamically at signup, so a fixed,
# hand-typed allow_origins list can't work here — allow_origin_regex trusts
# every subdomain of BASE_DOMAIN automatically. This only controls whether
# the browser lets a page read a response; tenant isolation itself is still
# entirely enforced by get_current_tenant + tenant_id filtering.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=rf"https?://[a-z0-9-]+\.{re.escape(BASE_DOMAIN)}(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition isn't one of the small set of "safe" response
    # headers browsers expose to JS by default — without this, the document
    # download flow's fetch() can read the file bytes but not the real
    # filename FileResponse sets, and silently falls back to "download".
    expose_headers=["Content-Disposition"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok"}
