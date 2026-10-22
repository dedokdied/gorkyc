from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я ассистент задач и встреч.\n\n"
        "Напиши, что нужно сделать, например:\n"
        "«Напомни завтра в 10 позвонить Ивану»\n\n"
        "Посмотреть планы: /today, /tomorrow, /week.\n"
        "Пока я работаю с текстом. Голосовые сообщения подключим позже."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Что я умею:\n"
        "— создавать задачи, встречи и напоминания;\n"
        "— уточнять дату и время;\n"
        "— показывать список на день: /today, /tomorrow, /week;\n"
        "— искать по старым записям.\n\n"
        "Просто напиши фразу обычным языком."
    )
