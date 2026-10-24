from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.integrations.llm import (
    FallbackLLM,
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
