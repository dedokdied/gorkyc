from __future__ import annotations

from typing import Protocol

import httpx


class TelegramNotifierError(Exception):
    pass


class ReminderNotifier(Protocol):
    async def send(self, telegram_id: int, text: str) -> None: ...


class TelegramNotifier:
    def __init__(
        self,
        *,
        token: str,
        base_url: str = "https://api.telegram.org",
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def send(self, telegram_id: int, text: str) -> None:
        try:
            response = await self._client.post(
                f"{self._base_url}/bot{self._token}/sendMessage",
                json={
                    "chat_id": telegram_id,
                    "text": text[:4096],
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # The raw httpx error string contains the request URL, and Telegram
            # puts the bot token there. Keep only the API description.
            description = ""
            try:
                payload = exc.response.json()
            except ValueError:
                payload = {}
            if isinstance(payload, dict):
                description = str(payload.get("description") or "")
            detail = f"{exc.response.status_code} {description}".strip()
            raise TelegramNotifierError(f"Telegram send failed: {detail}") from None
        except httpx.HTTPError as exc:
            raise TelegramNotifierError(
                f"Telegram send failed: {type(exc).__name__}"
            ) from None
