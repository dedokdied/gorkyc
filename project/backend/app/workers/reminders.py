from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.services.reminders import ReminderService

logger = get_logger("assistant.reminder_worker")


class ReminderWorker:
    def __init__(
        self,
        service: ReminderService,
        *,
        interval_seconds: float = 30.0,
        enabled: bool = True,
    ) -> None:
        self._service = service
        self._interval_seconds = max(1.0, interval_seconds)
        self._enabled = enabled
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if not self._enabled or self.running:
            return
        self._task = asyncio.create_task(self._run(), name="reminder-worker")
        logger.info("reminder_worker_started", interval_seconds=self._interval_seconds)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is None:
            return
        await self._task
        self._task = None
        logger.info("reminder_worker_stopped")

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self._service.process_due()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("reminder_worker_iteration_failed")

            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self._interval_seconds,
                )
            except TimeoutError:
                pass
