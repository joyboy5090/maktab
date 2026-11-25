from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, func
from database.connection import get_tenant_db
from database.models import ClassSubjectAllocation, SchoolClass, Subject, Teacher, Room
from schemas.schemas import AllocationCreate, AllocationResponse, AllocationUpdate
from core.rbac import CurrentUser, require_school_admin, require_any_authenticated
from utils.crud_factory import paginate_response

router = APIRouter(prefix="/curriculum", tags=["O'quv Rejasi (Sinf Fanlari & Choraklik Yuklama)"])

@router.get("/all")
async def get_all_allocations(
    term: Optional[int] = None,
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    per_page: int = Query(500, ge=1, le=2000, description="Har sahifadagi elementlar soni"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Maktabdagi barcha sinflarning o'quv rejasini (fanlarini) sahifalash bilan olish.
    """
    stmt = (
        select(
            ClassSubjectAllocation,
            SchoolClass.name.label("class_name"),
            Subject.name.label("subject_name"),
            Subject.short_code.label("subject_code"),
            Subject.color_hex.label("color_hex"),
            Teacher.full_name.label("teacher_name"),
            Room.room_number.label("room_number")
        )
        .join(SchoolClass, ClassSubjectAllocation.class_id == SchoolClass.id)
        .join(Subject, ClassSubjectAllocation.subject_id == Subject.id)
        .outerjoin(Teacher, ClassSubjectAllocation.teacher_id == Teacher.id)
        .outerjoin(Room, ClassSubjectAllocation.preferred_room_id == Room.id)
        .where(ClassSubjectAllocation.school_id == current_user.school_id)
    )
    if term:
        stmt = stmt.where(ClassSubjectAllocation.term == term)

    count_query = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(SchoolClass.name, Subject.name).offset((page - 1) * per_page).limit(per_page)
    res = await db.execute(stmt)
    rows = res.all()

    items = [
        {
            "id": row.ClassSubjectAllocation.id,
            "school_id": row.ClassSubjectAllocation.school_id,
            "class_id": row.ClassSubjectAllocation.class_id,
            "class_name": row.class_name,
            "subject_id": row.ClassSubjectAllocation.subject_id,
            "subject_name": row.subject_name,
            "subject_code": row.subject_code,
            "color_hex": row.color_hex,
            "teacher_id": row.ClassSubjectAllocation.teacher_id,
            "teacher_name": row.teacher_name,
            "preferred_room_id": row.ClassSubjectAllocation.preferred_room_id,
            "room_number": row.room_number,
            "term": row.ClassSubjectAllocation.term,
            "quarter_total_hours": row.ClassSubjectAllocation.quarter_total_hours,
            "weeks_in_quarter": row.ClassSubjectAllocation.weeks_in_quarter,
            "weekly_hours": row.ClassSubjectAllocation.weekly_hours,
            "max_hours_per_day": row.ClassSubjectAllocation.max_hours_per_day,
        }
        for row in rows
    ]
    return paginate_response(items, total, page, per_page)

@router.get("/by-class/{class_id}", response_model=List[AllocationResponse])
async def get_curriculum_by_class(
    class_id: str,
    term: Optional[int] = 1,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Tanlangan sinf (ID yoki nomi bo'yicha) va chorak bo'yicha o'quv rejasini olish.
    """
    stmt = (
        select(
            ClassSubjectAllocation,
            SchoolClass.name.label("class_name"),
            Subject.name.label("subject_name"),
            Subject.short_code.label("subject_code"),
            Subject.color_hex.label("color_hex"),
            Teacher.full_name.label("teacher_name"),
            Room.room_number.label("room_number")
        )
        .join(SchoolClass, ClassSubjectAllocation.class_id == SchoolClass.id)
        .join(Subject, ClassSubjectAllocation.subject_id == Subject.id)
        .outerjoin(Teacher, ClassSubjectAllocation.teacher_id == Teacher.id)
        .outerjoin(Room, ClassSubjectAllocation.preferred_room_id == Room.id)
        .where(
            ClassSubjectAllocation.school_id == current_user.school_id,
            or_(
                ClassSubjectAllocation.class_id == class_id,
                SchoolClass.name == class_id
            ),
            ClassSubjectAllocation.term == term
        )
        .order_by(Subject.name)
    )

    res = await db.execute(stmt)
    rows = res.all()

    return [
        AllocationResponse(
            id=row.ClassSubjectAllocation.id,
            school_id=row.ClassSubjectAllocation.school_id,
            class_id=row.ClassSubjectAllocation.class_id,
            class_name=row.class_name,
            subject_id=row.ClassSubjectAllocation.subject_id,
            subject_name=row.subject_name,
            subject_code=row.subject_code,
            color_hex=row.color_hex,
            teacher_id=row.ClassSubjectAllocation.teacher_id,
            teacher_name=row.teacher_name,
            preferred_room_id=row.ClassSubjectAllocation.preferred_room_id,
            room_number=row.room_number,
            term=row.ClassSubjectAllocation.term,
            quarter_total_hours=row.ClassSubjectAllocation.quarter_total_hours,
            weeks_in_quarter=row.ClassSubjectAllocation.weeks_in_quarter,
            weekly_hours=row.ClassSubjectAllocation.weekly_hours,
            max_hours_per_day=row.ClassSubjectAllocation.max_hours_per_day,
        )
        for row in rows
    ]

@router.post("/allocate", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
async def allocate_subject_to_class(
    data: AllocationCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    """
    Sinfga yangi fan biriktirish va uning bitta chorakdagi umumiy va haftalik soatini belgilash.
    """
    # Haftalik soatni tekshiramiz: agar kiritilmagan bo'lsa choraklik soatdan hisoblaymiz
    weekly_hours = data.weekly_hours
    if weekly_hours <= 0 and data.weeks_in_quarter > 0:
        weekly_hours = round(data.quarter_total_hours / data.weeks_in_quarter)
        if weekly_hours < 1:
            weekly_hours = 1

    # Asosiy darslar sinfning o'z xonasida bo'lishini ta'minlash
    preferred_room_id = data.preferred_room_id
    if not preferred_room_id:
        subj = await db.get(Subject, data.subject_id)
        cls = await db.get(SchoolClass, data.class_id)
        if subj and cls:
            s_room_type = (subj.required_room_type or "GENERAL").upper()
            if any(k in s_room_type for k in ("KOMP", "IT", "INF", "COMPUTER")):
                r_res = await db.execute(select(Room).where(Room.school_id == current_user.school_id, Room.room_type == "COMPUTER_LAB"))
                r_match = r_res.scalars().first()
                if r_match:
                    preferred_room_id = r_match.id
            elif any(k in s_room_type for k in ("SPORT", "GYM")):
                r_res = await db.execute(select(Room).where(Room.school_id == current_user.school_id, Room.room_type == "GYM"))
                r_match = r_res.scalars().first()
                if r_match:
                    preferred_room_id = r_match.id
            elif "LAB" in s_room_type:
                r_res = await db.execute(select(Room).where(Room.school_id == current_user.school_id, Room.room_type == "LABORATORY"))
                r_match = r_res.scalars().first()
                if r_match:
                    preferred_room_id = r_match.id
            else:
                r_res = await db.execute(
                    select(Room).where(
                        Room.school_id == current_user.school_id,
                        Room.room_number.ilike(f"%{cls.name}%")
                    )
                )
                r_match = r_res.scalars().first()
                if r_match:
                    preferred_room_id = r_match.id

    new_alloc = ClassSubjectAllocation(
        school_id=current_user.school_id,
        class_id=data.class_id,
        subject_id=data.subject_id,
        teacher_id=data.teacher_id,
        preferred_room_id=preferred_room_id,
        term=data.term,
        quarter_total_hours=data.quarter_total_hours,
        weeks_in_quarter=data.weeks_in_quarter,
        weekly_hours=weekly_hours,
        max_hours_per_day=data.max_hours_per_day
    )

    db.add(new_alloc)
    await db.commit()
    await db.refresh(new_alloc)

    # Qo'shimcha nomlarni olish
    cls = await db.get(SchoolClass, new_alloc.class_id)
    subj = await db.get(Subject, new_alloc.subject_id)
    tchr = await db.get(Teacher, new_alloc.teacher_id) if new_alloc.teacher_id else None
    rm = await db.get(Room, new_alloc.preferred_room_id) if new_alloc.preferred_room_id else None

    return AllocationResponse(
        id=new_alloc.id,
        school_id=new_alloc.school_id,
        class_id=new_alloc.class_id,
        class_name=cls.name if cls else "",
        subject_id=new_alloc.subject_id,
        subject_name=subj.name if subj else "",
        subject_code=subj.short_code if subj else "",
        color_hex=subj.color_hex if subj else "#1E40AF",
        teacher_id=new_alloc.teacher_id,
        teacher_name=tchr.full_name if tchr else "",
        preferred_room_id=new_alloc.preferred_room_id,
        room_number=rm.room_number if rm else None,
        term=new_alloc.term,
        quarter_total_hours=new_alloc.quarter_total_hours,
        weeks_in_quarter=new_alloc.weeks_in_quarter,
        weekly_hours=new_alloc.weekly_hours,
        max_hours_per_day=new_alloc.max_hours_per_day,
    )

@router.put("/allocate/{allocation_id}", response_model=AllocationResponse)
async def update_allocation(
    allocation_id: str,
    data: AllocationUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    """
    Sinf faniga o'qituvchi, xona yoki dars soatini biriktirish / o'zgartirish
    """
    query = select(ClassSubjectAllocation).where(
        ClassSubjectAllocation.id == allocation_id,
        ClassSubjectAllocation.school_id == current_user.school_id
    )
    res = await db.execute(query)
    alloc = res.scalar_one_or_none()
    if not alloc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fan biriktiruvi topilmadi"
        )

    if data.teacher_id is not None:
        alloc.teacher_id = data.teacher_id if data.teacher_id != "" else None
    if data.preferred_room_id is not None:
        alloc.preferred_room_id = data.preferred_room_id if data.preferred_room_id != "" else None
    if data.weekly_hours is not None:
        alloc.weekly_hours = data.weekly_hours
    if data.quarter_total_hours is not None:
        alloc.quarter_total_hours = data.quarter_total_hours
    if data.max_hours_per_day is not None:
        alloc.max_hours_per_day = data.max_hours_per_day

    await db.commit()
    await db.refresh(alloc)

    cls = await db.get(SchoolClass, alloc.class_id)
    subj = await db.get(Subject, alloc.subject_id)
    tchr = await db.get(Teacher, alloc.teacher_id) if alloc.teacher_id else None
    rm = await db.get(Room, alloc.preferred_room_id) if alloc.preferred_room_id else None

    return AllocationResponse(
        id=alloc.id,
        school_id=alloc.school_id,
        class_id=alloc.class_id,
        class_name=cls.name if cls else "",
        subject_id=alloc.subject_id,
        subject_name=subj.name if subj else "",
        subject_code=subj.short_code if subj else "",
        color_hex=subj.color_hex if subj else "#1E40AF",
        teacher_id=alloc.teacher_id,
        teacher_name=tchr.full_name if tchr else "",
        preferred_room_id=alloc.preferred_room_id,
        room_number=rm.room_number if rm else None,
        term=alloc.term,
        quarter_total_hours=alloc.quarter_total_hours,
        weeks_in_quarter=alloc.weeks_in_quarter,
        weekly_hours=alloc.weekly_hours,
        max_hours_per_day=alloc.max_hours_per_day,
    )

@router.delete("/allocate/{allocation_id}", status_code=status.HTTP_200_OK)
async def delete_allocation(
    allocation_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    """
    Sinfdan fanni o'chirish
    """
    query = select(ClassSubjectAllocation).where(
        ClassSubjectAllocation.id == allocation_id,
        ClassSubjectAllocation.school_id == current_user.school_id
    )
    res = await db.execute(query)
    alloc = res.scalar_one_or_none()
    if not alloc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'chirish uchun fan biriktiruvi topilmadi"
        )

    await db.delete(alloc)
    await db.commit()
    return {"success": True, "message": "Fan o'quv rejasidan olib tashlandi"}
