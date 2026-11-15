"""Unit tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@acme.com",
        "password": "Password1!",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "password" not in body


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    payload = {"username": "bob", "email": "bob@acme.com", "password": "Password1!"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_username_characters(client: AsyncClient):
    payload = {"username": "bad user!", "email": "bad@acme.com", "password": "Password1!"}
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    payload = {"username": "shortpass", "email": "short@acme.com", "password": "123"}
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={
        "username": "carol",
        "email": "carol@acme.com",
        "password": "Password1!",
    })
    resp = await client.post("/auth/login", json={"username": "carol", "password": "Password1!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "username": "dave",
        "email": "dave@acme.com",
        "password": "Password1!",
    })
    resp = await client.post("/auth/login", json={"username": "dave", "password": "wrong"})
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers
