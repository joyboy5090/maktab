import re
from typing import Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from database.connection import get_tenant_db
from database.models import Teacher, Subject, SchoolClass, ClassSubjectAllocation
from schemas.schemas import TeacherCreate, TeacherResponse, TeacherUpdate
from core.rbac import CurrentUser, require_school_admin, require_any_authenticated
from utils.crud_factory import paginate_response

router = APIRouter(prefix="/teachers", tags=["O'qituvchilar Moduli"])

@router.get("")
async def list_teachers(
    page: int = Query(1, ge=1, description="Sahifa raqami"),
    per_page: int = Query(50, ge=1, le=100, description="Har bir sahifadagi elementlar soni"),
    search: Optional[str] = Query(None, description="O'qituvchi ismi bo'yicha qidiruv"),
    subject: Optional[str] = Query(None, description="Fan bo'yicha filtr"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    O'qituvchilar ro'yxatini filtrlash, qidiruv va sahifalash bilan olish
    """
    query = select(Teacher).where(Teacher.school_id == current_user.school_id)

    if search:
        query = query.where(Teacher.full_name.ilike(f"%{search.strip()}%"))
    if subject:
        query = query.where(Teacher.primary_subject.ilike(f"%{subject.strip()}%"))

    # Jami sonini hisoblash
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Sahifalash
    query = query.order_by(Teacher.full_name).offset((page - 1) * per_page).limit(per_page)
    res = await db.execute(query)
    teachers = res.scalars().all()

    teachers_data = [
        {
            "id": t.id,
            "school_id": t.school_id,
            "full_name": t.full_name,
            "primary_subject": t.primary_subject,
            "max_weekly_hours": t.max_weekly_hours,
            "max_daily_hours": t.max_daily_hours,
        }
        for t in teachers
    ]

    return paginate_response(teachers_data, total, page, per_page)

@router.get("/workload-demand")
async def get_teacher_workload_demand(
    term: Optional[int] = Query(1, description="Chorak raqami"),
    rate: int = Query(18, ge=10, le=36, description="1 stavka dars soati me'yori (soat/hafta)"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_any_authenticated)
):
    """
    Sinflarga o'tiladigan fanlar dars yuklamasiga qarab
    qancha o'qituvchi kerakligini (pedagogik ehtiyoj tahlilini) hisoblash.
    """
    import math
    from collections import defaultdict

    school_id = current_user.school_id

    # 1. Barcha fanlar
    s_res = await db.execute(
        select(Subject).where(Subject.school_id == school_id).order_by(Subject.name)
    )
    subjects = s_res.scalars().all()

    # 2. Barcha o'qituvchilar
    t_res = await db.execute(
        select(Teacher).where(Teacher.school_id == school_id)
    )
    teachers = t_res.scalars().all()

    # 3. Barcha sinflar
    c_res = await db.execute(
        select(SchoolClass).where(SchoolClass.school_id == school_id)
    )
    classes_map = {c.id: c.name for c in c_res.scalars().all()}

    # 4. Tanlangan chorakdagi o'quv rejasi yuklamalari
    alloc_stmt = (
        select(ClassSubjectAllocation)
        .where(
            ClassSubjectAllocation.school_id == school_id,
            ClassSubjectAllocation.term == term
        )
    )
    alloc_res = await db.execute(alloc_stmt)
    allocations = alloc_res.scalars().all()

    # Fanlar bo'yicha guruhlash
    subj_allocs = defaultdict(list)
    teacher_assigned_hours = defaultdict(int)
    for a in allocations:
        subj_allocs[a.subject_id].append(a)
        teacher_assigned_hours[a.teacher_id] += a.weekly_hours

    # Har bir fan bo'yicha tahlil
    subject_demands = []
    total_weekly_hours = 0
    total_required_teachers = 0

    for s in subjects:
        items = subj_allocs.get(s.id, [])
        hours = sum(item.weekly_hours for item in items)
        total_weekly_hours += hours

        # Qaysi sinflarga o'tiladi
        class_ids = sorted(list(set(item.class_id for item in items)))
        class_names = [classes_map[cid] for cid in class_ids if cid in classes_map]

        # 1 stavka = rate soat
        stavka_units = round(hours / rate, 2) if rate > 0 else 0

        # Kerakli o'qituvchi soni: math.ceil(hours / rate)
        req_teachers = math.ceil(hours / rate) if hours > 0 else 0
        total_required_teachers += req_teachers

        # Shu fanni o'tadigan / sohasi bo'lgan o'qituvchilar
        s_name_clean = s.name.strip().lower()
        matching_teachers = []
        for t in teachers:
            is_primary = False
            if t.primary_subject:
                t_subjs = [x.strip().lower() for x in re.split(r'[,/;&]+', t.primary_subject) if x.strip()]
                if any(s_name_clean == x or s_name_clean in x or x in s_name_clean for x in t_subjs):
                    is_primary = True

            has_alloc = any(item.teacher_id == t.id for item in items)

            if is_primary or has_alloc:
                matching_teachers.append({
                    "id": t.id,
                    "name": t.full_name,
                    "primary_subject": t.primary_subject,
                    "max_weekly_hours": t.max_weekly_hours,
                    "assigned_hours": teacher_assigned_hours.get(t.id, 0)
                })

        seen_tids = set()
        unique_teachers = []
        for mt in matching_teachers:
            if mt["id"] not in seen_tids:
                seen_tids.add(mt["id"])
                unique_teachers.append(mt)

        cur_count = len(unique_teachers)
        # O'qituvchilarning me'yordagi umumiy qamrovi (masalan: 1 nafar o'qituvchi * 18 soat = 18 soat)
        teachers_capacity = cur_count * rate
        
        # Ortib qolgan (ochiq/yetishmayotgan) dars soatlari
        overload_hours = max(0, hours - teachers_capacity)
        spare_hours = max(0, teachers_capacity - hours)
        
        deficit = req_teachers - cur_count

        if overload_hours > 0:
            status_code = "OVERLOAD"
            status_label = f"+{overload_hours} soat ortib qolgan"
        elif spare_hours > 0:
            status_code = "SURPLUS"
            status_label = f"{spare_hours} soat zaxira bor"
        else:
            status_code = "BALANCED"
            status_label = "0 soat (to'liq qoplangan)"

        subject_demands.append({
            "subject_id": s.id,
            "subject_name": s.name,
            "subject_code": s.short_code,
            "color_hex": s.color_hex or "#1E40AF",
            "total_weekly_hours": hours,
            "classes_count": len(class_names),
            "class_names": class_names,
            "stavka_units": stavka_units,
            "teachers_capacity_hours": teachers_capacity,
            "overload_hours": overload_hours,
            "spare_hours": spare_hours,
            "required_teachers": req_teachers,
            "current_teachers_count": cur_count,
            "current_teachers": unique_teachers,
            "deficit": max(0, deficit),
            "status": status_code,
            "status_label": status_label
        })

    total_overload_hours = sum(item["overload_hours"] for item in subject_demands)
    total_spare_hours = sum(item["spare_hours"] for item in subject_demands)
    total_covered_hours = sum(min(item["total_weekly_hours"], item["teachers_capacity_hours"]) for item in subject_demands)
    total_deficit = sum(item["deficit"] for item in subject_demands)
    total_stavka = round(total_weekly_hours / rate, 2) if rate > 0 else 0

    return {
        "term": term,
        "standard_rate_hours": rate,
        "summary": {
            "total_classes": len(classes_map),
            "total_weekly_hours": total_weekly_hours,
            "total_covered_hours": total_covered_hours,
            "total_overload_hours": total_overload_hours,
            "total_spare_hours": total_spare_hours,
            "total_stavka": total_stavka,
            "total_required_teachers": total_required_teachers,
            "total_current_teachers": len(teachers),
            "total_deficit": total_deficit
        },
        "subjects": subject_demands
    }

@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    data: TeacherCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    new_t = Teacher(
        school_id=current_user.school_id,
        full_name=data.full_name,
        primary_subject=data.primary_subject,
        max_weekly_hours=data.max_weekly_hours,
        max_daily_hours=data.max_daily_hours
    )
    db.add(new_t)
    await db.commit()
    await db.refresh(new_t)
    return new_t

@router.put("/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(Teacher).where(Teacher.id == teacher_id, Teacher.school_id == current_user.school_id)
    res = await db.execute(query)
    teacher = res.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'qituvchi topilmadi"
        )

    if data.full_name is not None:
        teacher.full_name = data.full_name
    if data.primary_subject is not None:
        teacher.primary_subject = data.primary_subject
    if data.max_weekly_hours is not None:
        teacher.max_weekly_hours = data.max_weekly_hours
    if data.max_daily_hours is not None:
        teacher.max_daily_hours = data.max_daily_hours

    await db.commit()
    await db.refresh(teacher)
    return teacher

@router.delete("/{teacher_id}", status_code=status.HTTP_200_OK)
async def delete_teacher(
    teacher_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: CurrentUser = Depends(require_school_admin)
):
    query = select(Teacher).where(Teacher.id == teacher_id, Teacher.school_id == current_user.school_id)
    res = await db.execute(query)
    teacher = res.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'chirish uchun o'qituvchi topilmadi"
        )

    await db.delete(teacher)
    await db.commit()
    return {"success": True, "message": "O'qituvchi bazadan o'chirildi"}
