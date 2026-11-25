import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from database.connection import get_tenant_db
from database.models import TimetableEntry, SchoolClass, Subject, Teacher, Room, TimetableJob
from schemas.schemas import GenerateTimetableRequest, TimetableItemResponse
from services.timetable_service import TimetableService
from core.rbac import CurrentUser, require_school_admin, require_any_authenticated
from utils.crud_factory import paginate_response

router = APIRouter(prefix="/timetable", tags=["Dars Jadvali Generator & API"])

@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_timetable(
    req: GenerateTimetableRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    """
    Tanlangan chorak (term) bo'yicha asinxron dars jadvali generatsiya vazifasini yaratadi.
    Bir maktab uchun bir vaqtda faqat bitta faol vazifa bo'lishiga ruxsat beriladi.
    """
    if not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foydalanuvchiga maktab biriktirilmagan."
        )

    active_res = await db.execute(
        select(TimetableJob)
        .where(
            TimetableJob.school_id == current_user.school_id,
            TimetableJob.status.in_(["pending", "running"]),
        )
        .limit(1)
    )
    existing_job = active_res.scalar_one_or_none()
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ushbu maktab uchun jadval generatsiyasi allaqachon jarayonda."
        )

    job = TimetableJob(
        school_id=current_user.school_id,
        term=req.term,
        status="pending",
        progress=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    if os.getenv("PROCESS_JOBS_EXTERNALLY", "false").lower() != "true":
        asyncio.create_task(
            TimetableService.execute_job_in_background(
                job_id=job.id,
                school_id=current_user.school_id,
                term=req.term,
                slots_per_day=req.slots_per_day,
                save_partial=req.save_partial,
            )
        )

    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "term": job.term,
        "message": "Dars jadvali generatsiyasi navbatga qo'yildi.",
    }


@router.get("/jobs/{job_id}")
async def get_timetable_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Dars jadvali generatsiya vazifasining holati, progressi va natijasini qaytaradi (RLS bilan himoyalangan).
    """
    job = await db.get(TimetableJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generatsiya vazifasi topilmadi."
        )

    return {
        "id": job.id,
        "school_id": job.school_id,
        "term": job.term,
        "status": job.status,
        "progress": job.progress,
        "result": job.result_json,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }

@router.get("/all")
async def get_all_timetables(
    term: Optional[int] = 1,
    class_id: Optional[str] = None,
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    per_page: int = Query(3000, ge=1, le=10000, description="Har sahifadagi darslar soni"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Maktabdagi barcha sinflarning dars jadvalini olish (cheksiz / to'liq).
    """
    stmt = (
        select(
            TimetableEntry,
            SchoolClass.name.label("class_name"),
            Subject.name.label("subject_name"),
            Subject.short_code.label("subject_code"),
            Subject.color_hex.label("color_hex"),
            Teacher.full_name.label("teacher_name"),
            Room.room_number.label("room_number")
        )
        .join(SchoolClass, TimetableEntry.class_id == SchoolClass.id)
        .join(Subject, TimetableEntry.subject_id == Subject.id)
        .outerjoin(Teacher, TimetableEntry.teacher_id == Teacher.id)
        .outerjoin(Room, TimetableEntry.room_id == Room.id)
        .where(
            TimetableEntry.school_id == current_user.school_id,
            TimetableEntry.term == term
        )
    )

    if class_id:
        stmt = stmt.where(
            or_(
                TimetableEntry.class_id == class_id,
                SchoolClass.name == class_id
            )
        )

    count_query = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(SchoolClass.name, TimetableEntry.day, TimetableEntry.lesson_order).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        {
            "id": row.TimetableEntry.id,
            "term": row.TimetableEntry.term,
            "day": row.TimetableEntry.day,
            "lesson_order": row.TimetableEntry.lesson_order,
            "class_id": row.TimetableEntry.class_id,
            "class_name": row.class_name,
            "subject_id": row.TimetableEntry.subject_id,
            "subject_name": row.subject_name,
            "subject_code": row.subject_code,
            "color_hex": row.color_hex,
            "teacher_id": row.TimetableEntry.teacher_id,
            "teacher_name": row.teacher_name or "Biriktirilmagan",
            "room_id": row.TimetableEntry.room_id,
            "room_number": row.room_number or (f"{row.class_name} xona" if row.class_name else "Sinf xonasi"),
        }
        for row in rows
    ]

    return paginate_response(items, total, page, per_page)

@router.get("/by-class/{class_id}")
async def get_timetable_by_class(
    class_id: str,
    term: int = 1,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Berilgan sinf (ID yoki Nomi) va chorak bo'yicha haftalik dars jadvalini olish.
    """
    stmt = (
        select(
            TimetableEntry,
            SchoolClass.name.label("class_name"),
            Subject.name.label("subject_name"),
            Subject.short_code.label("subject_code"),
            Subject.color_hex.label("color_hex"),
            Teacher.full_name.label("teacher_name"),
            Room.room_number.label("room_number")
        )
        .join(SchoolClass, TimetableEntry.class_id == SchoolClass.id)
        .join(Subject, TimetableEntry.subject_id == Subject.id)
        .outerjoin(Teacher, TimetableEntry.teacher_id == Teacher.id)
        .outerjoin(Room, TimetableEntry.room_id == Room.id)
        .where(
            TimetableEntry.school_id == current_user.school_id,
            or_(
                TimetableEntry.class_id == class_id,
                SchoolClass.name == class_id
            ),
            TimetableEntry.term == term
        )
        .order_by(TimetableEntry.day, TimetableEntry.lesson_order)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": row.TimetableEntry.id,
            "term": row.TimetableEntry.term,
            "day": row.TimetableEntry.day,
            "lesson_order": row.TimetableEntry.lesson_order,
            "class_id": row.TimetableEntry.class_id,
            "class_name": row.class_name,
            "subject_id": row.TimetableEntry.subject_id,
            "subject_name": row.subject_name,
            "subject_code": row.subject_code,
            "color_hex": row.color_hex,
            "teacher_id": row.TimetableEntry.teacher_id,
            "teacher_name": row.teacher_name or "Biriktirilmagan",
            "room_id": row.TimetableEntry.room_id,
            "room_number": row.room_number or (f"{row.class_name} xona" if row.class_name else "Sinf xonasi"),
        }
        for row in rows
    ]
