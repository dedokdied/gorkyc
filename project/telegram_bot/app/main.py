from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.api_client import ApiClient
from app.config import get_settings
from app.handlers import clarification, events, onboarding, start, text, voice

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не задан. Заполни project/.env или project/telegram_bot/.env."
        )

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    api = ApiClient(settings)
    dispatcher["api"] = api
    dispatcher["settings"] = settings
    dispatcher.include_routers(
        start.router,
        onboarding.router,
        events.router,
        clarification.router,
        voice.router,
        text.router,
    )

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Начать"),
                BotCommand(command="menu", description="Главное меню"),
                BotCommand(command="today", description="Планы на сегодня"),
                BotCommand(command="tomorrow", description="Планы на завтра"),
                BotCommand(command="week", description="Планы на неделю"),
                BotCommand(command="search", description="Поиск по записям"),
                BotCommand(command="link", description="Связать с сайтом"),
                BotCommand(command="settings", description="Часовой пояс"),
                BotCommand(command="cancel", description="Отменить уточнение"),
                BotCommand(command="help", description="Что я умею"),
            ]
        )
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await api.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("bot stopped")
