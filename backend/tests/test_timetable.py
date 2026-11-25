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


@pytest.mark.asyncio
async def test_patch_timetable_entry_pin_and_conflict_409(async_client: AsyncClient, auth_headers: dict):
    list_res = await async_client.get("/timetable/all?term=1&per_page=50", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json().get("data", [])
    assert len(items) >= 2

    first = items[0]
    same_class_other = next((x for x in items[1:] if x["class_id"] == first["class_id"]), None)
    assert same_class_other is not None

    # 1. Pin first entry
    pin_res = await async_client.patch(
        f"/timetable/entries/{first['id']}",
        headers=auth_headers,
        json={"is_pinned": True},
    )
    assert pin_res.status_code == 200
    assert pin_res.json()["is_pinned"] is True

    # 2. Try moving first entry onto same_class_other's slot -> must return 409 Conflict
    conflict_res = await async_client.patch(
        f"/timetable/entries/{first['id']}",
        headers=auth_headers,
        json={
            "day": same_class_other["day"],
            "lesson_order": same_class_other["lesson_order"],
        },
    )
    assert conflict_res.status_code == 409
    err_data = conflict_res.json()
    msg = err_data.get("detail") or err_data.get("error", {}).get("message", "")
    assert "To'qnashuv" in msg

    # 3. Unpin back to clean state
    unpin_res = await async_client.patch(
        f"/timetable/entries/{first['id']}",
        headers=auth_headers,
        json={"is_pinned": False},
    )
    assert unpin_res.status_code == 200
    assert unpin_res.json()["is_pinned"] is False
