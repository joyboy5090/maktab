import pytest
import os
import sys
from typing import AsyncGenerator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from main import app
from database.connection import engine
from core.security import create_access_token

@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as client:
        yield client
    await engine.dispose()

@pytest.fixture(scope="session")
def auth_headers() -> dict:
    token = create_access_token(
        subject="admin@maktab142.uz",
        school_id="94561d8a-2ca8-4bb2-9b94-e67a53fc472c",
        role="SCHOOL_ADMIN",
        email="admin@maktab142.uz"
    )
    return {"Authorization": f"Bearer {token}"}
