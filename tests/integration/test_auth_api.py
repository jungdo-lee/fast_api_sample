import pytest
from httpx import AsyncClient

DEVICE_HEADERS = {
    "X-Device-Id": "test-device-001",
    "X-Device-Name": "Test Device",
    "X-App-Version": "1.0.0",
    "X-OS-Type": "iOS",
    "X-OS-Version": "17.2",
}


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "test@example.com",
            "password": "TestPass123!",
            "name": "Test User",
            "phone_number": "01012345678",
            "marketing_agreed": True,
        },
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "test@example.com"
    assert data["data"]["name"] == "Test User"


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "dup@example.com",
            "password": "TestPass123!",
            "name": "User One",
        },
        headers=DEVICE_HEADERS,
    )

    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "dup@example.com",
            "password": "TestPass123!",
            "name": "User Two",
        },
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signup_invalid_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "weak@example.com",
            "password": "short",
            "name": "Test",
        },
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "login@example.com",
            "password": "TestPass123!",
            "name": "Login User",
        },
        headers=DEVICE_HEADERS,
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPass123!",
        },
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123!",
        },
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
