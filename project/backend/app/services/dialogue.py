from __future__ import annotations

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
