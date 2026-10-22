from __future__ import annotations

from typing import Protocol


class TTSClient(Protocol):
    async def synthesize(self, text: str) -> bytes | None: ...


class NullTTS:
    async def synthesize(self, text: str) -> bytes | None:
        del text
        return None
