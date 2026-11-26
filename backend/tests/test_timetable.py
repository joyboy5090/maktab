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
async def test_patch_timetable_entry_pin_and_conflict_409(async_client: AsyncClient, seeded_school_and_admin: dict):
    import uuid
    from sqlalchemy import delete
    from database.connection import SuperAsyncSessionLocal
    from database.models import SchoolClass, Subject, Teacher, Room, TimetableEntry

    school_id = seeded_school_and_admin["school_id"]
    headers = seeded_school_and_admin["headers"]
    cls_id = str(uuid.uuid4())
    subj_id = str(uuid.uuid4())
    tch_id = str(uuid.uuid4())
    room_id = str(uuid.uuid4())
    e1_id = str(uuid.uuid4())
    e2_id = str(uuid.uuid4())

    async with SuperAsyncSessionLocal() as db:
        db.add_all([
            SchoolClass(id=cls_id, school_id=school_id, name=f"5-T-{cls_id[:4]}", grade_level=5, student_count=25, shift="MORNING"),
            Subject(id=subj_id, school_id=school_id, name="Matematika", short_code=f"M{subj_id[:4]}", required_room_type="GENERAL"),
            Teacher(id=tch_id, school_id=school_id, full_name="Patch Teacher", primary_subject="Matematika"),
            Room(id=room_id, school_id=school_id, room_number=f"R-{room_id[:4]}", capacity=30, room_type="GENERAL"),
        ])
        await db.flush()
        db.add_all([
            TimetableEntry(id=e1_id, school_id=school_id, term=1, day="Dushanba", lesson_order=1, class_id=cls_id, subject_id=subj_id, teacher_id=tch_id, room_id=room_id),
            TimetableEntry(id=e2_id, school_id=school_id, term=1, day="Dushanba", lesson_order=2, class_id=cls_id, subject_id=subj_id, teacher_id=tch_id, room_id=room_id),
        ])
        await db.commit()

    try:
        # 1. Pin first entry
        pin_res = await async_client.patch(
            f"/timetable/entries/{e1_id}",
            headers=headers,
            json={"is_pinned": True},
        )
        assert pin_res.status_code == 200
        assert pin_res.json()["is_pinned"] is True

        # 2. Try moving first entry onto e2's slot -> must return 409 Conflict
        conflict_res = await async_client.patch(
            f"/timetable/entries/{e1_id}",
            headers=headers,
            json={"day": "Dushanba", "lesson_order": 2},
        )
        assert conflict_res.status_code == 409
        err_data = conflict_res.json()
        msg = err_data.get("detail") or err_data.get("error", {}).get("message", "")
        assert "To'qnashuv" in msg

        # 3. Unpin back to clean state
        unpin_res = await async_client.patch(
            f"/timetable/entries/{e1_id}",
            headers=headers,
            json={"is_pinned": False},
        )
        assert unpin_res.status_code == 200
        assert unpin_res.json()["is_pinned"] is False
    finally:
        async with SuperAsyncSessionLocal() as db:
            await db.execute(delete(TimetableEntry).where(TimetableEntry.id.in_([e1_id, e2_id])))
            await db.execute(delete(Teacher).where(Teacher.id == tch_id))
            await db.execute(delete(Room).where(Room.id == room_id))
            await db.execute(delete(Subject).where(Subject.id == subj_id))
            await db.execute(delete(SchoolClass).where(SchoolClass.id == cls_id))
            await db.commit()


@pytest.mark.asyncio
async def test_teacher_my_timetable_rbac_and_rls(async_client: AsyncClient, seeded_school_and_admin: dict):
    import uuid
    from sqlalchemy import delete
    from database.connection import SuperAsyncSessionLocal
    from database.models import Teacher, User, SchoolClass, Subject, Room, TimetableEntry
    from core.security import get_password_hash

    school_id = seeded_school_and_admin["school_id"]
    other_school_id = str(uuid.uuid4())
    user_a_id = str(uuid.uuid4())
    teacher_a_id = str(uuid.uuid4())
    teacher_b_id = str(uuid.uuid4())
    cls_id = str(uuid.uuid4())
    subj_id = str(uuid.uuid4())
    room_id = str(uuid.uuid4())
    e_a_id = str(uuid.uuid4())
    e_b_id = str(uuid.uuid4())
    user_a_email = f"teacher_{user_a_id[:8]}@maktab-test.uz"

    async with SuperAsyncSessionLocal() as db:
        db.add(
            User(
                id=user_a_id,
                school_id=school_id,
                role="TEACHER",
                email=user_a_email,
                password_hash=get_password_hash("TeacherPass123!"),
                first_name="Test",
                last_name="Teacher",
                is_active=True,
            )
        )
        await db.flush()
        db.add_all([
            Teacher(id=teacher_a_id, school_id=school_id, user_id=user_a_id, full_name="Teacher A", primary_subject="Matematika"),
            Teacher(id=teacher_b_id, school_id=school_id, full_name="Teacher B", primary_subject="Fizika"),
            SchoolClass(id=cls_id, school_id=school_id, name=f"6-T-{cls_id[:4]}", grade_level=6, student_count=25, shift="MORNING"),
            Subject(id=subj_id, school_id=school_id, name="Fizika", short_code=f"F{subj_id[:4]}", required_room_type="GENERAL"),
            Room(id=room_id, school_id=school_id, room_number=f"R2-{room_id[:4]}", capacity=30, room_type="GENERAL"),
        ])
        await db.flush()
        db.add_all([
            TimetableEntry(id=e_a_id, school_id=school_id, term=1, day="Seshanba", lesson_order=1, class_id=cls_id, subject_id=subj_id, teacher_id=teacher_a_id, room_id=room_id),
            TimetableEntry(id=e_b_id, school_id=school_id, term=1, day="Seshanba", lesson_order=2, class_id=cls_id, subject_id=subj_id, teacher_id=teacher_b_id, room_id=room_id),
        ])
        await db.commit()

    try:
        login_res = await async_client.post(
            "/auth/login",
            json={"email": user_a_email, "password": "TeacherPass123!"},
        )
        assert login_res.status_code == 200
        teacher_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
        async_client.cookies.clear()

        # 1. RBAC: TEACHER cannot access /timetable/all or /timetable/by-class/{id}
        all_res = await async_client.get("/timetable/all?term=1", headers=teacher_headers)
        assert all_res.status_code == 403

        by_class_res = await async_client.get(
            f"/timetable/by-class/{cls_id}?term=1", headers=teacher_headers
        )
        assert by_class_res.status_code == 403

        # 2. /timetable/my returns ONLY lessons assigned to teacher_a_id
        my_res = await async_client.get("/timetable/my?term=1", headers=teacher_headers)
        assert my_res.status_code == 200
        my_items = my_res.json()
        assert len(my_items) == 1
        assert my_items[0]["teacher_id"] == teacher_a_id

        # 3. Unlinked TEACHER gets empty list
        unlinked_token = create_access_token(
            subject=str(uuid.uuid4()),
            school_id=school_id,
            role="TEACHER",
            email="unlinked@maktab-test.uz",
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
        async with SuperAsyncSessionLocal() as db:
            await db.execute(delete(TimetableEntry).where(TimetableEntry.id.in_([e_a_id, e_b_id])))
            await db.execute(delete(Teacher).where(Teacher.id.in_([teacher_a_id, teacher_b_id])))
            await db.execute(delete(Room).where(Room.id == room_id))
            await db.execute(delete(Subject).where(Subject.id == subj_id))
            await db.execute(delete(SchoolClass).where(SchoolClass.id == cls_id))
            await db.execute(delete(User).where(User.id == user_a_id))
            await db.commit()
