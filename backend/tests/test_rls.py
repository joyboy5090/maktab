import os
import subprocess
import urllib.parse
from datetime import time
import pytest
import asyncpg
from sqlalchemy import select, update, text
from sqlalchemy.exc import ProgrammingError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import database.connection as db_conn
from core.config import get_async_db_url
from core.rbac import CurrentUser
from database.models import School, Teacher, Room, SchoolClass, Subject, TimeSlot, TimetableEntry


def _get_db_urls():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    raw = os.getenv("DATABASE_URL", "")
    parsed = urllib.parse.urlsplit(raw)
    admin_url = urllib.parse.urlunsplit(("postgresql", parsed.netloc, "/neondb", parsed.query, ""))
    owner_async_url = get_async_db_url(urllib.parse.urlunsplit(("postgresql+asyncpg", parsed.netloc, "/maktab_rls_test", parsed.query, "")))
    # Non-owner maktab_app role (NOBYPASSRLS)
    host_port = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
    app_netloc = f"maktab_app:maktab_app_secret@{host_port}"
    app_async_url = get_async_db_url(urllib.parse.urlunsplit(("postgresql+asyncpg", app_netloc, "/maktab_rls_test", parsed.query, "")))
    return admin_url, owner_async_url, app_async_url


@pytest.mark.asyncio
async def test_rls_tenant_isolation_with_real_postgres(monkeypatch):
    admin_url, owner_async_url, app_async_url = _get_db_urls()

    # 1. Create clean DB and run Alembic migrations (including RLS + maktab_app role)
    conn = await asyncpg.connect(admin_url)
    try:
        await conn.execute("DROP DATABASE IF EXISTS maktab_rls_test")
        await conn.execute("CREATE DATABASE maktab_rls_test")
    finally:
        await conn.close()

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = owner_async_url
    env["DATABASE_URL"] = app_async_url

    up_res = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert up_res.returncode == 0, f"alembic upgrade head failed: {up_res.stderr}"

    owner_engine = create_async_engine(owner_async_url)
    app_engine = create_async_engine(app_async_url)
    OwnerSession = async_sessionmaker(bind=owner_engine, class_=AsyncSession, expire_on_commit=False)
    AppSession = async_sessionmaker(bind=app_engine, class_=AsyncSession, expire_on_commit=False)

    # Patch connection.AsyncSessionLocal so get_tenant_db uses non-owner maktab_app role
    monkeypatch.setattr(db_conn, "AsyncSessionLocal", AppSession)

    try:
        # 2. Seed School A + Teacher A, School B + Teacher B (as owner / super admin)
        async with OwnerSession() as s:
            await s.execute(text("SELECT set_config('app.is_super_admin', 'on', true)"))
            school_a = School(name="Maktab A", slug="maktab-a-rls", email="a@maktab.uz")
            school_b = School(name="Maktab B", slug="maktab-b-rls", email="b@maktab.uz")
            s.add_all([school_a, school_b])
            await s.flush()

            teacher_a = Teacher(school_id=school_a.id, full_name="Teacher A", primary_subject="Matematika")
            teacher_b = Teacher(school_id=school_b.id, full_name="Teacher B", primary_subject="Fizika")
            s.add_all([teacher_a, teacher_b])
            await s.commit()
            school_a_id, school_b_id = school_a.id, school_b.id
            teacher_a_id, teacher_b_id = teacher_a.id, teacher_b.id

        user_a = CurrentUser(id="user-a", email="a@maktab.uz", role="SCHOOL_ADMIN", school_id=school_a_id)
        super_admin = CurrentUser(id="sa-1", email="sa@maktab.uz", role="SUPER_ADMIN", school_id=None)

        # 3. Verify School A user cannot see or modify School B rows, even without WHERE school_id
        gen_a = db_conn.get_tenant_db(current_user=user_a)
        db_a = await gen_a.__anext__()
        try:
            # Query WITHOUT any WHERE school_id filter
            all_teachers = (await db_a.execute(select(Teacher))).scalars().all()
            assert [t.id for t in all_teachers] == [teacher_a_id]

            # Direct lookup of School B teacher returns None
            b_row = (await db_a.execute(select(Teacher).where(Teacher.id == teacher_b_id))).scalar_one_or_none()
            assert b_row is None

            # Update targeting School B teacher affects 0 rows
            upd_res = await db_a.execute(
                update(Teacher).where(Teacher.id == teacher_b_id).values(full_name="Hacked B")
            )
            assert upd_res.rowcount == 0

            # 4. Commit in the middle of request, then query again (after_begin must re-apply RLS)
            await db_a.commit()

            after_commit_teachers = (await db_a.execute(select(Teacher))).scalars().all()
            assert [t.id for t in after_commit_teachers] == [teacher_a_id]

            # Inserting into School B as School A must fail WITH CHECK policy
            db_a.add(Teacher(school_id=school_b_id, full_name="Injected B", primary_subject="Kimyo"))
            with pytest.raises(ProgrammingError):
                await db_a.flush()
            await db_a.rollback()
        finally:
            await gen_a.aclose()

        # 5. Verify SUPER_ADMIN sees both schools
        gen_sa = db_conn.get_tenant_db(current_user=super_admin)
        db_sa = await gen_sa.__anext__()
        try:
            sa_teachers = (await db_sa.execute(select(Teacher))).scalars().all()
            assert {t.id for t in sa_teachers} == {teacher_a_id, teacher_b_id}
        finally:
            await gen_sa.aclose()

        # 6. Verify double-booking IntegrityError (teacher & room) and TIME column type
        gen_db = db_conn.get_tenant_db(current_user=user_a)
        db_t = await gen_db.__anext__()
        try:
            room_a1 = Room(school_id=school_a_id, room_number="101", capacity=30, room_type="GENERAL")
            room_a2 = Room(school_id=school_a_id, room_number="102", capacity=30, room_type="GENERAL")
            cls_a1 = SchoolClass(school_id=school_a_id, name="5-A", grade_level=5, student_count=25, shift="MORNING")
            cls_a2 = SchoolClass(school_id=school_a_id, name="5-B", grade_level=5, student_count=25, shift="MORNING")
            subj_a = Subject(school_id=school_a_id, name="Matematika", short_code="MAT", required_room_type="GENERAL")
            teacher_a2 = Teacher(school_id=school_a_id, full_name="Teacher A2", primary_subject="Fizika")
            ts_a = TimeSlot(
                school_id=school_a_id,
                lesson_order=1,
                shift="MORNING",
                start_time=time(8, 0),
                end_time=time(8, 45),
            )
            db_t.add_all([room_a1, room_a2, cls_a1, cls_a2, subj_a, teacher_a2, ts_a])
            await db_t.flush()
            assert isinstance(ts_a.start_time, time)
            cls_a1_id, cls_a2_id = cls_a1.id, cls_a2.id
            subj_a_id = subj_a.id
            teacher_a2_id = teacher_a2.id
            room_a1_id, room_a2_id = room_a1.id, room_a2.id

            base_entry = TimetableEntry(
                school_id=school_a_id,
                term=1,
                day="Dushanba",
                lesson_order=1,
                class_id=cls_a1_id,
                subject_id=subj_a_id,
                teacher_id=teacher_a_id,
                room_id=room_a1_id,
            )
            db_t.add(base_entry)
            await db_t.commit()

            # Overlapping teacher in same slot must raise IntegrityError
            db_t.add(
                TimetableEntry(
                    school_id=school_a_id,
                    term=1,
                    day="Dushanba",
                    lesson_order=1,
                    class_id=cls_a2_id,
                    subject_id=subj_a_id,
                    teacher_id=teacher_a_id,
                    room_id=room_a2_id,
                )
            )
            with pytest.raises(IntegrityError):
                await db_t.flush()
            await db_t.rollback()

            # Overlapping room in same slot must raise IntegrityError
            db_t.add(
                TimetableEntry(
                    school_id=school_a_id,
                    term=1,
                    day="Dushanba",
                    lesson_order=1,
                    class_id=cls_a2_id,
                    subject_id=subj_a_id,
                    teacher_id=teacher_a2_id,
                    room_id=room_a1_id,
                )
            )
            with pytest.raises(IntegrityError):
                await db_t.flush()
            await db_t.rollback()
        finally:
            await gen_db.aclose()

    finally:
        await owner_engine.dispose()
        await app_engine.dispose()

        # Verify downgrade base works cleanly on RLS migration too
        down_res = subprocess.run(
            ["python", "-m", "alembic", "downgrade", "base"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert down_res.returncode == 0, f"alembic downgrade base failed: {down_res.stderr}"

        conn = await asyncpg.connect(admin_url)
        try:
            await conn.execute("DROP DATABASE IF EXISTS maktab_rls_test")
        finally:
            await conn.close()
