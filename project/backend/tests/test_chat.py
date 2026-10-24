from __future__ import annotations

from typing import Any

import pytest

from app.integrations.llm import FallbackLLM, LLMError, LLMTurn, RuleBasedLLM, ToolCall
from app.schemas.tools import (
    CreateEventArgs,
    EventIdArgs,
    ListEventsArgs,
    SearchEventsArgs,
    UpdateEventArgs,
)
from app.services.assistant import Assistant, ClarificationNeeded
from app.services.dialogue import InMemoryPendingActionStore


class FakeTools:
    def __init__(self, *, require_time: bool = False) -> None:
        self.require_time = require_time
        self.events: list[dict[str, Any]] = []

    async def create_event(
        self,
        user_id: str,
        args: CreateEventArgs,
        timezone: str,
    ) -> dict[str, Any]:
        del user_id, timezone
        if self.require_time and ":" not in (args.time_expression or ""):
            raise ClarificationNeeded(
                "Во сколько поставить встречу?",
                options=["10:00", "15:00"],
                missing=["starts_at"],
            )
        event = {
            "id": f"event-{len(self.events) + 1}",
            "type": args.type,
            "title": args.title,
            "starts_at": args.time_expression,
        }
        self.events.append(event)
        return event

    async def update_event(
        self,
        user_id: str,
        args: UpdateEventArgs,
        timezone: str,
    ) -> dict[str, Any]:
        del user_id, timezone
        return {"id": args.event_id, "title": args.title}

    async def complete_event(
        self,
        user_id: str,
        args: EventIdArgs,
        timezone: str,
    ) -> dict[str, Any]:
        del user_id, timezone
        return {"id": args.event_id}

    async def delete_event(
        self,
        user_id: str,
        args: EventIdArgs,
        timezone: str,
    ) -> dict[str, Any]:
        del user_id, timezone
        return {"id": args.event_id}

    async def list_events(
        self,
        user_id: str,
        args: ListEventsArgs,
        timezone: str,
    ) -> list[dict[str, Any]]:
        del user_id, timezone, args
        return self.events

    async def search_events(
        self,
        user_id: str,
        args: SearchEventsArgs,
        timezone: str,
    ) -> list[dict[str, Any]]:
        del user_id, timezone, args
        return self.events


class ScriptedLLM:
    def __init__(self, *turns: LLMTurn) -> None:
        self._turns = list(turns)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn:
        del messages, tools
        return self._turns.pop(0)


class FailingLLM:
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn:
        del messages, tools
        raise LLMError("ollama is down")


class RecordingLLM:
    def __init__(self, *turns: LLMTurn) -> None:
        self._turns = list(turns)
        self.seen: list[list[dict[str, Any]]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMTurn:
        del tools
        self.seen.append([dict(message) for message in messages])
        return self._turns.pop(0)


def create_call(**arguments: Any) -> LLMTurn:
    return LLMTurn(
        tool_calls=[
            ToolCall(
                id="call-1",
                name="create_event",
                arguments=arguments,
            )
        ]
    )


@pytest.mark.asyncio
async def test_assistant_creates_event_through_tool_call() -> None:
    tools = FakeTools()
    assistant = Assistant(
        llm=ScriptedLLM(
            create_call(
                type="reminder",
                title="Позвонить Ивану",
                time_expression="завтра в 10",
            ),
            LLMTurn(content="Создал напоминание."),
        ),
        tools=tools,
        pending=InMemoryPendingActionStore(),
    )

    response = await assistant.handle("user-1", "Напомни завтра в 10")

    assert response.reply == "Создал напоминание."
    assert response.action is not None
    assert response.action.name == "create_event"
    assert response.action.entity_id == "event-1"
    assert tools.events[0]["title"] == "Позвонить Ивану"


@pytest.mark.asyncio
async def test_assistant_returns_clarification_and_continues_it() -> None:
    tools = FakeTools(require_time=True)
    store = InMemoryPendingActionStore()
    assistant = Assistant(
        llm=ScriptedLLM(
            create_call(
                type="meeting",
                title="Встреча с Иваном",
                time_expression="завтра",
            ),
        ),
        tools=tools,
        pending=store,
    )

    response = await assistant.handle("user-1", "Поставь встречу с Иваном")

    assert response.clarification is not None
    assert response.clarification.question == "Во сколько поставить встречу?"
    assert response.action is not None
    assert response.action.status == "needs_clarification"
    assert await store.get(response.clarification.id) is not None

    updated = await assistant.answer_clarification(
        "user-1",
        response.clarification.id,
        "15:00",
    )

    assert updated.reply == "Готово: Встреча с Иваном."
    assert updated.clarification is None
    assert tools.events[0]["starts_at"] == "завтра 15:00"


@pytest.mark.asyncio
async def test_create_event_without_title_asks_what_to_do() -> None:
    tools = FakeTools()
    assistant = Assistant(
        llm=ScriptedLLM(
            create_call(type="task", time_expression="завтра"),
        ),
        tools=tools,
        pending=InMemoryPendingActionStore(),
    )

    response = await assistant.handle("user-1", "Запланируй на завтра")

    assert response.clarification is not None
    assert response.clarification.question == "Что нужно сделать?"
    assert response.clarification.missing == ["title"]

    updated = await assistant.answer_clarification(
        "user-1",
        response.clarification.id,
        "Подготовить отчёт",
    )

    assert updated.reply == "Готово: Подготовить отчёт."
    assert tools.events[0]["title"] == "Подготовить отчёт"


@pytest.mark.asyncio
async def test_assistant_lists_events() -> None:
    tools = FakeTools()
    tools.events = [{"id": "event-1", "title": "Позвонить Ивану"}]
    assistant = Assistant(
        llm=ScriptedLLM(
            LLMTurn(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="list_events",
                        arguments={"period": "today", "limit": 20},
                    )
                ]
            ),
            LLMTurn(content="У тебя одно событие."),
        ),
        tools=tools,
        pending=InMemoryPendingActionStore(),
    )

    response = await assistant.handle("user-1", "Что у меня сегодня?")

    assert response.reply == "У тебя одно событие."
    assert response.action is not None
    assert response.action.name == "list_events"


@pytest.mark.asyncio
async def test_rule_based_llm_returns_create_event() -> None:
    turn = await RuleBasedLLM().complete(
        [{"role": "user", "content": "Напомни завтра в 10 позвонить Ивану"}],
        [],
    )

    assert turn.tool_calls[0].name == "create_event"
    assert turn.tool_calls[0].arguments["type"] == "reminder"


@pytest.mark.asyncio
async def test_fallback_llm_uses_rule_based_when_local_model_is_down() -> None:
    llm = FallbackLLM(
        primary=FailingLLM(),
        fallback=RuleBasedLLM(),
    )

    turn = await llm.complete(
        [{"role": "user", "content": "Напомни завтра в 10 позвонить Ивану"}],
        [],
    )

    assert turn.tool_calls[0].name == "create_event"


@pytest.mark.asyncio
async def test_assistant_keeps_last_four_messages_in_context() -> None:
    llm = RecordingLLM(
        LLMTurn(content="Первый ответ."),
        LLMTurn(content="Второй ответ."),
        LLMTurn(content="Третий ответ."),
    )
    assistant = Assistant(
        llm=llm,
        tools=FakeTools(),
        pending=InMemoryPendingActionStore(),
    )

    await assistant.handle("user-1", "Первое сообщение")
    await assistant.handle("user-1", "Второе сообщение")
    await assistant.handle("user-1", "Третье сообщение")

    dialogue = [
        message["content"]
        for message in llm.seen[2]
        if message["role"] in {"user", "assistant"}
    ]
    assert dialogue == [
        "Первое сообщение",
        "Первый ответ.",
        "Второе сообщение",
        "Второй ответ.",
        "Третье сообщение",
    ]


@pytest.mark.asyncio
async def test_answer_to_ask_clarification_uses_dialogue_context() -> None:
    tools = FakeTools()
    llm = RecordingLLM(
        LLMTurn(
            tool_calls=[
                ToolCall(
                    id="call-1",
                    name="ask_clarification",
                    arguments={
                        "question": "Во сколько поставить встречу?",
                        "missing": ["starts_at"],
                    },
                )
            ]
        ),
        create_call(
            type="meeting",
            title="Встреча с Иваном",
            time_expression="завтра 15:00",
        ),
        LLMTurn(content="Создал встречу."),
    )
    assistant = Assistant(
        llm=llm,
        tools=tools,
        pending=InMemoryPendingActionStore(),
    )

    first = await assistant.handle("user-1", "Поставь встречу с Иваном завтра")
    assert first.clarification is not None
    assert first.clarification.question == "Во сколько поставить встречу?"

    second = await assistant.answer_clarification(
        "user-1",
        first.clarification.id,
        "в 15:00",
    )

    assert second.reply == "Создал встречу."
    assert tools.events[0]["title"] == "Встреча с Иваном"
    dialogue = [
        message["content"]
        for message in llm.seen[1]
        if message["role"] in {"user", "assistant"}
    ]
    assert "Во сколько поставить встречу?" in dialogue
    assert "в 15:00" in dialogue


def test_system_prompt_forbids_button_hints() -> None:
    prompt = Assistant._system_prompt("Europe/Moscow").lower()

    assert "не предлагай нажимать кнопки" in prompt


@pytest.mark.asyncio
async def test_rule_based_flow_creates_event_and_phrases_result() -> None:
    tools = FakeTools()
    assistant = Assistant(
        llm=RuleBasedLLM(),
        tools=tools,
        pending=InMemoryPendingActionStore(),
    )

    response = await assistant.handle(
        "user-1",
        "Напомни завтра в 10 позвонить Ивану",
    )

    assert response.action is not None
    assert response.action.name == "create_event"
    assert response.reply == "Готово."
    assert tools.events[0]["type"] == "reminder"
