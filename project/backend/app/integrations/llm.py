from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

import httpx

from app.schemas.tools import (
    AskClarificationArgs,
    CreateEventArgs,
    EventIdArgs,
    GetCurrentDatetimeArgs,
    ListEventsArgs,
    SearchEventsArgs,
    UpdateEventArgs,
)


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn: ...


def _tool(name: str, description: str, model: type) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": model.model_json_schema(),
        },
    }


TOOL_SCHEMAS = [
    _tool("create_event", "Создать задачу, встречу или напоминание", CreateEventArgs),
    _tool("update_event", "Изменить существующее событие", UpdateEventArgs),
    _tool("complete_event", "Отметить событие выполненным", EventIdArgs),
    _tool("delete_event", "Удалить событие", EventIdArgs),
    _tool("list_events", "Показать события за период", ListEventsArgs),
    _tool("search_events", "Найти события по тексту", SearchEventsArgs),
    _tool("ask_clarification", "Задать уточняющий вопрос", AskClarificationArgs),
    _tool("get_current_datetime", "Получить текущую дату и время", GetCurrentDatetimeArgs),
]


class OpenAICompatibleLLM:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn:
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            payload = response.json()
            message = payload["choices"][0]["message"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError("LLM request failed") from exc

        tool_calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            arguments = function.get("arguments") or "{}"
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise LLMError("LLM returned invalid tool arguments") from exc
            tool_calls.append(
                ToolCall(
                    id=str(item.get("id") or ""),
                    name=str(function.get("name") or ""),
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
            )

        return LLMTurn(
            content=message.get("content"),
            tool_calls=tool_calls,
        )


class RuleBasedLLM:
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn:
        del tools
        if messages and messages[-1].get("role") == "tool":
            return LLMTurn(content=self._tool_reply(messages[-1]))

        text = self._last_user_text(messages)
        lowered = text.lower()

        if "напомни" in lowered or "напоминание" in lowered:
            return self._call(
                "create_event",
                {
                    "type": "reminder",
                    "title": text,
                    "time_expression": text,
                },
            )
        if "встреч" in lowered:
            return self._call(
                "create_event",
                {
                    "type": "meeting",
                    "title": text,
                    "time_expression": text,
                },
            )
        if any(word in lowered for word in ("что у меня", "покажи", "список")):
            if "завтра" in lowered:
                period = "tomorrow"
            elif "недел" in lowered:
                period = "week"
            else:
                period = "today"
            return self._call("list_events", {"period": period, "limit": 20})
        if "найди" in lowered or "поиск" in lowered:
            return self._call("search_events", {"query": text, "limit": 5})
        if "привет" in lowered:
            return LLMTurn(content="Привет! Напиши, что нужно сделать.")
        return LLMTurn(
            content="Пока не понял. Скажи, что создать, показать или найти."
        )

    @staticmethod
    def _last_user_text(messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content") or "")
        return ""

    @staticmethod
    def _tool_reply(message: dict[str, Any]) -> str:
        name = str(message.get("name") or "")
        try:
            result = json.loads(str(message.get("content") or "null"))
        except json.JSONDecodeError:
            return "Готово."

        if name in {"list_events", "search_events"}:
            count = len(result) if isinstance(result, list) else 0
            return "Ничего не нашёл." if count == 0 else f"Нашёл событий: {count}."
        if name == "get_current_datetime" and isinstance(result, dict):
            return f"Сейчас: {result.get('now', '')}."
        if isinstance(result, dict) and result.get("error"):
            return "Не получилось выполнить действие. Уточни данные."
        return "Готово."

    @staticmethod
    def _call(name: str, arguments: dict[str, Any]) -> LLMTurn:
        return LLMTurn(
            tool_calls=[
                ToolCall(
                    id=f"call-{uuid4()}",
                    name=name,
                    arguments=arguments,
                )
            ]
        )


def build_llm_from_env() -> LLMClient:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return RuleBasedLLM()
    return OpenAICompatibleLLM(
        api_key=api_key,
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
    )
