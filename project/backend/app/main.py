from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models  # noqa: F401
from app.api import auth, events, health, reminders, search, telegram
from app.api.chat import build_chat_router
from app.api.deps import resolve_api_user
from app.api.voice import build_voice_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, get_request_id
from app.core.middleware import RequestIDMiddleware
from app.db import SessionLocal
from app.integrations.llm import build_llm_from_env
from app.integrations.stt import build_stt_from_env
from app.integrations.telegram_notifier import TelegramNotifier
from app.services.assistant import Assistant
from app.services.assistant_tools import DbToolExecutor
from app.services.conversation_db import DbConversationStore
from app.services.events import ConflictError, DomainValidationError, NotFoundError
from app.services.pending_db import DbPendingActionStore
from app.services.reminders import ReminderService
from app.services.voice import VoiceService
from app.workers.reminders import ReminderWorker

configure_logging()
logger = get_logger("assistant.api")

assistant = Assistant(
    llm=build_llm_from_env(),
    tools=DbToolExecutor(),
    pending=DbPendingActionStore(SessionLocal),
    history=DbConversationStore(SessionLocal),
)
voice_service = VoiceService(
    stt=build_stt_from_env(),
    assistant=assistant,
)


_notifier: TelegramNotifier | None = None
_reminder_worker: ReminderWorker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Схема управляется Alembic. create_all в runtime запрещён: он маскирует
    # расхождения миграций и может работать не с той БД.
    global _notifier, _reminder_worker

    token = (settings.telegram_bot_token or "").strip()
    if settings.reminders_enabled and token:
        _notifier = TelegramNotifier(token=token)
        _reminder_worker = ReminderWorker(
            ReminderService(SessionLocal, _notifier),
            interval_seconds=settings.reminders_interval_seconds,
        )
        _reminder_worker.start()
    else:
        logger.info(
            "reminder_worker_disabled",
            enabled=settings.reminders_enabled,
            token_configured=bool(token),
        )

    try:
        yield
    finally:
        if _reminder_worker is not None:
            await _reminder_worker.stop()
            _reminder_worker = None
        if _notifier is not None:
            await _notifier.close()
            _notifier = None


app = FastAPI(title="Voice Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)

_web_origins = [origin.strip() for origin in settings.web_origin.split(",") if origin.strip()]
if _web_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_web_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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
app.include_router(auth.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(telegram.router, prefix="/api/v1")
app.include_router(
    build_chat_router(
        assistant=assistant,
        resolve_user=resolve_api_user,
    ),
    prefix="/api/v1",
)
app.include_router(
    build_voice_router(
        voice=voice_service,
        resolve_user=resolve_api_user,
    ),
    prefix="/api/v1",
)
