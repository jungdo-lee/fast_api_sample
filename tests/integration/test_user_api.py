import pytest
from httpx import AsyncClient

DEVICE_HEADERS = {
    "X-Device-Id": "test-device-user",
    "X-Device-Name": "Test Device",
    "X-App-Version": "1.0.0",
    "X-OS-Type": "iOS",
    "X-OS-Version": "17.2",
}


async def _create_and_login(client: AsyncClient, email: str = "usertest@example.com"):
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "TestPass123!",
            "name": "Test User",
            "phone_number": "01012345678",
        },
        headers=DEVICE_HEADERS,
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
        headers=DEVICE_HEADERS,
    )
    data = login_resp.json()["data"]
    return data["access_token"]


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    token = await _create_and_login(client, "getme@example.com")
    response = await client.get(
        "/api/v1/users/me",
        headers={
            **DEVICE_HEADERS,
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "getme@example.com"


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient):
    token = await _create_and_login(client, "updateme@example.com")
    response = await client.patch(
        "/api/v1/users/me",
        json={"name": "Updated Name"},
        headers={
            **DEVICE_HEADERS,
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get(
        "/api/v1/users/me",
        headers=DEVICE_HEADERS,
    )
    assert response.status_code in (401, 403)
