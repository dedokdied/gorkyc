from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any, Protocol

import httpx

from app.core.config import Settings, settings


class STTError(Exception):
    pass


class STTClient(Protocol):
    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str: ...


class OpenAIWhisperSTT:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "whisper-1",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
        language: str = "ru",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._language = language
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        try:
            response = await self._client.post(
                f"{self._base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (filename, audio, content_type)},
                data={
                    "model": self._model,
                    "language": self._language,
                    "response_format": "json",
                },
            )
            response.raise_for_status()
            text = response.json().get("text")
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise STTError("STT API request failed") from exc

        if not isinstance(text, str):
            raise STTError("STT API returned no text")
        return text.strip()


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
    def __init__(self, reason: str = "STT is disabled") -> None:
        self._reason = reason

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        del audio, filename, content_type
        raise STTError(self._reason)


def build_stt_from_env(config: Settings | None = None) -> STTClient:
    cfg = config or settings
    provider = (cfg.stt_provider or "api").strip().lower()
    if provider in {"none", "off", "unavailable"}:
        return UnavailableSTT()
    if provider in {"api", "openai", "openai-compatible", "openai_compatible"}:
        api_key = (cfg.stt_api_key or "").strip()
        if not api_key:
            return UnavailableSTT("STT_API_KEY is not configured")
        return OpenAIWhisperSTT(
            api_key=api_key,
            model=cfg.stt_model,
            base_url=cfg.stt_base_url,
            timeout=cfg.stt_timeout,
            language=cfg.stt_language,
        )
    if provider in {"faster-whisper", "faster_whisper", "local"}:
        return FasterWhisperSTT(
            model_size=cfg.stt_model,
            device=cfg.stt_device,
            compute_type=cfg.stt_compute_type,
            language=cfg.stt_language,
        )
    raise ValueError(f"Unsupported STT_PROVIDER: {provider}")
