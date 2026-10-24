
import pytest

from app.core.config import settings


async def create_event(client, **payload):
    response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def error_code(response) -> str:
    return response.json()["error"]["code"]


@pytest.mark.asyncio
async def test_create_task_and_get(client):
    created = await create_event(
        client,
        type="task",
        title="  Проверить договор  ",
        description="Позвонить Ивану",
        due_at="2026-10-23T10:00:00+03:00",
        timezone="Europe/Moscow",
        recurrence="RRULE:FREQ=DAILY;COUNT=1",
    )
    assert created["title"] == "Проверить договор"
    assert created["type"] == "task"
    assert created["status"] == "planned"
    assert created["source"] == "text"
    assert created["recurrence"] == "RRULE:FREQ=DAILY;COUNT=1"
    assert created["due_at"] == "2026-10-23T10:00:00+03:00"

    response = await client.get(f"/api/v1/events/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_events_are_isolated_by_telegram_account(client):
    headers_a = {
        "X-Telegram-Id": "1001",
        "X-Telegram-Username": "@alice",
        "X-Bot-Secret": settings.bot_internal_secret,
    }
    headers_b = {
        "X-Telegram-Id": "1002",
        "X-Telegram-Username": "@bob",
        "X-Bot-Secret": settings.bot_internal_secret,
    }

    created = await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Личная задача Алисы",
            "timezone": "Europe/Moscow",
        },
        headers=headers_a,
    )
    assert created.status_code == 201, created.text

    alice = await client.get("/api/v1/events", headers=headers_a)
    bob = await client.get("/api/v1/events", headers=headers_b)

    assert [item["title"] for item in alice.json()] == ["Личная задача Алисы"]
    assert bob.json() == []


@pytest.mark.asyncio
async def test_meeting_requires_start_and_end_or_duration(client):
    invalid = await client.post(
        "/api/v1/events",
        json={
            "type": "meeting",
            "title": "Без конца",
            "starts_at": "2026-10-23T15:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert invalid.status_code == 422
    assert error_code(invalid) == "validation_error"

    with_duration = await create_event(
        client,
        type="meeting",
        title="Созвон",
        starts_at="2026-10-23T15:00:00+03:00",
        duration_minutes=60,
        timezone="Europe/Moscow",
    )
    assert with_duration["ends_at"] == "2026-10-23T16:00:00+03:00"
    assert with_duration["duration_minutes"] == 60

    with_ends = await create_event(
        client,
        type="meeting",
        title="Ещё созвон",
        starts_at="2026-10-23T17:00:00+03:00",
        ends_at="2026-10-23T18:30:00+03:00",
        timezone="Europe/Moscow",
    )
    assert with_ends["duration_minutes"] == 90


@pytest.mark.asyncio
async def test_meeting_overlap_returns_409(client):
    await create_event(
        client,
        type="meeting",
        title="Первая встреча",
        starts_at="2026-10-23T15:00:00+03:00",
        ends_at="2026-10-23T16:00:00+03:00",
        timezone="Europe/Moscow",
    )
    response = await client.post(
        "/api/v1/events",
        json={
            "type": "meeting",
            "title": "Пересечение",
            "starts_at": "2026-10-23T15:30:00+03:00",
            "duration_minutes": 60,
            "timezone": "Europe/Moscow",
        },
    )
    assert response.status_code == 409
    assert error_code(response) == "meeting_overlap"


@pytest.mark.asyncio
async def test_reminder_requires_due_at(client):
    invalid = await client.post(
        "/api/v1/events",
        json={
            "type": "reminder",
            "title": "Напомнить",
            "starts_at": "2026-10-23T15:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert invalid.status_code == 422

    reminder = await create_event(
        client,
        type="reminder",
        title="Напомнить",
        due_at="2026-10-23T15:00:00+03:00",
        timezone="Europe/Moscow",
    )
    assert reminder["type"] == "reminder"
    assert reminder["due_at"] == "2026-10-23T15:00:00+03:00"


@pytest.mark.asyncio
async def test_list_period_uses_intersection(client):
    await create_event(
        client,
        type="meeting",
        title="Встреча",
        starts_at="2026-10-23T10:00:00+03:00",
        ends_at="2026-10-23T12:00:00+03:00",
        timezone="Europe/Moscow",
    )
    await create_event(
        client,
        type="task",
        title="Задача с интервалом",
        starts_at="2026-10-23T09:30:00+03:00",
        ends_at="2026-10-23T11:30:00+03:00",
        timezone="Europe/Moscow",
    )
    await create_event(
        client,
        type="task",
        title="Позже",
        due_at="2026-10-23T15:00:00+03:00",
        timezone="Europe/Moscow",
    )
    await create_event(
        client,
        type="task",
        title="Следующий день",
        due_at="2026-10-24T10:00:00+03:00",
        timezone="Europe/Moscow",
    )
    await create_event(
        client,
        type="task",
        title="Без даты",
        timezone="Europe/Moscow",
    )

    response = await client.get(
        "/api/v1/events",
        params={
            "from": "2026-10-23T11:00:00+03:00",
            "to": "2026-10-23T13:00:00+03:00",
        },
    )
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"Встреча", "Задача с интервалом"}


@pytest.mark.asyncio
async def test_patch_meeting_recalculates_ends_and_duration(client):
    meeting = await create_event(
        client,
        type="meeting",
        title="Созвон",
        starts_at="2026-10-23T10:00:00+03:00",
        ends_at="2026-10-23T11:00:00+03:00",
        timezone="Europe/Moscow",
    )

    moved = await client.patch(
        f"/api/v1/events/{meeting['id']}",
        json={"starts_at": "2026-10-23T12:00:00+03:00"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["starts_at"] == "2026-10-23T12:00:00+03:00"
    assert moved.json()["ends_at"] == "2026-10-23T13:00:00+03:00"
    assert moved.json()["duration_minutes"] == 60

    longer = await client.patch(
        f"/api/v1/events/{meeting['id']}",
        json={"duration_minutes": 90},
    )
    assert longer.status_code == 200, longer.text
    assert longer.json()["ends_at"] == "2026-10-23T13:30:00+03:00"

    later_end = await client.patch(
        f"/api/v1/events/{meeting['id']}",
        json={"ends_at": "2026-10-23T14:00:00+03:00"},
    )
    assert later_end.status_code == 200, later_end.text
    assert later_end.json()["duration_minutes"] == 120


@pytest.mark.asyncio
async def test_patch_clears_nullable_fields(client):
    task = await create_event(
        client,
        type="task",
        title="Задача",
        description="Описание",
        due_at="2026-10-23T10:00:00+03:00",
        timezone="Europe/Moscow",
    )
    response = await client.patch(
        f"/api/v1/events/{task['id']}",
        json={"description": None, "due_at": None},
    )
    assert response.status_code == 200, response.text
    assert response.json()["description"] is None
    assert response.json()["due_at"] is None

    status_patch = await client.patch(
        f"/api/v1/events/{task['id']}",
        json={"status": "done"},
    )
    assert status_patch.status_code == 422
    assert error_code(status_patch) == "validation_error"


@pytest.mark.asyncio
async def test_patch_rejects_clearing_required_slots(client):
    meeting = await create_event(
        client,
        type="meeting",
        title="Созвон",
        starts_at="2026-10-23T10:00:00+03:00",
        duration_minutes=60,
        timezone="Europe/Moscow",
    )
    response = await client.patch(
        f"/api/v1/events/{meeting['id']}",
        json={"starts_at": None},
    )
    assert response.status_code == 422

    reminder = await create_event(
        client,
        type="reminder",
        title="Напоминание",
        due_at="2026-10-23T10:00:00+03:00",
        timezone="Europe/Moscow",
    )
    response = await client.patch(
        f"/api/v1/events/{reminder['id']}",
        json={"due_at": None},
    )
    assert response.status_code == 422
    assert error_code(response) == "validation_error"


@pytest.mark.asyncio
async def test_complete_and_delete(client):
    task = await create_event(
        client,
        type="task",
        title="Задача",
        due_at="2026-10-23T10:00:00+03:00",
        timezone="Europe/Moscow",
    )
    completed = await client.post(f"/api/v1/events/{task['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"
    assert completed.json()["completed_at"] is not None

    deleted = await client.delete(f"/api/v1/events/{task['id']}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/events/{task['id']}")
    assert missing.status_code == 404
    assert error_code(missing) == "not_found"


@pytest.mark.asyncio
async def test_error_envelope_and_request_id(client):
    response = await client.get(
        "/api/v1/events",
        params={"type": "unknown"},
        headers={"X-Request-ID": "test-request-id"},
    )
    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "test-request-id"
    assert response.json()["error"]["request_id"] == "test-request-id"
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_events_are_isolated_by_demo_user(client):
    alice = await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Секрет Алисы",
            "due_at": "2026-10-23T10:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
        headers={"X-Demo-User": "alice"},
    )
    assert alice.status_code == 201

    response = await client.get(
        f"/api/v1/events/{alice.json()['id']}",
        headers={"X-Demo-User": "bob"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_datetime_and_timezone_are_rejected(client):
    naive = await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Наивная дата",
            "due_at": "2026-10-23T10:00:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert naive.status_code == 422

    bad_tz = await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Плохая таймзона",
            "due_at": "2026-10-23T10:00:00+03:00",
            "timezone": "No/Such_Zone",
        },
    )
    assert bad_tz.status_code == 422


@pytest.mark.asyncio
async def test_invalid_period_is_rejected_by_domain_validation(client):
    response = await client.get(
        "/api/v1/events",
        params={
            "from": "2026-10-24T00:00:00+03:00",
            "to": "2026-10-23T00:00:00+03:00",
        },
    )
    assert response.status_code == 422
    assert error_code(response) == "validation_error"
