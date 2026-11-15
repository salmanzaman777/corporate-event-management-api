"""Unit tests for registration endpoints and business-rule enforcement."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token

EVENT_PAYLOAD = {
    "title": "Team Building Day",
    "description": "Outdoor team activities",
    "event_date": "2026-12-15T09:00:00Z",
    "location": "City Park",
    "max_capacity": 2,
}


async def _create_event(client: AsyncClient, token: str, capacity: int = 2) -> dict:
    resp = await client.post(
        "/events",
        json={**EVENT_PAYLOAD, "max_capacity": capacity},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _register_user(client: AsyncClient, event_id: int, user_id: int, token: str) -> dict:
    resp = await client.post(
        f"/events/{event_id}/registrations",
        json={"user_id": user_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    token = await get_auth_token(client, "user_a")
    # get user_a's id
    login_resp = await client.post("/auth/login", json={"username": "user_a", "password": "TestPass123"})
    # create event
    event = await _create_event(client, token)
    # register user_a (id=1 since first user)
    user_resp = await client.post("/auth/register", json={"username": "user_b", "email": "b@test.com", "password": "TestPass123"})
    user_b_id = user_resp.json()["id"]

    resp = await _register_user(client, event["id"], user_b_id, token)
    assert resp.status_code == 201
    body = resp.json()
    assert body["event_id"] == event["id"]
    assert body["user_id"] == user_b_id


@pytest.mark.asyncio
async def test_register_duplicate_rejected(client: AsyncClient):
    token = await get_auth_token(client, "user_c")
    event = await _create_event(client, token, capacity=10)
    user_resp = await client.post("/auth/register", json={"username": "user_d", "email": "d@test.com", "password": "TestPass123"})
    uid = user_resp.json()["id"]

    await _register_user(client, event["id"], uid, token)
    resp = await _register_user(client, event["id"], uid, token)
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_capacity_limit_enforced(client: AsyncClient):
    token = await get_auth_token(client, "organizer")
    event = await _create_event(client, token, capacity=1)

    # Create two more users
    u1 = (await client.post("/auth/register", json={"username": "u1", "email": "u1@t.com", "password": "TestPass123"})).json()["id"]
    u2 = (await client.post("/auth/register", json={"username": "u2", "email": "u2@t.com", "password": "TestPass123"})).json()["id"]

    r1 = await _register_user(client, event["id"], u1, token)
    assert r1.status_code == 201

    r2 = await _register_user(client, event["id"], u2, token)
    assert r2.status_code == 409
    assert "capacity" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_register_nonexistent_event(client: AsyncClient):
    token = await get_auth_token(client, "user_e")
    resp = await _register_user(client, 9999, 1, token)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_register_nonexistent_user(client: AsyncClient):
    token = await get_auth_token(client, "user_f")
    event = await _create_event(client, token)
    resp = await _register_user(client, event["id"], 9999, token)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_registrations(client: AsyncClient):
    token = await get_auth_token(client, "user_g")
    event = await _create_event(client, token, capacity=10)
    u = (await client.post("/auth/register", json={"username": "attendee", "email": "att@t.com", "password": "TestPass123"})).json()["id"]
    await _register_user(client, event["id"], u, token)

    resp = await client.get(f"/events/{event['id']}/registrations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_registrations_nonexistent_event(client: AsyncClient):
    resp = await client.get("/events/9999/registrations")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_registration(client: AsyncClient):
    token = await get_auth_token(client, "user_h")
    event = await _create_event(client, token, capacity=10)
    u = (await client.post("/auth/register", json={"username": "reg_user", "email": "reg@t.com", "password": "TestPass123"})).json()["id"]
    reg = (await _register_user(client, event["id"], u, token)).json()

    resp = await client.delete(f"/registrations/{reg['id']}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # Verify cancelled
    regs = (await client.get(f"/events/{event['id']}/registrations")).json()
    assert all(r["id"] != reg["id"] for r in regs)


@pytest.mark.asyncio
async def test_cancel_registration_not_found(client: AsyncClient):
    token = await get_auth_token(client, "user_i")
    resp = await client.delete("/registrations/9999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_register_requires_auth(client: AsyncClient):
    token = await get_auth_token(client, "user_j")
    event = await _create_event(client, token)
    resp = await client.post(f"/events/{event['id']}/registrations", json={"user_id": 1})
    assert resp.status_code == 401
