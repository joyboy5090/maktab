from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.connection import get_tenant_db
from database.models import SchoolClass, Room
from schemas.schemas import ClassCreate, ClassResponse, ClassUpdate
from core.rbac import CurrentUser, require_school_admin, require_any_authenticated
from utils.crud_factory import paginate_response

router = APIRouter(prefix="/classes", tags=["Sinflar Moduli"])

@router.get("")
async def list_classes(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    per_page: int = Query(50, ge=1, le=100, description="Har bir sahifadagi elementlar"),
    search: Optional[str] = Query(None, description="Sinf nomi bo'yicha qidiruv (masalan: 5-A)"),
    shift: Optional[str] = Query(None, description="Smena bo'yicha filtr (1-smena, 2-smena)"),
    grade: Optional[int] = Query(None, description="Sinf darajasi bo'yicha filtr (5, 6, 7...)"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Sinflar ro'yxatini filtrlash, qidiruv va sahifalash bilan olish
    """
    query = select(SchoolClass).where(SchoolClass.school_id == current_user.school_id)

    if search:
        query = query.where(SchoolClass.name.ilike(f"%{search.strip()}%"))
    if shift:
        query = query.where(SchoolClass.shift.ilike(f"%{shift.strip()}%"))
    if grade:
        query = query.where(SchoolClass.grade_level == grade)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(SchoolClass.grade_level, SchoolClass.name).offset((page - 1) * per_page).limit(per_page)
    res = await db.execute(query)
    classes = res.scalars().all()

    data = [
        {
            "id": c.id,
            "school_id": c.school_id,
            "name": c.name,
            "grade_level": c.grade_level,
            "student_count": c.student_count,
            "shift": c.shift,
            "language": getattr(c, "language", "UZBEK") or "UZBEK",
        }
        for c in classes
    ]

    return paginate_response(data, total, page, per_page)

@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    data: ClassCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    new_class = SchoolClass(
        school_id=current_user.school_id,
        name=data.name,
        grade_level=data.grade_level,
        student_count=data.student_count,
        shift=data.shift,
        language=data.language or "UZBEK"
    )
    db.add(new_class)

    # Yangi sinf uchun uning o'z sinf xonasi avtomatik yaratiladi (masalan: 5-A xona)
    expected_room_num = f"{data.name} xona"
    existing_room = await db.execute(
        select(Room).where(
            Room.school_id == current_user.school_id,
            Room.room_number == expected_room_num
        )
    )
    if not existing_room.scalar_one_or_none():
        db.add(Room(
            school_id=current_user.school_id,
            room_number=expected_room_num,
            name=f"{data.name} sinf xonasi",
            capacity=data.student_count + 4,
            room_type="GENERAL"
        ))

    await db.commit()
    await db.refresh(new_class)

    # Tanlangan til va sinf bosqichiga asosan 2026-2027 tayanch o'quv rejasini avtomatik biriktirish:
    try:
        from core.curriculum_templates import apply_curriculum_to_class
        await apply_curriculum_to_class(
            db=db,
            school_id=current_user.school_id,
            class_id=new_class.id,
            class_name=new_class.name,
            grade_level=new_class.grade_level,
            language=new_class.language
        )
    except Exception as e:
        print(f"O'quv rejasi avtomatik yuklanishida xatolik: {e}")

    return new_class

@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: str,
    data: ClassUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(SchoolClass).where(SchoolClass.id == class_id, SchoolClass.school_id == current_user.school_id)
    res = await db.execute(query)
    cls = res.scalar_one_or_none()
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinf topilmadi"
        )

    if data.name is not None:
        cls.name = data.name
    if data.grade_level is not None:
        cls.grade_level = data.grade_level
    if data.student_count is not None:
        cls.student_count = data.student_count
    if data.shift is not None:
        cls.shift = data.shift
    if data.language is not None:
        cls.language = data.language

    await db.commit()
    await db.refresh(cls)
    return cls

@router.post("/{class_id}/apply-curriculum")
async def apply_class_curriculum(
    class_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    """
    Sinf uchun davlat tayanch o'quv rejasini (fanlar va soatlarni) qayta qo'llash
    """
    cls = await db.get(SchoolClass, class_id)
    if not cls or cls.school_id != current_user.school_id:
        raise HTTPException(status_code=404, detail="Sinf topilmadi")

    from core.curriculum_templates import apply_curriculum_to_class
    count = await apply_curriculum_to_class(
        db=db,
        school_id=current_user.school_id,
        class_id=cls.id,
        class_name=cls.name,
        grade_level=cls.grade_level,
        language=getattr(cls, "language", "UZBEK") or "UZBEK"
    )
    return {"success": True, "message": f"{count} ta fan davlat tayanch o'quv rejasi bo'yicha biriktirildi"}

@router.delete("/{class_id}", status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(SchoolClass).where(SchoolClass.id == class_id, SchoolClass.school_id == current_user.school_id)
    res = await db.execute(query)
    cls = res.scalar_one_or_none()
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'chirish uchun sinf topilmadi"
        )

    await db.delete(cls)
    await db.commit()
    return {"success": True, "message": "Sinf bazadan o'chirildi"}
