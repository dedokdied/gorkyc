import pytest


@pytest.mark.asyncio
async def test_four_required_scenarios_end_to_end(client):
    task_response = await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Проверить договор",
            "description": "Позвонить Ивану",
            "due_at": "2026-10-23T10:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert task_response.status_code == 201
    task = task_response.json()

    meeting_response = await client.post(
        "/api/v1/events",
        json={
            "type": "meeting",
            "title": "Встреча с командой",
            "starts_at": "2026-10-23T15:00:00+03:00",
            "duration_minutes": 60,
            "timezone": "Europe/Moscow",
        },
    )
    assert meeting_response.status_code == 201
    meeting = meeting_response.json()

    reminder_response = await client.post(
        "/api/v1/events",
        json={
            "type": "reminder",
            "title": "Позвонить Ивану",
            "due_at": "2026-10-24T09:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert reminder_response.status_code == 201
    reminder = reminder_response.json()

    # 1. Список за день.
    list_response = await client.get(
        "/api/v1/events",
        params={
            "from": "2026-10-23T00:00:00+03:00",
            "to": "2026-10-23T23:59:59+03:00",
        },
    )
    assert list_response.status_code == 200
    assert {item["id"] for item in list_response.json()} == {task["id"], meeting["id"]}

    # 2. Поиск по старым записям.
    search_response = await client.post(
        "/api/v1/search",
        json={"query": "договор", "limit": 5},
    )
    assert search_response.status_code == 200
    assert search_response.json()["items"][0]["event"]["id"] == task["id"]

    # 3. Изменение встречи.
    moved_response = await client.patch(
        f"/api/v1/events/{meeting['id']}",
        json={"starts_at": "2026-10-23T16:00:00+03:00"},
    )
    assert moved_response.status_code == 200
    assert moved_response.json()["ends_at"] == "2026-10-23T17:00:00+03:00"

    # 4. Завершение задачи.
    complete_response = await client.post(f"/api/v1/events/{task['id']}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "done"

    persisted = await client.get(f"/api/v1/events/{task['id']}")
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "done"

    deleted = await client.delete(f"/api/v1/events/{reminder['id']}")
    assert deleted.status_code == 204

    ready = await client.get("/api/v1/readyz")
    assert ready.status_code == 200
