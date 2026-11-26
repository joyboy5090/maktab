import os
import subprocess
import urllib.parse
import pytest
import asyncpg
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import database.connection as db_conn
from core.config import get_async_db_url
from main import app


def _get_test_db_urls():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    raw = os.getenv("DATABASE_URL", "")
    parsed = urllib.parse.urlsplit(raw)
    admin_url = urllib.parse.urlunsplit(("postgresql", parsed.netloc, "/neondb", parsed.query, ""))
    owner_async_url = get_async_db_url(
        urllib.parse.urlunsplit(("postgresql+asyncpg", parsed.netloc, "/maktab_init_test", parsed.query, ""))
    )
    host_port = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
    app_netloc = f"maktab_app:maktab_app_secret@{host_port}"
    app_async_url = get_async_db_url(
        urllib.parse.urlunsplit(("postgresql+asyncpg", app_netloc, "/maktab_init_test", parsed.query, ""))
    )
    return admin_url, owner_async_url, app_async_url


@pytest.mark.asyncio
async def test_clean_db_alembic_init_db_and_admin_login(monkeypatch):
    admin_url, owner_async_url, app_async_url = _get_test_db_urls()
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    conn = await asyncpg.connect(admin_url)
    try:
        await conn.execute("DROP DATABASE IF EXISTS maktab_init_test")
        await conn.execute("CREATE DATABASE maktab_init_test")
    finally:
        await conn.close()

    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = owner_async_url
    env["DATABASE_URL"] = app_async_url
    env["DEFAULT_ADMIN_EMAIL"] = "clean_admin@maktab.uz"
    env["DEFAULT_ADMIN_PASSWORD"] = "CleanAdmin123!"

    app_engine = create_async_engine(app_async_url)
    AppSession = async_sessionmaker(bind=app_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        up_res = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert up_res.returncode == 0, f"alembic upgrade head failed: {up_res.stderr}"

        init_res = subprocess.run(
            ["python", "init_db.py"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert init_res.returncode == 0, f"init_db.py failed: {init_res.stderr}\n{init_res.stdout}"

        # Idempotent re-run must not fail or overwrite existing admin password
        init_res_2 = subprocess.run(
            ["python", "init_db.py"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert init_res_2.returncode == 0, f"second init_db.py failed: {init_res_2.stderr}"

        # Login against the clean DB using the non-owner maktab_app role
        monkeypatch.setattr(db_conn, "AsyncSessionLocal", AppSession)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as client:
            login_res = await client.post(
                "/auth/login",
                json={"email": "clean_admin@maktab.uz", "password": "CleanAdmin123!"},
            )
            assert login_res.status_code == 200, login_res.text
            assert "access_token" in login_res.json()
    finally:
        await app_engine.dispose()
        conn = await asyncpg.connect(admin_url)
        try:
            await conn.execute("DROP DATABASE IF EXISTS maktab_init_test")
        finally:
            await conn.close()
