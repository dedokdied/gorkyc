from __future__ import annotations

from aiogram.fsm.context import FSMContext


async def clear_clarification(state: FSMContext) -> None:
    """Forget the pending clarification for this chat.

    Every explicit command or menu action starts a new request, so an old
    question must not swallow the next free-form message.
    """
    await state.update_data(clarification_id=None, clarification_options=[])
