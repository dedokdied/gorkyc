from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

import httpx

from app.core.config import Settings, settings
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
        api_key: str | None = None,
        model: str = "qwen2.5:3b",
        base_url: str = "http://localhost:11434/v1",
        timeout: float = 120.0,
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
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
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


class OllamaLLM(OpenAICompatibleLLM):
    def __init__(
        self,
        *,
        model: str = "qwen2.5:3b",
        base_url: str = "http://localhost:11434/v1",
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            api_key=None,
            model=model,
            base_url=base_url,
            timeout=timeout,
            client=client,
        )


class FallbackLLM:
    _REFUSAL = re.compile(
        r"не могу (?:создавать|записать|помочь)|оскорбительн|неэтичн",
        re.IGNORECASE,
    )

    def __init__(self, *, primary: LLMClient, fallback: LLMClient) -> None:
        self._primary = primary
        self._fallback = fallback

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn:
        try:
            turn = await self._primary.complete(messages, tools)
        except LLMError:
            return await self._fallback.complete(messages, tools)
        # Some providers refuse to store rude words in a personal note.
        # The user's own note text is not a safety issue for this assistant.
        if not turn.tool_calls and turn.content and self._REFUSAL.search(turn.content):
            return await self._fallback.complete(messages, tools)
        return turn


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

        # Read-only commands must win over creation words: «покажи заметки»
        # contains «заметк», but it is a list request, not a new note.
        if any(word in lowered for word in ("что у меня", "покажи", "список", "какие")):
            if "завтра" in lowered:
                period = "tomorrow"
            elif "недел" in lowered:
                period = "week"
            elif "сегодня" in lowered:
                period = "today"
            elif any(word in lowered for word in ("заметк", "задач", "все", "всё")):
                period = "all"
            else:
                period = "today"
            return self._call("list_events", {"period": period, "limit": 20})
        if "найди" in lowered or "поищи" in lowered or "поиск" in lowered:
            return self._call(
                "search_events",
                {"query": self._search_query(text), "limit": 5},
            )
        if "напомни" in lowered or "напоминание" in lowered:
            return self._call(
                "create_event",
                {
                    "type": "reminder",
                    "title": text,
                    "time_expression": text,
                },
            )
        if "заметк" in lowered or "задач" in lowered:
            return self._call(
                "create_event",
                {
                    "type": "task",
                    "title": self._note_title(text),
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
        if "привет" in lowered:
            return LLMTurn(content="Привет! Напиши, что нужно сделать.")
        return LLMTurn(
            content="Пока не понял. Скажи, что создать, показать или найти."
        )

    @staticmethod
    def _search_query(text: str) -> str:
        query = re.sub(
            r"^\s*(?:найди|поищи|поиск)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return query or text

    @staticmethod
    def _note_title(text: str) -> str:
        title = re.sub(
            r"^\s*(?:сделай|создай|запиши|добавь)\s+"
            r"(?:заметку|заметка|задачу|задача)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return title or text

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


def build_llm_from_env(config: Settings | None = None) -> LLMClient:
    cfg = config or settings
    provider = (cfg.llm_provider or "api").strip().lower()
    if provider in {"rule-based", "rule_based", "none", "off"}:
        return RuleBasedLLM()
    if provider in {"api", "openai", "openai-compatible", "openai_compatible"}:
        api_key = (cfg.llm_api_key or "").strip()
        if not api_key:
            return RuleBasedLLM()
        return FallbackLLM(
            primary=OpenAICompatibleLLM(
                api_key=api_key,
                model=cfg.llm_model or "gpt-4o-mini",
                base_url=cfg.llm_base_url or "https://api.openai.com/v1",
                timeout=cfg.llm_timeout,
            ),
            fallback=RuleBasedLLM(),
        )
    if provider in {"ollama", "local"}:
        return FallbackLLM(
            primary=OllamaLLM(
                model=cfg.llm_model or "qwen2.5:3b",
                base_url=cfg.llm_base_url or "http://localhost:11434/v1",
                timeout=cfg.llm_timeout,
            ),
            fallback=RuleBasedLLM(),
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
