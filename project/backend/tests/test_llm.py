from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.integrations.llm import (
    FallbackLLM,
    LLMTurn,
    OpenAICompatibleLLM,
    RuleBasedLLM,
    build_llm_from_env,
)


def test_llm_defaults_to_rule_based_without_api_key() -> None:
    config = Settings(
        _env_file=None,
        llm_provider="api",
        llm_api_key=None,
    )

    llm = build_llm_from_env(config)

    assert isinstance(llm, RuleBasedLLM)


def test_llm_api_provider_with_key_uses_fallback() -> None:
    config = Settings(
        _env_file=None,
        llm_provider="api",
        llm_api_key="test-key",
    )

    llm = build_llm_from_env(config)

    assert isinstance(llm, FallbackLLM)


@pytest.mark.asyncio
async def test_api_llm_sends_bearer_token() -> None:
    captured: dict[str, str | None] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "готово"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        llm = OpenAICompatibleLLM(
            api_key="secret",
            model="test-model",
            base_url="https://example.test/v1",
            client=client,
        )

        turn = await llm.complete([{"role": "user", "content": "привет"}], [])

    assert turn.content == "готово"
    assert captured["auth"] == "Bearer secret"
    assert str(captured["url"]).endswith("/chat/completions")


class _RefusingLLM:
    async def complete(self, messages, tools):
        del messages, tools
        return LLMTurn(
            content="Я не могу создавать заметки с оскорбительным содержанием."
        )


@pytest.mark.asyncio
async def test_refusal_falls_back_to_rule_based_create() -> None:
    llm = FallbackLLM(primary=_RefusingLLM(), fallback=RuleBasedLLM())

    turn = await llm.complete(
        [{"role": "user", "content": "сделай заметку бульба завтра в час"}],
        [],
    )

    assert len(turn.tool_calls) == 1
    call = turn.tool_calls[0]
    assert call.name == "create_event"
    assert call.arguments["type"] == "task"
    assert call.arguments["title"] == "бульба завтра в час"


@pytest.mark.asyncio
async def test_rule_based_llm_recognizes_note() -> None:
    turn = await RuleBasedLLM().complete(
        [{"role": "user", "content": "сделай заметку бульба"}],
        [],
    )

    assert turn.tool_calls[0].arguments["title"] == "бульба"


@pytest.mark.asyncio
async def test_rule_based_llm_lists_notes_instead_of_creating() -> None:
    turn = await RuleBasedLLM().complete(
        [{"role": "user", "content": "покажи заметки"}],
        [],
    )

    call = turn.tool_calls[0]
    assert call.name == "list_events"
    assert call.arguments["period"] == "all"


@pytest.mark.asyncio
async def test_rule_based_llm_lists_meetings_instead_of_creating() -> None:
    turn = await RuleBasedLLM().complete(
        [{"role": "user", "content": "покажи встречи"}],
        [],
    )

    assert turn.tool_calls[0].name == "list_events"


@pytest.mark.asyncio
async def test_rule_based_llm_strips_search_command() -> None:
    turn = await RuleBasedLLM().complete(
        [{"role": "user", "content": "найди договор"}],
        [],
    )

    call = turn.tool_calls[0]
    assert call.name == "search_events"
    assert call.arguments["query"] == "договор"
