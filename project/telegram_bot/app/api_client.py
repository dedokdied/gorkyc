from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


class BackendError(Exception):
    def __init__(
        self,
        user_message: str,
        *,
        code: str = "backend_error",
        status_code: int | None = None,
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.code = code
        self.status_code = status_code


@dataclass(slots=True)
class ChatResult:
    session_id: str | None
    reply: str
    action: dict[str, Any] | None = None
    clarification: dict[str, Any] | None = None
    audio_url: str | None = None


class ApiClient:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.api_base_url,
            timeout=settings.request_timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self, telegram_id: int) -> dict[str, str]:
        return {
            "X-Telegram-Id": str(telegram_id),
            "X-Bot-Secret": self._settings.bot_internal_secret,
        }

    async def chat(
        self,
        telegram_id: int,
        text: str,
        *,
        session_id: str | None = None,
        timezone: str | None = None,
    ) -> ChatResult:
        if self._settings.bot_mock_mode:
            return self._mock_chat(telegram_id, text)

        payload = {
            "session_id": session_id,
            "text": text,
            "timezone": timezone or self._settings.app_tz,
        }
        data = await self._request(
            "POST",
            "/chat",
            telegram_id=telegram_id,
            json=payload,
        )
        return self._parse_chat(data)

    async def answer_clarification(
        self,
        telegram_id: int,
        clarification_id: str,
        text: str,
        *,
        session_id: str | None = None,
    ) -> ChatResult:
        if self._settings.bot_mock_mode:
            return self._mock_chat(telegram_id, text)

        data = await self._request(
            "POST",
            f"/clarifications/{clarification_id}/answer",
            telegram_id=telegram_id,
            json={"text": text, "session_id": session_id},
        )
        return self._parse_chat(data)

    async def list_events(
        self,
        telegram_id: int,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            "from": start,
            "to": end,
            "status": "planned",
            "limit": 100,
        }
        data = await self._request(
            "GET",
            "/events",
            telegram_id=telegram_id,
            params={key: value for key, value in params.items() if value is not None},
        )
        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data
        return items if isinstance(items, list) else []

    async def _request(
        self,
        method: str,
        path: str,
        *,
        telegram_id: int,
        **kwargs: Any,
    ) -> Any:
        try:
            response = await self._client.request(
                method,
                path,
                headers=self._headers(telegram_id),
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise BackendError(
                "Backend недоступен. Попробуй ещё раз через минуту.",
                code="backend_unavailable",
            ) from exc

        if response.status_code >= 400:
            raise self._error_from_response(response)

        try:
            return response.json()
        except ValueError as exc:
            raise BackendError(
                "Backend вернул некорректный ответ.",
                code="invalid_response",
                status_code=response.status_code,
            ) from exc

    @staticmethod
    def _error_from_response(response: httpx.Response) -> BackendError:
        message = "Не получилось обработать запрос. Попробуй переформулировать."
        code = "backend_error"
        try:
            payload = response.json()
            error = payload.get("error", {})
            message = error.get("message") or message
            code = error.get("code") or code
        except (ValueError, AttributeError):
            pass
        return BackendError(message, code=code, status_code=response.status_code)

    @staticmethod
    def _parse_chat(data: Any) -> ChatResult:
        if not isinstance(data, dict) or not isinstance(data.get("reply"), str):
            raise BackendError(
                "Backend вернул ответ без текста.",
                code="invalid_response",
            )
        clarification = data.get("clarification")
        return ChatResult(
            session_id=data.get("session_id"),
            reply=data["reply"],
            action=data.get("action"),
            clarification=clarification if isinstance(clarification, dict) else None,
            audio_url=data.get("audio_url"),
        )

    @staticmethod
    def _mock_chat(telegram_id: int, text: str) -> ChatResult:
        lowered = text.lower()
        if "напомни" in lowered or "напоминание" in lowered:
            reply = "Mock: напоминание создано. В реальном backend здесь будет дата и время."
        elif "встреч" in lowered:
            reply = "Mock: встреча создана. В реальном backend здесь будет подтверждение."
        elif "найди" in lowered or "поиск" in lowered:
            reply = "Mock: поиск работает. В реальном backend здесь будут результаты."
        else:
            reply = "Mock-ответ: backend ещё не подключён, но бот работает."
        return ChatResult(
            session_id=f"mock-{telegram_id}",
            reply=reply,
            action={"name": "mock", "status": "done"},
        )
