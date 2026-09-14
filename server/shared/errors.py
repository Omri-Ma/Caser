from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.error_messages import translate_pydantic_error


def register_error_handlers(app: FastAPI) -> None:
    """Make every error response share one JSON shape: {"error": ..., "field": ...}.
    Every message text — HTTPException.detail (set by application code from
    shared/error_messages.py) and Pydantic's own auto-generated validation
    messages (translated here) — is Hebrew, per CLAUDE.md's app-wide rule.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"] if part != "body")
        return JSONResponse(
            status_code=422,
            content={"error": translate_pydantic_error(first_error), "field": field},
        )
