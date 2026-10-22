from __future__ import annotations

import asyncio
import os
from io import BytesIO
from typing import Any, Protocol


class STTError(Exception):
    pass


class STTClient(Protocol):
    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str: ...


class FasterWhisperSTT:
    def __init__(
        self,
        *,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "ru",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise STTError(
                    "faster-whisper не установлен. Выполни: pip install faster-whisper"
                ) from exc
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    def _transcribe_sync(self, audio: bytes) -> str:
        model = self._load_model()
        segments, _ = model.transcribe(
            BytesIO(audio),
            language=self._language,
            vad_filter=True,
        )
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(parts).strip()

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        del filename, content_type
        try:
            return await asyncio.to_thread(self._transcribe_sync, audio)
        except STTError:
            raise
        except Exception as exc:
            raise STTError("faster-whisper transcription failed") from exc


class UnavailableSTT:
    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        del audio, filename, content_type
        raise STTError("STT is disabled")


def build_stt_from_env() -> STTClient:
    provider = os.getenv("STT_PROVIDER", "faster-whisper").strip().lower()
    if provider in {"none", "off", "unavailable"}:
        return UnavailableSTT()
    if provider in {"faster-whisper", "faster_whisper"}:
        return FasterWhisperSTT(
            model_size=os.getenv("STT_MODEL", "small"),
            device=os.getenv("STT_DEVICE", "cpu"),
            compute_type=os.getenv("STT_COMPUTE_TYPE", "int8"),
            language=os.getenv("STT_LANGUAGE", "ru"),
        )
    raise ValueError(f"Unsupported STT_PROVIDER: {provider}")
