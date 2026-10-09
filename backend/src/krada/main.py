import re
import time
import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from krada.api import router
from krada.config import get_settings
from krada.database import engine

settings = get_settings()
structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()]
)
log = structlog.get_logger()
app = FastAPI(
    title="Крада API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    """Normalize deliberate API failures without exposing internal exception text."""
    detail: dict[str, object] = exc.detail if isinstance(exc.detail, dict) else {}
    raw_code = detail.get("code")
    raw_message = detail.get("message")
    code = raw_code if isinstance(raw_code, str) else f"http_{exc.status_code}"
    message = raw_message if isinstance(raw_message, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": code, "message": message}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return field locations and error types, never rejected values or request bodies."""
    fields = [{"location": list(error["loc"]), "type": error["type"]} for error in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "validation_error",
                "message": "Проверьте введённые данные",
                "fields": fields,
            }
        },
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_request_id = request.headers.get("x-request-id", "")
    # Restrict untrusted IDs before putting them into logs and downstream event correlation.
    request_id = (
        supplied_request_id
        if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id)
        else str(uuid.uuid4())
    )
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_failed", request_id=request_id, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "internal_error", "message": "Внутренняя ошибка"}},
            headers={"X-Request-ID": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    log.info(
        "request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return response


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        # Only the exception class is logged: connection strings may contain credentials.
        log.warning("readiness_failed", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "database": "unavailable"}
        )
