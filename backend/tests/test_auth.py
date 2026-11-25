import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import jwt
from httpx import AsyncClient
from pydantic import ValidationError
from schemas.schemas import LoginRequest, UserCreate
from core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from core.config import settings
from core.limiter import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()

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
    assert "refresh_token" not in data
    assert data["role"] == "SCHOOL_ADMIN"
    assert "refresh_token" in login_res.cookies
    set_cookie_hdr = login_res.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie_hdr
    assert "samesite=lax" in set_cookie_hdr

    # Test refresh token via HttpOnly cookie
    refresh_res = await async_client.post("/auth/refresh")
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    assert "access_token" in refresh_data
    assert "refresh_token" not in refresh_data
    assert "refresh_token" in refresh_res.cookies

    # Test /auth/me with new token
    me_res = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refresh_data['access_token']}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@maktab142.uz"


def test_access_token_expiry_within_15_to_30_minutes():
    assert 15 <= settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 30


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_detection(async_client: AsyncClient):
    # 1. Login to get initial refresh cookie (token_1)
    async_client.cookies.clear()
    login_res = await async_client.post("/auth/login", json={
        "email": "admin@maktab142.uz",
        "password": "Admin123!"
    })
    assert login_res.status_code == 200
    token_1 = login_res.cookies.get("refresh_token")
    assert token_1

    # 2. Rotate: refresh with token_1 -> gets token_2
    async_client.cookies.set("refresh_token", token_1)
    rot_res = await async_client.post("/auth/refresh")
    assert rot_res.status_code == 200
    token_2 = rot_res.cookies.get("refresh_token")
    assert token_2
    assert token_2 != token_1

    # 3. Reuse detection: replay revoked token_1 -> 401 and revokes token_2 too
    async_client.cookies.set("refresh_token", token_1)
    reuse_res = await async_client.post("/auth/refresh")
    assert reuse_res.status_code == 401

    # 4. token_2 must now also be revoked!
    async_client.cookies.set("refresh_token", token_2)
    after_reuse_res = await async_client.post("/auth/refresh")
    assert after_reuse_res.status_code == 401
    async_client.cookies.clear()


@pytest.mark.asyncio
async def test_logout_revokes_token_and_clears_cookie(async_client: AsyncClient):
    async_client.cookies.clear()
    login_res = await async_client.post("/auth/login", json={
        "email": "admin@maktab142.uz",
        "password": "Admin123!"
    })
    assert login_res.status_code == 200
    token_1 = login_res.cookies.get("refresh_token")
    assert token_1

    logout_res = await async_client.post("/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Old token must no longer work after logout
    async_client.cookies.set("refresh_token", token_1)
    refresh_after_logout = await async_client.post("/auth/refresh")
    assert refresh_after_logout.status_code == 401
    async_client.cookies.clear()


@pytest.mark.asyncio
async def test_expired_refresh_token_rejected(async_client: AsyncClient):
    from datetime import timedelta
    expired_token = create_refresh_token(
        subject="expired-user",
        school_id="94561d8a-2ca8-4bb2-9b94-e67a53fc472c",
        role="SCHOOL_ADMIN",
        email="admin@maktab142.uz",
        expires_delta=timedelta(seconds=-10),
    )
    async_client.cookies.set("refresh_token", expired_token)
    res = await async_client.post("/auth/refresh")
    assert res.status_code == 401
    async_client.cookies.clear()

@pytest.mark.asyncio
async def test_invalid_login(async_client: AsyncClient):
    res = await async_client.post("/auth/login", json={
        "email": "admin@maktab142.uz",
        "password": "WrongPassword99!"
    })
    assert res.status_code == 401


def test_access_token_has_type_access():
    token = create_access_token(
        subject="user-1",
        school_id="94561d8a-2ca8-4bb2-9b94-e67a53fc472c",
        role="SCHOOL_ADMIN",
        email="admin@maktab142.uz"
    )
    payload = decode_token(token)
    assert payload.get("type") == "access"


@pytest.mark.asyncio
async def test_refresh_token_rejected_on_me(async_client: AsyncClient):
    refresh_token = create_refresh_token(
        subject="user-1",
        school_id="94561d8a-2ca8-4bb2-9b94-e67a53fc472c",
        role="SCHOOL_ADMIN",
        email="admin@maktab142.uz"
    )
    res = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_token_without_type_rejected_on_me(async_client: AsyncClient):
    legacy_token = jwt.encode(
        {
            "sub": "user-1",
            "email": "admin@maktab142.uz",
            "school_id": "94561d8a-2ca8-4bb2-9b94-e67a53fc472c",
            "role": "SCHOOL_ADMIN",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    res = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {legacy_token}"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_teacher_put_school_forbidden_and_get_allowed(async_client: AsyncClient):
    teacher_token = create_access_token(
        subject="teacher-1",
        school_id="94561d8a-2ca8-4bb2-9b94-e67a53fc472c",
        role="TEACHER",
        email="teacher@maktab142.uz"
    )
    headers = {"Authorization": f"Bearer {teacher_token}"}

    put_res = await async_client.put(
        "/auth/school",
        headers=headers,
        json={"name": "Yangi Nomi"}
    )
    assert put_res.status_code == 403

    get_res = await async_client.get("/auth/school", headers=headers)
    assert get_res.status_code == 200


@pytest.mark.asyncio
async def test_login_unknown_user_still_verifies_password(async_client: AsyncClient):
    with patch("routers.auth.verify_password", return_value=False) as mock_verify:
        res = await async_client.post("/auth/login", json={
            "email": "nonexistent_timing_test@maktab142.uz",
            "password": "SomePassword123!"
        })
        assert res.status_code == 401
        assert mock_verify.call_count == 1


@pytest.mark.asyncio
async def test_init_db_requires_admin_env_and_echo_false(monkeypatch):
    import init_db

    assert init_db.engine.echo is False

    monkeypatch.delenv("DEFAULT_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)

    mock_conn = AsyncMock()
    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin.__aexit__ = AsyncMock(return_value=False)

    mock_school = MagicMock()
    mock_school.id = "school-1"
    mock_school.name = "Test School"
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_school

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_res)
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    with patch.object(init_db, "engine", mock_engine), \
         patch.object(init_db, "AsyncSessionLocal", return_value=mock_session_ctx):
        with pytest.raises(RuntimeError, match="DEFAULT_ADMIN_EMAIL"):
            await init_db.init()


def test_password_72_and_80_bytes_validation_and_hash():
    pw_72 = "A1" + "a" * 70
    assert len(pw_72.encode("utf-8")) == 72

    user_req = UserCreate(
        email="user72@maktab.uz",
        password=pw_72,
        first_name="Test",
        last_name="User",
    )
    login_req = LoginRequest(email="user72@maktab.uz", password=pw_72)
    assert user_req.password == pw_72
    assert login_req.password == pw_72

    hashed_72 = get_password_hash(pw_72)
    assert verify_password(pw_72, hashed_72) is True

    # 80 baytli ASCII parol schemas.py da rad etiladi
    pw_80 = "A1" + "a" * 78
    assert len(pw_80.encode("utf-8")) == 80
    with pytest.raises(ValidationError):
        UserCreate(
            email="user80@maktab.uz",
            password=pw_80,
            first_name="Test",
            last_name="User",
        )
    with pytest.raises(ValidationError):
        LoginRequest(email="user80@maktab.uz", password=pw_80)

    # Ko'p baytli UTF-8 parol (belgi soni <= 72, lekin bayt > 72) ham rad etiladi
    pw_utf8_over = "A1" + "Б" * 36  # 2 + 72 = 74 bayt
    assert len(pw_utf8_over) == 38
    assert len(pw_utf8_over.encode("utf-8")) == 74
    with pytest.raises(ValidationError):
        UserCreate(
            email="utf8@maktab.uz",
            password=pw_utf8_over,
            first_name="Test",
            last_name="User",
        )

    # security.py darajasida 80 baytli parol 72 baytga kesilib mos keladi
    hashed_80 = get_password_hash(pw_80)
    assert verify_password(pw_80, hashed_80) is True


@pytest.mark.asyncio
async def test_login_with_72_and_80_byte_passwords(async_client: AsyncClient):
    from main import app
    from database.connection import get_db_session

    pw_72 = "A1" + "x" * 70
    pw_80 = "A1" + "x" * 78

    mock_user = MagicMock()
    mock_user.id = "u-72"
    mock_user.email = "u72@maktab.uz"
    mock_user.role = "TEACHER"
    mock_user.school_id = "94561d8a-2ca8-4bb2-9b94-e67a53fc472c"
    mock_user.is_active = True
    mock_user.password_hash = get_password_hash(pw_72)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db_session] = override_db
    try:
        res_72 = await async_client.post("/auth/login", json={
            "email": "u72@maktab.uz",
            "password": pw_72,
        })
        assert res_72.status_code == 200
        assert "access_token" in res_72.json()
    finally:
        app.dependency_overrides.pop(get_db_session, None)
