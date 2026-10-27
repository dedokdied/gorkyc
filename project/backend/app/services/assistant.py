from __future__ import annotations

import json
import re
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
from app.services.datetime_parser import DatetimeParser
from app.services.dialogue import (
    ConversationStore,
    InMemoryConversationStore,
    PendingAction,
    PendingActionStore,
)

_NEW_REQUEST = re.compile(
    r"\b(?:создай|сделай|запиши|добавь|запланируй|поставь)\b"
    r".*\b(?:заметк|задач|встреч|напомин)"
    r"|\b(?:покажи|найди|удали|отметь|перенеси|измени|список)\b"
    r"|\bчто у меня\b|\bкакие у меня\b",
    re.IGNORECASE,
)


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
        history: ConversationStore | None = None,
        max_tool_rounds: int = 4,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._pending = pending
        self._history = history or InMemoryConversationStore(max_messages=4)
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
        history = [
            {"role": item["role"], "content": item["content"]}
            for item in await self._history.get(user_id, session)
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(timezone)},
            *history,
            {"role": "user", "content": text},
        ]
        action: ActionInfo | None = None
        last_error: str | None = None

        for _ in range(self._max_tool_rounds):
            turn = await self._llm.complete(messages, TOOL_SCHEMAS)
            if not turn.tool_calls:
                reply = turn.content or "Готово."
                if (
                    last_error is not None
                    and action is not None
                    and action.status == "failed"
                ):
                    # The model sometimes answers «Готово.» even when the tool
                    # returned a conflict or a validation error. Never confirm
                    # an action that failed.
                    reply = last_error
                response = ChatResponse(
                    session_id=session,
                    reply=reply,
                    action=action,
                )
                await self._remember(user_id, session, text, response.reply)
                return response

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
                    response = ChatResponse(
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
                    await self._remember(user_id, session, text, response.reply)
                    return response

                action = self._action_from_result(call.name, result)
                if isinstance(result, dict) and result.get("error"):
                    last_error = str(
                        result.get("message") or "Не получилось выполнить действие."
                    )
                else:
                    last_error = None
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        response = ChatResponse(
            session_id=session,
            reply="Не смог обработать запрос. Попробуй переформулировать.",
            action=action,
        )
        await self._remember(user_id, session, text, response.reply)
        return response

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
        if str(pending.user_id) != str(user_id):
            # Another account must not be able to consume someone else's
            # question just by guessing its id.
            await self._pending.save(pending)
            return ChatResponse(
                session_id=session_id or str(uuid4()),
                reply="Это уточнение уже неактуально. Напиши запрос заново.",
            )

        # ask_clarification does not carry tool arguments. Let the model see
        # its own question in the dialogue history and resolve the answer.
        if pending.intent == "ask_clarification":
            return await self.handle(
                user_id,
                text,
                session_id=pending.session_id,
                timezone=timezone,
            )

        # A complete new command supersedes the pending question. Without
        # this, «покажи планы» or a repeated «сделай заметку …» would be
        # glued to the old time expression and the bot would ask again.
        if self._looks_like_new_request(text):
            return await self.handle(
                user_id,
                text,
                session_id=pending.session_id,
                timezone=timezone,
            )

        args = self._merge_answer(pending, text, timezone)
        if set(pending.missing) & {"starts_at", "due_at"}:
            merged_expression = str(args.get("time_expression") or "")
            merged_time = (
                DatetimeParser().parse(merged_expression, timezone)
                if merged_expression
                else None
            )
            if merged_time is None or merged_time.date is None:
                # The answer still has no date. Repeating the same question
                # would loop forever, so ask explicitly for a full date/time.
                response = ChatResponse(
                    session_id=pending.session_id,
                    reply=(
                        "Не понял дату. Напиши, например: «завтра в 16:00» "
                        "или «30 октября в 16:00»."
                    ),
                    action=ActionInfo(name=pending.intent, status="failed"),
                )
                await self._remember(user_id, pending.session_id, text, response.reply)
                return response
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
            response = ChatResponse(
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
            await self._remember(user_id, pending.session_id, text, response.reply)
            return response

        response = ChatResponse(
            session_id=pending.session_id,
            reply=self._reply_for_result(pending.intent, result),
            action=self._action_from_result(pending.intent, result),
        )
        await self._remember(user_id, pending.session_id, text, response.reply)
        return response

    @staticmethod
    def _looks_like_new_request(text: str) -> bool:
        """True when the message is a new command, not an answer.

        Conservative on purpose: only imperative create/list/search verbs
        count. A bare «завтра в час» or «бульба» must stay an answer to the
        pending question.
        """
        return bool(_NEW_REQUEST.search(text))

    @staticmethod
    def _merge_answer(
        pending: PendingAction,
        text: str,
        timezone: str = "Europe/Moscow",
    ) -> dict[str, Any]:
        """Put a free-form answer into the field the server asked about."""
        args = dict(pending.args)
        missing = set(pending.missing)

        if "title" in missing:
            args["title"] = text
            return args
        if missing & {"starts_at", "due_at", "time_expression", "ends_at"}:
            args["time_expression"] = Assistant._merge_time_expression(
                args.get("time_expression"),
                text,
                timezone,
            )
            return args
        if missing & {"duration_minutes", "duration_expression"}:
            args["duration_expression"] = text
            return args
        if "description" in missing:
            args["description"] = text
            return args

        # Older pending actions did not always declare missing fields.
        args["time_expression"] = Assistant._merge_time_expression(
            args.get("time_expression"),
            text,
            timezone,
        )
        return args

    @staticmethod
    def _merge_time_expression(
        original: Any,
        answer: str,
        timezone: str,
    ) -> str:
        """Combine the previously known time with the user's answer.

        A complete date and time in the answer replaces the old expression.
        A time-only answer keeps the date from the previous expression and
        vice versa. This prevents «завтра» + «в 15:00» loops and stops old
        times from winning over a corrected one.
        """
        original_text = str(original or "").strip()
        answer = answer.strip()
        if not original_text:
            return answer
        if not answer:
            return original_text

        parser = DatetimeParser()
        parsed_answer = parser.parse(answer, timezone)
        if parsed_answer.starts_at is not None and not parsed_answer.is_ambiguous:
            return answer

        parsed_original = parser.parse(original_text, timezone)
        target_date = parsed_answer.date or parsed_original.date
        target_time = parsed_answer.time or parsed_original.time
        if target_date is not None and target_time is not None:
            try:
                zone = ZoneInfo(timezone)
            except (KeyError, ValueError):
                zone = ZoneInfo("Europe/Moscow")
            combined = datetime.combine(
                target_date.date(),
                target_time,
                tzinfo=zone,
            )
            return combined.isoformat()

        if parsed_answer.date is not None:
            return answer
        if answer not in original_text:
            return f"{original_text} {answer}".strip()
        return original_text

    async def _remember(
        self,
        user_id: str,
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        await self._history.append(user_id, session_id, user_text, assistant_text)

    async def clear_history(self, user_id: str, session_id: str | None) -> None:
        if session_id:
            await self._history.clear(user_id, session_id)
            await self._pending.clear_session(user_id, session_id)

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
            fields = {
                str(error["loc"][0])
                for error in exc.errors()
                if error.get("loc")
            }
            if call.name == "create_event" and "title" in fields:
                raise ClarificationNeeded(
                    "Что нужно сделать?",
                    missing=["title"],
                ) from exc
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
        if isinstance(result, dict) and result.get("error"):
            return ActionInfo(name=name, status="failed")
        entity_id = None
        if isinstance(result, dict):
            raw_id = result.get("id")
            entity_id = str(raw_id) if raw_id else None
        return ActionInfo(name=name, status="done", entity_id=entity_id)

    @staticmethod
    def _reply_for_result(name: str, result: Any) -> str:
        if isinstance(result, dict) and result.get("error"):
            return str(result.get("message") or "Не получилось выполнить действие.")
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
            "Ты ассистент задач и встреч. Учитывай историю диалога: если "
            "пользователь отвечает на твой предыдущий вопрос, используй "
            "контекст. Не считай даты самостоятельно: передавай исходное "
            "выражение времени в time_expression. time_expression всегда "
            "пиши дословно по-русски, как сказал пользователь: не переводи "
            "его на английский и не заменяй относительные даты (никаких "
            "«tomorrow», «today», «next week»). В title — только суть "
            "события, без даты, времени и служебных слов вроде «добавь», "
            "«поставь», «напомни». Если спрашивают про встречи, задачи или "
            "напоминания, передавай соответствующий type в list_events. "
            "Для произвольного периода («с 3 по 7 ноября») передавай в "
            "list_events date_from и date_to в формате YYYY-MM-DD, считая "
            "год по текущей дате. "
            "Не придумывай event_id. "
            "Если не хватает обязательных полей, используй ask_clarification. "
            "Для создания события вызывай create_event с уже известными "
            "полями: недостающие поля сервер уточнит сам. Никогда не "
            "подставляй дату или время, которых нет в запросе: если сказано "
            "только «в пятницу», передай это без часов. Сохраняй текст "
            "заметки как есть и не отказывайся из-за грубых слов. Никогда не "
            "предлагай нажимать кнопки и не упоминай кнопки или интерфейс: "
            "все вопросы задавай обычным текстом. Не используй markdown-"
            "разметку (**...**, #, таблицы): только обычный текст и строки, "
            "начинающиеся с «—». Отвечай кратко. Говори "
            "ИСКЛЮЧИТЕЛЬНО на русском языке, даже если пользователь пишет или "
            "говорит по-английски: никогда не переходи на английский, не "
            "вставляй английские слова и фразы и не дублируй ответ переводом. "
            "Латиницу используй только в неизбежных именах собственных. "
            f"Сейчас: {now}, таймзона: {timezone}."
        )
