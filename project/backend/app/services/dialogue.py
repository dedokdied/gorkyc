from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class PendingAction:
    id: str
    user_id: str
    session_id: str
    intent: str
    args: dict[str, Any]
    question: str
    options: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class PendingActionStore(Protocol):
    async def save(self, action: PendingAction) -> None: ...

    async def get(self, action_id: str) -> PendingAction | None: ...

    async def pop(self, action_id: str) -> PendingAction | None: ...


class InMemoryPendingActionStore:
    def __init__(self) -> None:
        self._actions: dict[str, PendingAction] = {}

    async def save(self, action: PendingAction) -> None:
        self._actions[action.id] = action

    async def get(self, action_id: str) -> PendingAction | None:
        return self._actions.get(action_id)

    async def pop(self, action_id: str) -> PendingAction | None:
        return self._actions.pop(action_id, None)


class ConversationStore(Protocol):
    async def get(self, user_id: str) -> list[dict[str, str]]: ...

    async def append(
        self,
        user_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None: ...


class InMemoryConversationStore:
    """Keep the last N natural-language messages per user.

    Tool calls are not stored: the model only needs its own questions and the
    user's answers to keep the dialogue coherent. Four messages = two complete
    user/assistant exchanges.
    """

    def __init__(self, max_messages: int = 4) -> None:
        self._max_messages = max(2, max_messages)
        self._messages: dict[str, deque[dict[str, str]]] = {}

    async def get(self, user_id: str) -> list[dict[str, str]]:
        return list(self._messages.get(user_id, ()))

    async def append(
        self,
        user_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        if not user_text.strip() or not assistant_text.strip():
            return
        messages = self._messages.setdefault(
            user_id,
            deque(maxlen=self._max_messages),
        )
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": assistant_text})

    async def clear(self, user_id: str) -> None:
        self._messages.pop(user_id, None)
