import os
import sys
import uuid
from typing import AsyncGenerator
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete
from main import app
from database.connection import engine, super_engine, SuperAsyncSessionLocal
from database.models import School, User
from core.security import get_password_hash


@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as client:
        yield client
    await engine.dispose()
    if super_engine is not engine:
        await super_engine.dispose()


@pytest.fixture(scope="session")
async def seeded_school_and_admin(async_client: AsyncClient) -> AsyncGenerator[dict, None]:
    """Har bir test sessiyasi uchun mustaqil maktab va SCHOOL_ADMIN yaratadi va haqiqiy /auth/login orqali token oladi."""
    uid = uuid.uuid4().hex[:8]
    school_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    email = f"test_admin_{uid}@maktab-test.uz"
    password = os.getenv("TEST_ADMIN_PASSWORD", "TestAdmin123!")

    async with SuperAsyncSessionLocal() as db:
        school = School(
            id=school_id,
            name=f"Test Maktab {uid}",
            slug=f"test-maktab-{uid}",
            email=email,
            is_active=True,
        )
        admin = User(
            id=admin_id,
            school_id=school_id,
            role="SCHOOL_ADMIN",
            email=email,
            password_hash=get_password_hash(password),
            first_name="Test",
            last_name="Admin",
            is_active=True,
        )
        db.add_all([school, admin])
        await db.commit()

    login_res = await async_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, f"Test admin login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    async_client.cookies.clear()

    try:
        yield {
            "school_id": school_id,
            "admin_id": admin_id,
            "email": email,
            "password": password,
            "headers": {"Authorization": f"Bearer {token}"},
        }
    finally:
        async with SuperAsyncSessionLocal() as db:
            await db.execute(delete(User).where(User.id == admin_id))
            await db.execute(delete(School).where(School.id == school_id))
            await db.commit()


@pytest.fixture(scope="session")
def auth_headers(seeded_school_and_admin: dict) -> dict:
    return seeded_school_and_admin["headers"]
