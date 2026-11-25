from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.connection import get_db_session
from database.models import School, Subscription, User, Teacher, SchoolClass
from core.rbac import CurrentUser, get_current_user, require_super_admin
from core.security import get_password_hash

router = APIRouter(prefix="/schools", tags=["Maktablar Boshqaruvi (Super Admin)"])

class SchoolCreateInput(BaseModel):
    name: str
    slug: str
    subdomain: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    admin_first_name: Optional[str] = "Direktor"
    admin_last_name: Optional[str] = "Maktabov"
    admin_email: Optional[str] = None
    admin_password: Optional[str] = "Admin123!"
    plan_name: Optional[str] = "Standard Pro"

class SchoolUpdateInput(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("", response_model=List[dict])
async def list_all_schools(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_super_admin)
):
    """
    Faqat SUPER_ADMIN uchun:
    Tizimdagi barcha maktablar ro'yxati va ularning statistikasi
    """
    res = await db.execute(select(School).order_by(School.created_at.asc()))
    schools = res.scalars().all()

    output = []
    for s in schools:
        # Statistikalar
        cls_count = await db.scalar(
            select(func.count(SchoolClass.id)).where(SchoolClass.school_id == s.id)
        ) or 0
        tch_count = await db.scalar(
            select(func.count(Teacher.id)).where(Teacher.school_id == s.id)
        ) or 0
        std_sum = await db.scalar(
            select(func.sum(SchoolClass.student_count)).where(SchoolClass.school_id == s.id)
        ) or 0

        # Obuna
        sub_res = await db.execute(
            select(Subscription).where(Subscription.school_id == s.id).limit(1)
        )
        subscription = sub_res.scalar_one_or_none()

        output.append({
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "subdomain": s.subdomain,
            "email": s.email,
            "phone": s.phone,
            "address": s.address,
            "is_active": s.is_active,
            "total_classes": cls_count,
            "total_teachers": tch_count,
            "total_students": int(std_sum),
            "subscription": {
                "plan_name": subscription.plan_name if subscription else "Free",
                "status": subscription.status if subscription else "ACTIVE",
                "max_students": subscription.max_students if subscription else 500,
                "max_teachers": subscription.max_teachers if subscription else 30,
            } if subscription else None
        })

    return output

@router.post("", response_model=dict)
async def create_school(
    payload: SchoolCreateInput,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_super_admin)
):
    """
    Yangi maktab yaratish va unga maktab ma'muri (SCHOOL_ADMIN) hisobini biriktirish
    """
    # Slug tekshirish
    existing = await db.scalar(select(School).where(School.slug == payload.slug))
    if existing:
        raise HTTPException(status_code=400, detail=f"'{payload.slug}' nomli maktab slug'i allaqachon band")

    new_school = School(
        name=payload.name,
        slug=payload.slug,
        subdomain=payload.subdomain or payload.slug,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        is_active=True
    )
    db.add(new_school)
    await db.flush()

    # Obuna qo'shish
    sub = Subscription(
        school_id=new_school.id,
        plan_name=payload.plan_name or "Standard Pro",
        status="ACTIVE",
        max_students=1000,
        max_teachers=60
    )
    db.add(sub)

    # Admin user yaratish
    adm_email = payload.admin_email or payload.email
    user_exists = await db.scalar(select(User).where(User.email == adm_email))
    if not user_exists:
        admin_user = User(
            school_id=new_school.id,
            role="SCHOOL_ADMIN",
            email=adm_email,
            password_hash=get_password_hash(payload.admin_password or "Admin123!"),
            first_name=payload.admin_first_name or "Direktor",
            last_name=payload.admin_last_name or "Maktabov",
            is_active=True
        )
        db.add(admin_user)

    await db.commit()
    await db.refresh(new_school)

    # Yangi maktab uchun 133-sonli buyruqdagi barcha 31 ta rasmiy fan va xonalarni avtomatik yaratish:
    try:
        from core.curriculum_templates import seed_official_subjects_for_school, seed_standard_rooms_for_school
        await seed_official_subjects_for_school(db, new_school.id)
        await seed_standard_rooms_for_school(db, new_school.id)
    except Exception as e:
        print(f"Yangi maktab fanlari avtomatik yaratilishida ogohlantirish: {e}")

    return {
        "success": True,
        "message": f"{new_school.name} muvaffaqiyatli ro'yxatdan o'tkazildi",
        "school": {
            "id": new_school.id,
            "name": new_school.name,
            "slug": new_school.slug,
            "email": new_school.email
        }
    }

@router.put("/{school_id}", response_model=dict)
async def update_school(
    school_id: str,
    payload: SchoolUpdateInput,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_super_admin)
):
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")

    if payload.name is not None:
        school.name = payload.name
    if payload.email is not None:
        school.email = payload.email
    if payload.phone is not None:
        school.phone = payload.phone
    if payload.address is not None:
        school.address = payload.address
    if payload.is_active is not None:
        school.is_active = payload.is_active

    await db.commit()
    return {"success": True, "message": "Maktab ma'lumotlari yangilandi"}
