from __future__ import annotations

from app.integrations.stt import (
    FasterWhisperSTT,
    UnavailableSTT,
    build_stt_from_env,
)


def test_stt_defaults_to_local_faster_whisper(monkeypatch) -> None:
    monkeypatch.delenv("STT_PROVIDER", raising=False)

    stt = build_stt_from_env()

    assert isinstance(stt, FasterWhisperSTT)


def test_stt_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("STT_PROVIDER", "none")

    stt = build_stt_from_env()

    assert isinstance(stt, UnavailableSTT)
