from uuid import uuid4

import pytest


def _email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4().hex[:12]}@example.com"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_login_and_me(client) -> None:
    email = _email()
    password = "correct-horse-battery"

    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "  Иван  ",
            "timezone": "Europe/Moscow",
        },
    )
    assert registered.status_code == 201
    payload = registered.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == email
    assert payload["user"]["display_name"] == "Иван"
    assert payload["user"]["timezone"] == "Europe/Moscow"

    me = await client.get("/api/v1/auth/me", headers=_auth(payload["access_token"]))
    assert me.status_code == 200
    assert me.json()["id"] == payload["user"]["id"]

    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": email.upper(), "password": password},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["id"] == payload["user"]["id"]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client) -> None:
    email = _email("duplicate")
    body = {"email": email, "password": "password-123"}

    first = await client.post("/api/v1/auth/register", json=body)
    second = await client.post("/api/v1/auth/register", json=body)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client) -> None:
    email = _email("wrong")
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password-123"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password-456"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_me_requires_valid_bearer(client) -> None:
    missing = await client.get("/api/v1/auth/me")
    invalid = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer definitely-not-a-token"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401


@pytest.mark.asyncio
async def test_web_accounts_are_isolated(client) -> None:
    first = await client.post(
        "/api/v1/auth/register",
        json={"email": _email("alice"), "password": "password-123"},
    )
    second = await client.post(
        "/api/v1/auth/register",
        json={"email": _email("bob"), "password": "password-123"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    first_token = first.json()["access_token"]
    second_token = second.json()["access_token"]

    created = await client.post(
        "/api/v1/events",
        json={
            "type": "task",
            "title": "Секрет Алисы",
            "due_at": "2030-01-01T10:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
        headers=_auth(first_token),
    )
    assert created.status_code == 201

    first_list = await client.get("/api/v1/events", headers=_auth(first_token))
    second_list = await client.get("/api/v1/events", headers=_auth(second_token))
    assert [item["title"] for item in first_list.json()] == ["Секрет Алисы"]
    assert second_list.json() == []

    first_search = await client.post(
        "/api/v1/search",
        json={"query": "секрет"},
        headers=_auth(first_token),
    )
    second_search = await client.post(
        "/api/v1/search",
        json={"query": "секрет"},
        headers=_auth(second_token),
    )
    assert first_search.status_code == 200
    assert second_search.status_code == 200
    assert len(first_search.json()["items"]) == 1
    assert second_search.json()["items"] == []


@pytest.mark.asyncio
async def test_demo_auth_still_works_for_local_clients(client) -> None:
    response = await client.get("/api/v1/events", headers={"X-Demo-User": "legacy-demo"})

    assert response.status_code == 200
    assert response.json() == []
