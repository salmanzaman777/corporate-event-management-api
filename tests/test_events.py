"""Unit tests for event CRUD endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token

EVENT_PAYLOAD = {
    "title": "Python Workshop",
    "description": "Intro to FastAPI",
    "event_date": "2026-12-01T14:00:00Z",
    "location": "HQ Room A",
    "max_capacity": 30,
}


@pytest.mark.asyncio
async def test_create_event_requires_auth(client: AsyncClient):
    resp = await client.post("/events", json=EVENT_PAYLOAD)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_event_success(client: AsyncClient):
    token = await get_auth_token(client)
    resp = await client.post("/events", json=EVENT_PAYLOAD, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Python Workshop"
    assert body["max_capacity"] == 30


@pytest.mark.asyncio
async def test_create_event_blank_title(client: AsyncClient):
    token = await get_auth_token(client)
    bad = {**EVENT_PAYLOAD, "title": "   "}
    resp = await client.post("/events", json=bad, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_event_zero_capacity(client: AsyncClient):
    token = await get_auth_token(client)
    bad = {**EVENT_PAYLOAD, "max_capacity": 0}
    resp = await client.post("/events", json=bad, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_events_public(client: AsyncClient):
    token = await get_auth_token(client)
    await client.post("/events", json=EVENT_PAYLOAD, headers={"Authorization": f"Bearer {token}"})
    resp = await client.get("/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


@pytest.mark.asyncio
async def test_list_events_pagination(client: AsyncClient):
    token = await get_auth_token(client)
    for i in range(5):
        await client.post(
            "/events",
            json={**EVENT_PAYLOAD, "title": f"Event {i}"},
            headers={"Authorization": f"Bearer {token}"},
        )
    resp = await client.get("/events?skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_list_events_filter_title(client: AsyncClient):
    token = await get_auth_token(client)
    await client.post("/events", json={**EVENT_PAYLOAD, "title": "Alpha Meeting"}, headers={"Authorization": f"Bearer {token}"})
    await client.post("/events", json={**EVENT_PAYLOAD, "title": "Beta Workshop"}, headers={"Authorization": f"Bearer {token}"})
    resp = await client.get("/events?title=Alpha")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all("Alpha" in item["title"] for item in items)


@pytest.mark.asyncio
async def test_get_event_by_id(client: AsyncClient):
    token = await get_auth_token(client)
    created = (await client.post("/events", json=EVENT_PAYLOAD, headers={"Authorization": f"Bearer {token}"})).json()
    resp = await client.get(f"/events/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    resp = await client.get("/events/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_event(client: AsyncClient):
    token = await get_auth_token(client)
    created = (await client.post("/events", json=EVENT_PAYLOAD, headers={"Authorization": f"Bearer {token}"})).json()
    resp = await client.put(
        f"/events/{created['id']}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_event(client: AsyncClient):
    token = await get_auth_token(client)
    created = (await client.post("/events", json=EVENT_PAYLOAD, headers={"Authorization": f"Bearer {token}"})).json()
    resp = await client.delete(f"/events/{created['id']}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204
    assert (await client.get(f"/events/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_event_not_found(client: AsyncClient):
    token = await get_auth_token(client)
    resp = await client.delete("/events/9999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
