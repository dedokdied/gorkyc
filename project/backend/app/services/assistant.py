from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.integrations.llm import TOOL_SCHEMAS, LLMClient, ToolCall
from app.schemas.chat import (
    ActionInfo,
    ChatResponse,
    Clarification,
)
from app.schemas.tools import (
    AskClarificationArgs,
    CreateEventArgs,
    EventIdArgs,
    ListEventsArgs,
    SearchEventsArgs,
    UpdateEventArgs,
)
from app.services.dialogue import PendingAction, PendingActionStore


class ClarificationNeeded(Exception):
    def __init__(
        self,
        question: str,
        *,
        options: list[str] | None = None,
        missing: list[str] | None = None,
    ) -> None:
        super().__init__(question)
        self.question = question
        self.options = options or []
        self.missing = missing or []


class ToolExecutor(Protocol):
    async def create_event(
        self,
        user_id: str,
        args: CreateEventArgs,
        timezone: str,
    ) -> dict[str, Any]: ...

    async def update_event(
        self,
        user_id: str,
        args: UpdateEventArgs,
        timezone: str,
    ) -> dict[str, Any]: ...

    async def complete_event(
        self,
        user_id: str,
        args: EventIdArgs,
        timezone: str,
    ) -> dict[str, Any]: ...

    async def delete_event(
        self,
        user_id: str,
        args: EventIdArgs,
        timezone: str,
    ) -> dict[str, Any]: ...

    async def list_events(
        self,
        user_id: str,
        args: ListEventsArgs,
        timezone: str,
    ) -> list[dict[str, Any]]: ...

    async def search_events(
        self,
        user_id: str,
        args: SearchEventsArgs,
        timezone: str,
    ) -> list[dict[str, Any]]: ...


class Assistant:
    def __init__(
        self,
        *,
        llm: LLMClient,
        tools: ToolExecutor,
        pending: PendingActionStore,
        max_tool_rounds: int = 2,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._pending = pending
        self._max_tool_rounds = max_tool_rounds

    async def handle(
        self,
        user_id: str,
        text: str,
        *,
        session_id: str | None = None,
        timezone: str = "Europe/Moscow",
    ) -> ChatResponse:
        session = session_id or str(uuid4())
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(timezone)},
            {"role": "user", "content": text},
        ]
        action: ActionInfo | None = None

        for _ in range(self._max_tool_rounds):
            turn = await self._llm.complete(messages, TOOL_SCHEMAS)
            if not turn.tool_calls:
                return ChatResponse(
                    session_id=session,
                    reply=turn.content or "Готово.",
                    action=action,
                )

            messages.append(self._assistant_tool_message(turn.content, turn.tool_calls))
            for call in turn.tool_calls:
                try:
                    result = await self._execute_tool(
                        call,
                        user_id=user_id,
                        session_id=session,
                        timezone=timezone,
                    )
                except ClarificationNeeded as exc:
                    pending = PendingAction(
                        id=str(uuid4()),
                        user_id=user_id,
                        session_id=session,
                        intent=call.name,
                        args=call.arguments,
                        question=exc.question,
                        options=exc.options,
                        missing=exc.missing,
                    )
                    await self._pending.save(pending)
                    return ChatResponse(
                        session_id=session,
                        reply=exc.question,
                        action=ActionInfo(
                            name=call.name,
                            status="needs_clarification",
                        ),
                        clarification=Clarification(
                            id=pending.id,
                            question=exc.question,
                            options=exc.options,
                            missing=exc.missing,
                        ),
                    )

                action = self._action_from_result(call.name, result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        return ChatResponse(
            session_id=session,
            reply="Не смог обработать запрос. Попробуй переформулировать.",
            action=action,
        )

    async def answer_clarification(
        self,
        user_id: str,
        clarification_id: str,
        text: str,
        *,
        session_id: str | None = None,
        timezone: str = "Europe/Moscow",
    ) -> ChatResponse:
        pending = await self._pending.pop(clarification_id)
        if pending is None:
            return ChatResponse(
                session_id=session_id or str(uuid4()),
                reply="Это уточнение уже неактуально. Напиши запрос заново.",
            )

        args = dict(pending.args)
        original_time = str(args.get("time_expression") or "")
        args["time_expression"] = f"{original_time} {text}".strip()
        call = ToolCall(
            id=f"call-{uuid4()}",
            name=pending.intent,
            arguments=args,
        )
        try:
            result = await self._execute_tool(
                call,
                user_id=user_id,
                session_id=pending.session_id,
                timezone=timezone,
            )
        except ClarificationNeeded as exc:
            updated = PendingAction(
                id=str(uuid4()),
                user_id=user_id,
                session_id=pending.session_id,
                intent=pending.intent,
                args=args,
                question=exc.question,
                options=exc.options,
                missing=exc.missing,
            )
            await self._pending.save(updated)
            return ChatResponse(
                session_id=pending.session_id,
                reply=exc.question,
                action=ActionInfo(
                    name=pending.intent,
                    status="needs_clarification",
                ),
                clarification=Clarification(
                    id=updated.id,
                    question=exc.question,
                    options=exc.options,
                    missing=exc.missing,
                ),
            )

        return ChatResponse(
            session_id=pending.session_id,
            reply=self._reply_for_result(pending.intent, result),
            action=self._action_from_result(pending.intent, result),
        )

    async def _execute_tool(
        self,
        call: ToolCall,
        *,
        user_id: str,
        session_id: str,
        timezone: str,
    ) -> Any:
        del session_id
        try:
            if call.name == "create_event":
                args = CreateEventArgs.model_validate(call.arguments)
                return await self._tools.create_event(user_id, args, timezone)
            if call.name == "update_event":
                args = UpdateEventArgs.model_validate(call.arguments)
                return await self._tools.update_event(user_id, args, timezone)
            if call.name == "complete_event":
                args = EventIdArgs.model_validate(call.arguments)
                return await self._tools.complete_event(user_id, args, timezone)
            if call.name == "delete_event":
                args = EventIdArgs.model_validate(call.arguments)
                return await self._tools.delete_event(user_id, args, timezone)
            if call.name == "list_events":
                args = ListEventsArgs.model_validate(call.arguments)
                return await self._tools.list_events(user_id, args, timezone)
            if call.name == "search_events":
                args = SearchEventsArgs.model_validate(call.arguments)
                return await self._tools.search_events(user_id, args, timezone)
            if call.name == "ask_clarification":
                args = AskClarificationArgs.model_validate(call.arguments)
                raise ClarificationNeeded(
                    args.question,
                    options=args.options,
                    missing=args.missing,
                )
            if call.name == "get_current_datetime":
                return {
                    "now": datetime.now(ZoneInfo(timezone)).isoformat(),
                    "timezone": timezone,
                }
        except ValidationError as exc:
            return {"error": "invalid_arguments", "details": str(exc)}
        return {"error": "unknown_tool", "name": call.name}

    @staticmethod
    def _assistant_tool_message(
        content: str | None,
        tool_calls: list[ToolCall],
    ) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in tool_calls
            ],
        }

    @staticmethod
    def _action_from_result(name: str, result: Any) -> ActionInfo:
        entity_id = None
        if isinstance(result, dict):
            raw_id = result.get("id")
            entity_id = str(raw_id) if raw_id else None
        return ActionInfo(name=name, status="done", entity_id=entity_id)

    @staticmethod
    def _reply_for_result(name: str, result: Any) -> str:
        if name in {"list_events", "search_events"}:
            count = len(result) if isinstance(result, list) else 0
            if count == 0:
                return "Ничего не нашёл."
            return f"Нашёл событий: {count}."
        if name == "delete_event":
            return "Удалил событие."
        if name == "complete_event":
            return "Отметил событие выполненным."
        if isinstance(result, dict) and result.get("title"):
            return f"Готово: {result['title']}."
        return "Готово."

    @staticmethod
    def _system_prompt(timezone: str) -> str:
        now = datetime.now(ZoneInfo(timezone)).isoformat()
        return (
            "Ты ассистент задач и встреч. Не считай даты самостоятельно: "
            "передавай исходное выражение времени в time_expression. "
            "Не придумывай event_id. Если не хватает обязательных полей, "
            "используй ask_clarification. Отвечай кратко, по-русски. "
            f"Сейчас: {now}, таймзона: {timezone}."
        )
