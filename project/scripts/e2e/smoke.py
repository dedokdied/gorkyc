from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import httpx


class SmokeError(RuntimeError):
    pass


def check(condition: Any, message: str) -> None:
    if not condition:
        raise SmokeError(message)


async def chat(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    text: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    response = await client.post(
        "chat",
        headers=headers,
        json={
            "session_id": session_id,
            "text": text,
            "timezone": "Europe/Moscow",
        },
    )
    if response.status_code >= 400:
        raise SmokeError(
            f"chat «{text}»: HTTP {response.status_code} {response.text}"
        )

    payload = response.json()
    check(isinstance(payload.get("reply"), str), f"chat «{text}»: нет reply")
    check(bool(payload["reply"].strip()), f"chat «{text}»: пустой reply")
    return payload


async def answer_clarification(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    clarification_id: str,
    text: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    response = await client.post(
        f"clarifications/{clarification_id}/answer",
        headers=headers,
        json={
            "session_id": session_id,
            "text": text,
        },
    )
    if response.status_code >= 400:
        raise SmokeError(
            f"clarification «{text}»: HTTP {response.status_code} {response.text}"
        )

    payload = response.json()
    check(isinstance(payload.get("reply"), str), "clarification: нет reply")
    return payload


async def run(args: argparse.Namespace) -> None:
    headers = {
        "X-Telegram-Id": str(args.telegram_id),
        "X-Bot-Secret": args.bot_secret,
    }

    base_url = args.base_url.rstrip("/") + "/"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        health = await client.get("healthz")
        check(health.status_code == 200, f"healthz: HTTP {health.status_code}")

        reminder = await chat(
            client,
            headers,
            "Напомни завтра в 10 утра позвонить Ивану",
        )
        reminder_action = reminder.get("action") or {}
        check(
            reminder_action.get("name") == "create_event",
            "напоминание не создано",
        )

        meeting = await chat(
            client,
            headers,
            "Поставь встречу с командой завтра",
        )
        clarification = meeting.get("clarification") or {}
        if clarification.get("id"):
            meeting = await answer_clarification(
                client,
                headers,
                str(clarification["id"]),
                "В 15:00",
                session_id=meeting.get("session_id"),
            )
        meeting_action = meeting.get("action") or {}
        check(
            meeting_action.get("name") == "create_event",
            "встреча не создана",
        )

        listing = await chat(client, headers, "Что у меня завтра?")
        check(bool(listing.get("reply")), "пустой список событий")

        search = await chat(client, headers, "Найди задачу про договор")
        check(bool(search.get("reply")), "поиск не вернул ответ")

        if args.voice_file:
            audio = args.voice_file.read_bytes()
            response = await client.post(
                "voice",
                headers=headers,
                files={
                    "file": (
                        args.voice_file.name,
                        audio,
                        "audio/ogg",
                    )
                },
                data={"timezone": "Europe/Moscow"},
            )
            check(
                response.status_code == 200,
                f"voice: HTTP {response.status_code} {response.text}",
            )
            check(bool(response.json().get("transcript")), "voice: нет transcript")
        else:
            print("voice: пропущен, задай --voice-file для проверки STT")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-проверка Telegram MVP API")
    parser.add_argument(
        "--base-url",
        default=os.getenv("BACKEND_URL", "http://localhost:8000/api/v1"),
    )
    parser.add_argument(
        "--telegram-id",
        type=int,
        default=int(os.getenv("E2E_TELEGRAM_ID", "1")),
    )
    parser.add_argument(
        "--bot-secret",
        default=os.getenv("BOT_INTERNAL_SECRET", "change-me"),
    )
    parser.add_argument("--voice-file", type=Path)
    return parser.parse_args()


def main() -> int:
    try:
        asyncio.run(run(parse_args()))
    except SmokeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"FAIL: API недоступен: {exc}", file=sys.stderr)
        return 1

    print("OK: health, reminder, meeting, list, search")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
