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


@pytest.mark.asyncio
async def test_teacher_my_timetable_rbac_and_rls(async_client: AsyncClient, auth_headers: dict):
    import uuid
    from sqlalchemy import select, update, delete
    from database.connection import AsyncSessionLocal
    from database.models import Teacher, User
    from core.security import get_password_hash

    list_res = await async_client.get("/timetable/all?term=1&per_page=50", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json().get("data", [])
    teacher_ids = list({x["teacher_id"] for x in items if x.get("teacher_id")})
    assert len(teacher_ids) >= 2, "Test uchun kamida 2 ta o'qituvchi darsi kerak"

    teacher_a_id = teacher_ids[0]
    teacher_b_id = teacher_ids[1]
    school_id = "94561d8a-2ca8-4bb2-9b94-e67a53fc472c"
    other_school_id = str(uuid.uuid4())
    user_a_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        orig_user_id = (
            await db.execute(select(Teacher.user_id).where(Teacher.id == teacher_a_id))
        ).scalar_one_or_none()
        user_a = User(
            id=user_a_id,
            school_id=school_id,
            role="TEACHER",
            email=f"teacher_{user_a_id[:8]}@maktab142.uz",
            password_hash=get_password_hash("secret123"),
            first_name="Test",
            last_name="Teacher",
        )
        db.add(user_a)
        await db.flush()
        await db.execute(
            update(Teacher).where(Teacher.id == teacher_a_id).values(user_id=user_a_id)
        )
        await db.commit()

    try:
        teacher_token = create_access_token(
            subject=user_a_id,
            school_id=school_id,
            role="TEACHER",
            email=f"teacher_{user_a_id[:8]}@maktab142.uz",
        )
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

        # 1. RBAC: TEACHER cannot access /timetable/all or /timetable/by-class/{id}
        all_res = await async_client.get("/timetable/all?term=1", headers=teacher_headers)
        assert all_res.status_code == 403

        by_class_res = await async_client.get(
            f"/timetable/by-class/{items[0]['class_id']}?term=1", headers=teacher_headers
        )
        assert by_class_res.status_code == 403

        # 2. /timetable/my returns ONLY lessons assigned to teacher_a_id
        my_res = await async_client.get("/timetable/my?term=1", headers=teacher_headers)
        assert my_res.status_code == 200
        my_items = my_res.json()
        assert len(my_items) >= 1
        assert all(entry["teacher_id"] == teacher_a_id for entry in my_items)
        assert all(entry["teacher_id"] != teacher_b_id for entry in my_items)

        # 3. Unlinked TEACHER gets empty list
        unlinked_token = create_access_token(
            subject=str(uuid.uuid4()),
            school_id=school_id,
            role="TEACHER",
            email="unlinked@maktab142.uz",
        )
        unlinked_res = await async_client.get(
            "/timetable/my?term=1", headers={"Authorization": f"Bearer {unlinked_token}"}
        )
        assert unlinked_res.status_code == 200
        assert unlinked_res.json() == []

        # 4. RLS / tenant isolation: same user_a_id with another school_id sees 0 rows
        other_school_token = create_access_token(
            subject=user_a_id,
            school_id=other_school_id,
            role="TEACHER",
            email=f"teacher_{user_a_id[:8]}@other.uz",
        )
        rls_res = await async_client.get(
            "/timetable/my?term=1", headers={"Authorization": f"Bearer {other_school_token}"}
        )
        assert rls_res.status_code == 200
        assert rls_res.json() == []
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Teacher).where(Teacher.id == teacher_a_id).values(user_id=orig_user_id)
            )
            await db.execute(delete(User).where(User.id == user_a_id))
            await db.commit()
