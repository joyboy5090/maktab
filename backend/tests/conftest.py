import pytest
import os
import sys
from typing import AsyncGenerator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from main import app
from database.connection import engine, AsyncSessionLocal
from database.models import User
from core.security import create_access_token

@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as client:
        yield client
    await engine.dispose()

@pytest.fixture(scope="session")
async def auth_headers() -> dict:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "admin@maktab142.uz"))
        admin = res.scalar_one()
        subject = admin.id
        school_id = admin.school_id
        role = admin.role
        email = admin.email

    token = create_access_token(
        subject=subject,
        school_id=school_id,
        role=role,
        email=email,
    )
    return {"Authorization": f"Bearer {token}"}
