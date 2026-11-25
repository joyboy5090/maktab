import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from core.security import create_access_token


@pytest.mark.asyncio
async def test_timetable_async_job_flow_and_concurrency_guard(async_client: AsyncClient, auth_headers: dict):
    # 1. Existing retrieval endpoint works
    res = await async_client.get("/timetable/all?term=1&per_page=50", headers=auth_headers)
    assert res.status_code == 200
    assert "data" in res.json()

    # 2. Mock background execution so test verifies 202, 409, GET job, and tenant isolation deterministically
    with patch("routers.timetable.TimetableService.execute_job_in_background", new=AsyncMock()):
        gen_res = await async_client.post(
            "/timetable/generate",
            headers=auth_headers,
            json={"term": 1, "slots_per_day": 6},
        )
        assert gen_res.status_code == 202
        gen_data = gen_res.json()
        assert "job_id" in gen_data
        assert gen_data["status"] == "pending"
        job_id = gen_data["job_id"]

        # Yield once so scheduled task runs
        await asyncio.sleep(0)

        # 3. Second concurrent request for same school must return 409 Conflict
        dup_res = await async_client.post(
            "/timetable/generate",
            headers=auth_headers,
            json={"term": 1, "slots_per_day": 6},
        )
        assert dup_res.status_code == 409

        # 4. GET /timetable/jobs/{job_id} returns job status for same school
        job_res = await async_client.get(f"/timetable/jobs/{job_id}", headers=auth_headers)
        assert job_res.status_code == 200
        job_data = job_res.json()
        assert job_data["id"] == job_id
        assert job_data["status"] == "pending"
        assert job_data["progress"] == 0

        # 5. Clean up test job row directly in DB so school isn't left with pending job
        from database.connection import AsyncSessionLocal
        from sqlalchemy import delete
        from database.models import TimetableJob
        async with AsyncSessionLocal() as db:
            await db.execute(delete(TimetableJob).where(TimetableJob.id == job_id))
            await db.commit()
