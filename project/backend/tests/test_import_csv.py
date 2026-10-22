from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest

from app.api.deps import get_current_user_id
from app.models.event import EventSource
from app.services.events import EventService

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "import_csv.py"


def load_import_script():
    spec = importlib.util.spec_from_file_location("import_csv_script", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_rows_reads_bom_and_classifies(tmp_path):
    module = load_import_script()
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "id,date,time,text\n"
        "1,2026-10-23,10:00,Напомнить про договор\n"
        "2,2026-10-24,15:00,Встреча с Иваном\n"
        "3,2026-10-25,12:00,Проверить отчёт\n",
        encoding="utf-8-sig",
    )

    rows = module.parse_rows(csv_path, "Europe/Moscow")

    assert [row.event_type for row in rows] == ["reminder", "meeting", "task"]
    assert rows[0].when.isoformat() == "2026-10-23T10:00:00+03:00"
    assert rows[1].title == "Встреча с Иваном"


def test_parse_rows_rejects_invalid_date(tmp_path):
    module = load_import_script()
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "id,date,time,text\n1,not-a-date,10:00,Проверить отчёт\n",
        encoding="utf-8-sig",
    )

    with pytest.raises(ValueError, match="строка 2"):
        module.parse_rows(csv_path, "Europe/Moscow")


def test_payload_for_uses_configured_meeting_duration():
    module = load_import_script()
    event = module.CsvEvent(
        row=2,
        title="Встреча с Иваном",
        event_type="meeting",
        when=datetime.fromisoformat("2026-10-24T15:00:00+03:00"),
    )

    payload = module.payload_for(event, "Europe/Moscow", 30)

    assert payload["starts_at"] == event.when
    assert payload["duration_minutes"] == 30
    assert "due_at" not in payload


@pytest.mark.asyncio
async def test_event_service_can_mark_imported_source(db_session):
    user_id = await get_current_user_id(
        x_demo_user="source-test",
        x_telegram_id=None,
        x_bot_secret=None,
        db=db_session,
    )

    event = await EventService(db_session).create(
        user_id,
        {
            "type": "task",
            "title": "Импортированная задача",
            "due_at": "2026-10-25T12:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
        source=EventSource.import_,
    )

    assert event.source == EventSource.import_
