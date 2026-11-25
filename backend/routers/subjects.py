from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from database.connection import get_tenant_db
from database.models import Subject
from schemas.schemas import SubjectCreate, SubjectResponse, SubjectUpdate
from core.rbac import CurrentUser, require_school_admin, require_any_authenticated
from utils.crud_factory import paginate_response

router = APIRouter(prefix="/subjects", tags=["Fanlar Moduli"])

@router.get("")
async def list_subjects(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    per_page: int = Query(50, ge=1, le=100, description="Har bir sahifadagi elementlar"),
    search: Optional[str] = Query(None, description="Fan nomi yoki kodi bo'yicha qidiruv"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    query = select(Subject).where(Subject.school_id == current_user.school_id)

    if search:
        query = query.where(
            or_(
                Subject.name.ilike(f"%{search.strip()}%"),
                Subject.short_code.ilike(f"%{search.strip()}%")
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(Subject.name).offset((page - 1) * per_page).limit(per_page)
    res = await db.execute(query)
    subjects = res.scalars().all()

    data = [
        {
            "id": s.id,
            "school_id": s.school_id,
            "name": s.name,
            "short_code": s.short_code,
            "required_room_type": s.required_room_type,
            "color_hex": s.color_hex,
        }
        for s in subjects
    ]

    return paginate_response(data, total, page, per_page)

@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    new_subject = Subject(
        school_id=current_user.school_id,
        name=data.name,
        short_code=data.short_code,
        required_room_type=data.required_room_type,
        color_hex=data.color_hex
    )
    db.add(new_subject)
    await db.commit()
    await db.refresh(new_subject)
    return new_subject

@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(Subject).where(Subject.id == subject_id, Subject.school_id == current_user.school_id)
    res = await db.execute(query)
    subject = res.scalar_one_or_none()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fan topilmadi"
        )

    if data.name is not None:
        subject.name = data.name
    if data.short_code is not None:
        subject.short_code = data.short_code
    if data.required_room_type is not None:
        subject.required_room_type = data.required_room_type
    if data.color_hex is not None:
        subject.color_hex = data.color_hex

    await db.commit()
    await db.refresh(subject)
    return subject

@router.delete("/{subject_id}", status_code=status.HTTP_200_OK)
async def delete_subject(
    subject_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(Subject).where(Subject.id == subject_id, Subject.school_id == current_user.school_id)
    res = await db.execute(query)
    subject = res.scalar_one_or_none()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'chirish uchun fan topilmadi"
        )

    await db.delete(subject)
    await db.commit()
    return {"success": True, "message": "Fan bazadan o'chirildi"}
