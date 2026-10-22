import pytest


async def create(client, **payload):
    response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_search_returns_matching_event_with_real_score(client):
    task = await create(
        client,
        type="task",
        title="Проверить договор с Иваном",
        description="Подготовить документы",
        due_at="2026-10-23T10:00:00+03:00",
        timezone="Europe/Moscow",
    )
    await create(
        client,
        type="meeting",
        title="Презентация проекта",
        starts_at="2026-10-24T15:00:00+03:00",
        duration_minutes=60,
        timezone="Europe/Moscow",
    )

    response = await client.post("/api/v1/search", json={"query": "договор", "limit": 5})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items
    assert items[0]["event"]["id"] == task["id"]
    assert items[0]["score"] > 0
    assert "договор" in items[0]["snippet"].lower()


@pytest.mark.asyncio
async def test_search_type_filter_and_period(client):
    await create(
        client,
        type="task",
        title="Презентация: подготовить слайды",
        due_at="2026-10-23T10:00:00+03:00",
        timezone="Europe/Moscow",
    )
    meeting = await create(
        client,
        type="meeting",
        title="Презентация проекта",
        starts_at="2026-10-24T15:00:00+03:00",
        duration_minutes=60,
        timezone="Europe/Moscow",
    )

    response = await client.post(
        "/api/v1/search",
        json={"query": "презентация", "type": "meeting"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["event"]["id"] for item in items] == [meeting["id"]]

    response = await client.post(
        "/api/v1/search",
        json={
            "query": "презентация",
            "from": "2026-10-24T00:00:00+03:00",
            "to": "2026-10-24T23:59:59+03:00",
        },
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["event"]["id"] == meeting["id"]


@pytest.mark.asyncio
async def test_search_limit(client):
    for index in range(3):
        await create(
            client,
            type="task",
            title=f"Договор {index}",
            due_at="2026-10-23T10:00:00+03:00",
            timezone="Europe/Moscow",
        )
    response = await client.post("/api/v1/search", json={"query": "договор", "limit": 2})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


@pytest.mark.asyncio
async def test_search_validation(client):
    empty = await client.post("/api/v1/search", json={"query": ""})
    assert empty.status_code == 422

    spaces = await client.post("/api/v1/search", json={"query": "   "})
    assert spaces.status_code == 422

    bad_type = await client.post(
        "/api/v1/search",
        json={"query": "договор", "type": "nope"},
    )
    assert bad_type.status_code == 422

    bad_period = await client.post(
        "/api/v1/search",
        json={
            "query": "договор",
            "from": "2026-10-24T00:00:00+03:00",
            "to": "2026-10-23T00:00:00+03:00",
        },
    )
    assert bad_period.status_code == 422


@pytest.mark.asyncio
async def test_search_is_isolated_by_user(client):
    await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Секретный договор Алисы",
            "due_at": "2026-10-23T10:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
        headers={"X-Demo-User": "alice"},
    )
    response = await client.post(
        "/api/v1/search",
        json={"query": "договор"},
        headers={"X-Demo-User": "bob"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
