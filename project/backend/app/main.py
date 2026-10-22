from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models  # noqa: F401
from app.api import chat, events, health, search
from app.core.logging import configure_logging, get_logger, get_request_id
from app.core.middleware import RequestIDMiddleware
from app.services.events import ConflictError, DomainValidationError, NotFoundError

configure_logging()
logger = get_logger("assistant.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Схема управляется Alembic. create_all в runtime запрещён: он маскирует
    # расхождения миграций и может работать не с той БД.
    yield


app = FastAPI(title="Voice Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or get_request_id() or "-"


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(422, "validation_error", "invalid request", request)


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(404, "not_found", str(exc) or "not found", request)


@app.exception_handler(ConflictError)
async def conflict_exception_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return _error_response(409, "meeting_overlap", str(exc) or "conflict", request)


@app.exception_handler(DomainValidationError)
async def domain_validation_exception_handler(request: Request, exc: DomainValidationError) -> JSONResponse:
    return _error_response(422, "validation_error", str(exc) or "invalid request", request)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", "http_error"))
        message = str(detail.get("message", detail))
    else:
        message = str(detail)
        code = "not_found" if exc.status_code == 404 else "unauthorized" if exc.status_code == 401 else "http_error"
    return _error_response(exc.status_code, code, message, request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", request_id=_request_id(request), path=request.url.path)
    return _error_response(500, "internal_error", "internal server error", request)


app.include_router(health.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
