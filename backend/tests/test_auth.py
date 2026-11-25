import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from schemas.schemas import LoginRequest, UserCreate
from core.security import create_refresh_token, decode_token

def test_password_policy_validation():
    # Valid password
    req = LoginRequest(email="test@maktab.uz", password="Password123")
    assert req.password == "Password123"

    # Too short (< 8 chars)
    with pytest.raises(ValidationError):
        LoginRequest(email="test@maktab.uz", password="Pass1")

    # No uppercase letter
    with pytest.raises(ValidationError):
        LoginRequest(email="test@maktab.uz", password="password123")

    # No digit
    with pytest.raises(ValidationError):
        LoginRequest(email="test@maktab.uz", password="PasswordOnly")

@pytest.mark.asyncio
async def test_login_and_refresh_flow(async_client: AsyncClient):
    # Test valid login with seeded admin
    login_res = await async_client.post("/auth/login", json={
        "email": "admin@maktab142.uz",
        "password": "Admin123!"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "SCHOOL_ADMIN"

    refresh_token = data["refresh_token"]

    # Test refresh token
    refresh_res = await async_client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    assert "access_token" in refresh_data

    # Test /auth/me with new token
    me_res = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refresh_data['access_token']}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@maktab142.uz"

@pytest.mark.asyncio
async def test_invalid_login(async_client: AsyncClient):
    res = await async_client.post("/auth/login", json={
        "email": "admin@maktab142.uz",
        "password": "WrongPassword99!"
    })
    assert res.status_code == 401
