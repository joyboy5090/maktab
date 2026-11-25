"""
O'zbekiston Respublikasi Maktabgacha va maktab ta'limi vazirining 
2026-yil 10-apreldagi 133-sonli buyrug'i asosidagi
2026-2027-o'quv yili TAYANCH O'QUV REJALARI SHABLONLARI.
"""

from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

# Fanlar konfiguratsiyasi
SUBJECT_METADATA = {
    # Filologiya
    "Ona tili": {"code": "ONA", "room": "Oddiy xona", "color": "#6366F1"},
    "O‘qish savodxonligi": {"code": "OQISH", "room": "Oddiy xona", "color": "#8B5CF6"},
    "Adabiyot": {"code": "ADB", "room": "Oddiy xona", "color": "#EC4899"},
    "Rus tili": {"code": "RUS", "room": "Oddiy xona", "color": "#3B82F6"},
    "O‘zbek tili": {"code": "UZB", "room": "Oddiy xona", "color": "#10B981"},
    "Chet tili": {"code": "ENG", "room": "Oddiy xona", "color": "#06B6D4"},
    "Ona tili va o‘qish savodxonligi": {"code": "ONA_OQISH", "room": "Oddiy xona", "color": "#6366F1"},
    
    # Ijtimoiy fanlar
    "Tarixdan hikoyalar": {"code": "THIK", "room": "Oddiy xona", "color": "#F59E0B"},
    "Qadimgi dunyo tarixi": {"code": "QTAR", "room": "Oddiy xona", "color": "#D97706"},
    "O‘zbekiston tarixi": {"code": "UTAR", "room": "Oddiy xona", "color": "#B45309"},
    "Jahon tarixi": {"code": "JTAR", "room": "Oddiy xona", "color": "#92400E"},
    "Davlat va huquq asoslari": {"code": "HUQUQ", "room": "Oddiy xona", "color": "#78350F"},
    "Tarbiya": {"code": "TRB", "room": "Oddiy xona", "color": "#84CC16"},
    
    # Aniq fanlar
    "Matematika": {"code": "MAT", "room": "Oddiy xona", "color": "#1E40AF"},
    "Algebra": {"code": "ALG", "room": "Oddiy xona", "color": "#1D4ED8"},
    "Geometriya": {"code": "GEO_M", "room": "Oddiy xona", "color": "#2563EB"},
    "Informatika va axborot texnologiyalari": {"code": "INF", "room": "Kompyuter xonasi", "color": "#0284C7"},
    
    # Tabiiy va iqtisodiy fanlar
    "Tabiiy fan (Science)": {"code": "SCI", "room": "Laboratoriya", "color": "#14B8A6"},
    "Fizika": {"code": "FIZ", "room": "Laboratoriya", "color": "#8B5CF6"},
    "Astronomiya": {"code": "ASTRO", "room": "Oddiy xona", "color": "#4338CA"},
    "Kimyo": {"code": "KIM", "room": "Laboratoriya", "color": "#EC4899"},
    "Biologiya": {"code": "BIO", "room": "Laboratoriya", "color": "#10B981"},
    "Geografiya": {"code": "GEO", "room": "Oddiy xona", "color": "#059669"},
    "Iqtisodiy bilim asoslari": {"code": "IQTISOD", "room": "Oddiy xona", "color": "#D97706"},
    "Tadbirkorlik asoslari": {"code": "TADBIR", "room": "Oddiy xona", "color": "#EA580C"},
    
    # Amaliy fanlar
    "Musiqa madaniyati": {"code": "MUS", "room": "Oddiy xona", "color": "#F43F5E"},
    "Tasviriy san’at": {"code": "RASM", "room": "Oddiy xona", "color": "#A855F7"},
    "Chizmachilik": {"code": "CHIZMA", "room": "Oddiy xona", "color": "#64748B"},
    "Texnologiya": {"code": "TEXNO", "room": "Oddiy xona", "color": "#EAB308"},
    "Jismoniy tarbiya": {"code": "SPORT", "room": "Sport zal", "color": "#F59E0B"},
    "Chaqiruvga qadar boshlang‘ich tayyorgarlik": {"code": "CHQBT", "room": "Oddiy xona", "color": "#475569"},
}

# 1-ILOVA: O'ZBEK TILI SINFLARI (1-11 sinflar haftalik soatlari)
UZBEK_CURRICULUM: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"subject": "Ona tili", "hours": 4},
        {"subject": "O‘qish savodxonligi", "hours": 4},
        {"subject": "Chet tili", "hours": 1},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Tabiiy fan (Science)", "hours": 1},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 1},
    ], # Jami: 21 soat
    2: [
        {"subject": "Ona tili", "hours": 4},
        {"subject": "O‘qish savodxonligi", "hours": 3},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 2},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Tabiiy fan (Science)", "hours": 1},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 24 soat
    3: [
        {"subject": "Ona tili", "hours": 4},
        {"subject": "O‘qish savodxonligi", "hours": 3},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 2},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Tabiiy fan (Science)", "hours": 1},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 24 soat
    4: [
        {"subject": "Ona tili", "hours": 4},
        {"subject": "O‘qish savodxonligi", "hours": 3},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 2},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},  # Yangi joriy etildi!
        {"subject": "Tabiiy fan (Science)", "hours": 1},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 24 soat
    5: [
        {"subject": "Ona tili", "hours": 4},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 4},
        {"subject": "Tarixdan hikoyalar", "hours": 2},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Tabiiy fan (Science)", "hours": 2},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 2},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 29 soat
    6: [
        {"subject": "Ona tili", "hours": 4},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 4},
        {"subject": "Qadimgi dunyo tarixi", "hours": 2},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Tabiiy fan (Science)", "hours": 3},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 2},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 30 soat
    7: [
        {"subject": "Ona tili", "hours": 3},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 4},
        {"subject": "O‘zbekiston tarixi", "hours": 2},
        {"subject": "Jahon tarixi", "hours": 1},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Matematika", "hours": 5},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Fizika", "hours": 2},
        {"subject": "Kimyo", "hours": 2},
        {"subject": "Biologiya", "hours": 2},
        {"subject": "Geografiya", "hours": 2},
        {"subject": "Musiqa madaniyati", "hours": 1},
        {"subject": "Tasviriy san’at", "hours": 1},
        {"subject": "Texnologiya", "hours": 2},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 35 soat
    8: [
        {"subject": "Ona tili", "hours": 3},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 3},
        {"subject": "O‘zbekiston tarixi", "hours": 2},
        {"subject": "Jahon tarixi", "hours": 1},
        {"subject": "Davlat va huquq asoslari", "hours": 1},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Algebra", "hours": 3},
        {"subject": "Geometriya", "hours": 2},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
        {"subject": "Fizika", "hours": 2},
        {"subject": "Kimyo", "hours": 2},
        {"subject": "Biologiya", "hours": 2},
        {"subject": "Geografiya", "hours": 1.5},
        {"subject": "Iqtisodiy bilim asoslari", "hours": 0.5},
        {"subject": "Chizmachilik", "hours": 1},
        {"subject": "Texnologiya", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 33 soat
    9: [
        {"subject": "Ona tili", "hours": 3},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 3},
        {"subject": "O‘zbekiston tarixi", "hours": 2},
        {"subject": "Jahon tarixi", "hours": 1},
        {"subject": "Davlat va huquq asoslari", "hours": 1},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Algebra", "hours": 3},
        {"subject": "Geometriya", "hours": 2},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 2},
        {"subject": "Fizika", "hours": 2},
        {"subject": "Kimyo", "hours": 2},
        {"subject": "Biologiya", "hours": 2},
        {"subject": "Geografiya", "hours": 1.5},
        {"subject": "Iqtisodiy bilim asoslari", "hours": 0.5},
        {"subject": "Chizmachilik", "hours": 1},
        {"subject": "Texnologiya", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 2},
    ], # Jami: 34 soat
    10: [
        {"subject": "Ona tili", "hours": 2},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 2},
        {"subject": "O‘zbekiston tarixi", "hours": 1},
        {"subject": "Jahon tarixi", "hours": 1},
        {"subject": "Davlat va huquq asoslari", "hours": 1},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Algebra", "hours": 3},
        {"subject": "Geometriya", "hours": 2},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 2},
        {"subject": "Fizika", "hours": 2},
        {"subject": "Kimyo", "hours": 2},
        {"subject": "Biologiya", "hours": 2},
        {"subject": "Geografiya", "hours": 2},
        {"subject": "Jismoniy tarbiya", "hours": 2},
        {"subject": "Chaqiruvga qadar boshlang‘ich tayyorgarlik", "hours": 2},
    ], # Jami: 31 soat
    11: [
        {"subject": "Ona tili", "hours": 2},
        {"subject": "Adabiyot", "hours": 2},
        {"subject": "Rus tili", "hours": 2},
        {"subject": "Chet tili", "hours": 2},
        {"subject": "O‘zbekiston tarixi", "hours": 1},
        {"subject": "Jahon tarixi", "hours": 1},
        {"subject": "Davlat va huquq asoslari", "hours": 1},
        {"subject": "Tarbiya", "hours": 1},
        {"subject": "Algebra", "hours": 3},
        {"subject": "Geometriya", "hours": 2},
        {"subject": "Informatika va axborot texnologiyalari", "hours": 2},
        {"subject": "Fizika", "hours": 2},
        {"subject": "Astronomiya", "hours": 1},
        {"subject": "Kimyo", "hours": 2},
        {"subject": "Biologiya", "hours": 2},
        {"subject": "Tadbirkorlik asoslari", "hours": 1},
        {"subject": "Jismoniy tarbiya", "hours": 2},
        {"subject": "Chaqiruvga qadar boshlang‘ich tayyorgarlik", "hours": 2},
    ], # Jami: 31 soat
}

# 2-ILOVA: RUS TILI SINFLARI (Ta'lim rus tilida olib boriladigan sinflar)
RUSSIAN_CURRICULUM: Dict[int, List[Dict[str, Any]]] = {}
for g in range(1, 12):
    # O'zbek tili fanlarini asos qilib olib, filologiya fanlarini almashtiramiz
    base_list = [item.copy() for item in UZBEK_CURRICULUM[g]]
    # Ona tili va O'zbek tili farqlari:
    res = []
    for item in base_list:
        name = item["subject"]
        if name == "Rus tili":
            continue # Rus tili sinflarida rus tili "Ona tili" bo'ladi
        elif name == "Ona tili":
            # Rus sinflarda Ona tili (rus tili): 1-4 da 4, 5-6 da 3, 7-9 da 2, 10-11 da 1
            if g in (1, 2, 3, 4):
                res.append({"subject": "Ona tili", "hours": 4})
            elif g in (5, 6):
                res.append({"subject": "Ona tili", "hours": 3})
            elif g in (7, 8, 9):
                res.append({"subject": "Ona tili", "hours": 2})
            else:
                res.append({"subject": "Ona tili", "hours": 1})
            
            # O'zbek tili (davlat tili) qo'shiladi: 2-4 da 2s, 5-11 da 3s
            if g in (2, 3, 4):
                res.append({"subject": "O‘zbek tili", "hours": 2})
            elif g >= 5:
                res.append({"subject": "O‘zbek tili", "hours": 3})
        else:
            res.append(item)
    RUSSIAN_CURRICULUM[g] = res

# 3-ILOVA: QARDOSH TILLAR (qozoq, tojik, qirg'iz, turkman sinflari)
QARDOSH_CURRICULUM: Dict[int, List[Dict[str, Any]]] = {}
for g in range(1, 12):
    base_list = [item.copy() for item in UZBEK_CURRICULUM[g]]
    res = []
    if g == 1:
        res = [
            {"subject": "Ona tili va o‘qish savodxonligi", "hours": 8},
            {"subject": "Chet tili", "hours": 1},
            {"subject": "Tarbiya", "hours": 1},
            {"subject": "Matematika", "hours": 5},
            {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
            {"subject": "Tabiiy fan (Science)", "hours": 1},
            {"subject": "Musiqa madaniyati", "hours": 1},
            {"subject": "Tasviriy san’at", "hours": 1},
            {"subject": "Texnologiya", "hours": 1},
            {"subject": "Jismoniy tarbiya", "hours": 1},
        ]
    elif g in (2, 3):
        res = [
            {"subject": "Ona tili va o‘qish savodxonligi", "hours": 6},
            {"subject": "O‘zbek tili", "hours": 2},
            {"subject": "Rus tili", "hours": 1},
            {"subject": "Chet tili", "hours": 2},
            {"subject": "Tarbiya", "hours": 1},
            {"subject": "Matematika", "hours": 5},
            {"subject": "Informatika va axborot texnologiyalari", "hours": 1},
            {"subject": "Tabiiy fan (Science)", "hours": 1},
            {"subject": "Musiqa madaniyati", "hours": 1},
            {"subject": "Tasviriy san’at", "hours": 1},
            {"subject": "Texnologiya", "hours": 1},
            {"subject": "Jismoniy tarbiya", "hours": 2},
        ]
    else:
        for item in base_list:
            name = item["subject"]
            if name == "Ona tili":
                # Qardosh 1-namunada: 4-sinfda 3, 5-6 da 2, 7-9 da 1.5, 10-11 da 1
                hrs = 3 if g == 4 else (2 if g in (5, 6) else (1.5 if g in (7, 8, 9) else 1))
                res.append({"subject": "Ona tili", "hours": hrs})
                if g == 4:
                    res.append({"subject": "O‘qish savodxonligi", "hours": 3})
                # O'zbek tili
                res.append({"subject": "O‘zbek tili", "hours": 2 if g == 4 else 3})
            elif name == "Rus tili":
                res.append({"subject": "Rus tili", "hours": 1})
            elif name == "Adabiyot":
                hrs = 2 if g in (5, 6) else (1.5 if g in (7, 8, 9) else 1)
                res.append({"subject": "Adabiyot", "hours": hrs})
            else:
                res.append(item)
    QARDOSH_CURRICULUM[g] = res


def get_template_curriculum(language: str, grade_level: int) -> List[Dict[str, Any]]:
    """Til va sinf bosqichiga mos tayanch o'quv rejasini qaytaradi"""
    lang = (language or "UZBEK").upper().strip()
    grade = max(1, min(11, grade_level))

    if "RUS" in lang:
        return RUSSIAN_CURRICULUM.get(grade, UZBEK_CURRICULUM.get(grade, []))
    elif any(k in lang for k in ("QARDOSH", "KAZAKH", "TAJIK", "KYRGYZ", "TURKMEN")):
        return QARDOSH_CURRICULUM.get(grade, UZBEK_CURRICULUM.get(grade, []))
    else:
        return UZBEK_CURRICULUM.get(grade, [])


async def apply_curriculum_to_class(
    db: AsyncSession,
    school_id: str,
    class_id: str,
    class_name: str,
    grade_level: int,
    language: str
) -> int:
    """
    Sinf uchun davlat standarti (2026-2027 buyrug'i) bo'yicha
    fanlar va haftalik soatlarni avtomatik tarzda yaratish va biriktirish.
    """
    from database.models import Subject, Room, ClassSubjectAllocation
    
    curriculum_items = get_template_curriculum(language, grade_level)
    if not curriculum_items:
        return 0

    # 1. Maktabdagi mavjud fanlarni yuklaymiz (nomi va kodi bo'yicha xaritalash)
    sub_res = await db.execute(select(Subject).where(Subject.school_id == school_id))
    existing_subjects = {s.name.strip().lower(): s for s in sub_res.scalars().all()}
    existing_by_code = {s.short_code.strip().upper(): s for s in existing_subjects.values()}

    # 2. Xonalarni yuklaymiz
    rooms_res = await db.execute(select(Room).where(Room.school_id == school_id))
    rooms = rooms_res.scalars().all()
    
    home_room = next((r for r in rooms if class_name.lower() in r.room_number.lower()), None)
    lab_rooms = [r for r in rooms if r.room_type == "LABORATORY"]
    it_rooms = [r for r in rooms if r.room_type == "COMPUTER_LAB"]
    gym_rooms = [r for r in rooms if r.room_type == "GYM"]

    created_count = 0
    valid_subject_ids = set()

    for item in curriculum_items:
        s_name = item["subject"]
        weekly_h = item["hours"]
        meta = SUBJECT_METADATA.get(s_name, {"code": s_name[:3].upper(), "room": "Oddiy xona", "color": "#1E40AF"})

        # Fanni topamiz yoki avtomatik yaratamiz
        subj = existing_subjects.get(s_name.lower())
        if not subj:
            code = meta["code"]
            # agar kod band bo'lsa yangilaymiz
            if code in existing_by_code:
                code = f"{code}_{grade_level}"[:20]
            
            subj = Subject(
                school_id=school_id,
                name=s_name,
                short_code=code,
                required_room_type=meta["room"],
                color_hex=meta["color"]
            )
            db.add(subj)
            await db.flush()
            existing_subjects[s_name.lower()] = subj
            existing_by_code[code] = subj

        valid_subject_ids.add(subj.id)

        # Xona tanlash
        pref_room_id = None
        req_room = (subj.required_room_type or "").upper()
        if any(k in req_room for k in ("KOMP", "IT", "COMPUTER")) and it_rooms:
            pref_room_id = it_rooms[0].id
        elif any(k in req_room for k in ("SPORT", "GYM")) and gym_rooms:
            pref_room_id = gym_rooms[0].id
        elif "LAB" in req_room and lab_rooms:
            pref_room_id = lab_rooms[0].id
        elif home_room:
            pref_room_id = home_room.id

        # Choraklik soatlar: 9 hafta hisobidan
        quarter_hours = round(weekly_h * 9)

        # Mavjud biriktiruvni tekshiramiz
        alloc_res = await db.execute(
            select(ClassSubjectAllocation).where(
                and_(
                    ClassSubjectAllocation.school_id == school_id,
                    ClassSubjectAllocation.class_id == class_id,
                    ClassSubjectAllocation.subject_id == subj.id,
                    ClassSubjectAllocation.term == 1
                )
            )
        )
        existing_alloc = alloc_res.scalar_one_or_none()

        if existing_alloc:
            existing_alloc.weekly_hours = weekly_h
            existing_alloc.quarter_total_hours = quarter_hours
            if not existing_alloc.preferred_room_id and pref_room_id:
                existing_alloc.preferred_room_id = pref_room_id
        else:
            new_alloc = ClassSubjectAllocation(
                school_id=school_id,
                class_id=class_id,
                subject_id=subj.id,
                teacher_id=None,  # O'qituvchi bo'sh (vakant)
                preferred_room_id=pref_room_id,
                term=1,
                weekly_hours=weekly_h,
                quarter_total_hours=quarter_hours,
                weeks_in_quarter=9,
                max_hours_per_day=2
            )
            db.add(new_alloc)
            created_count += 1

    # Ushbu sinf bosqichiga tegishli bo'lmagan ortiqcha fanlarni tozalaymiz
    all_allocs_res = await db.execute(
        select(ClassSubjectAllocation).where(
            and_(
                ClassSubjectAllocation.school_id == school_id,
                ClassSubjectAllocation.class_id == class_id,
                ClassSubjectAllocation.term == 1
            )
        )
    )
    for old_alloc in all_allocs_res.scalars().all():
        if old_alloc.subject_id not in valid_subject_ids:
            await db.delete(old_alloc)

    await db.commit()
    return created_count


async def sync_all_classes_curriculum(db: AsyncSession, school_id: str = None) -> int:
    """
    Barcha sinflar uchun 133-sonli buyruqdagi tayanch o'quv rejasini
    aniq moslashtirib, avtomatik sinxronlash.
    """
    from database.models import SchoolClass
    
    stmt = select(SchoolClass)
    if school_id:
        stmt = stmt.where(SchoolClass.school_id == school_id)
    res = await db.execute(stmt)
    classes = res.scalars().all()
    
    count = 0
    for cls in classes:
        lang = getattr(cls, "language", "UZBEK") or "UZBEK"
        await apply_curriculum_to_class(
            db=db,
            school_id=cls.school_id,
            class_id=cls.id,
            class_name=cls.name,
            grade_level=cls.grade_level,
            language=lang
        )
        count += 1
    return count


NAME_SPELLING_CORRECTIONS = {
    "jaxon tarixi": "Jahon tarixi",
    "jahon tarixi": "Jahon tarixi",
    "o'zbekiston tarix": "O‘zbekiston tarixi",
    "o'zbekiston tarixi": "O‘zbekiston tarixi",
    "davlat huquq asoslari": "Davlat va huquq asoslari",
    "davlat va huquq asoslari": "Davlat va huquq asoslari",
    "musiqa": "Musiqa madaniyati",
    "musiqa madaniyati": "Musiqa madaniyati",
    "tasviriy san'at": "Tasviriy san’at",
    "tasviriy san’at": "Tasviriy san’at",
    "informatika": "Informatika va axborot texnologiyalari",
    "informatika va axborot texnologiyalari": "Informatika va axborot texnologiyalari",
    "tabiiy fan": "Tabiiy fan (Science)",
    "tabiiy fan (science)": "Tabiiy fan (Science)",
    "chyot": "Chaqiruvga qadar boshlang‘ich tayyorgarlik",
    "chaqiriqqacha tayyorgarlik": "Chaqiruvga qadar boshlang‘ich tayyorgarlik",
    "chaqiruvga qadar boshlang'ich tayyorgarlik": "Chaqiruvga qadar boshlang‘ich tayyorgarlik",
}


async def seed_official_subjects_for_school(db: AsyncSession, school_id: str) -> int:
    """
    Yangi yoki mavjud maktab uchun vazirlikning 133-sonli buyrug'idagi
    barcha 31 ta rasmiy fanni avtomatik yaratish.
    Mavjud fanlarni o'chirmaydi.
    """
    from database.models import Subject
    
    res = await db.execute(select(Subject).where(Subject.school_id == school_id))
    existing_subjects = res.scalars().all()
    existing_names = {s.name.strip().lower() for s in existing_subjects}
    existing_codes = {s.short_code.strip().upper() for s in existing_subjects}
    
    added_count = 0
    for s_name, meta in SUBJECT_METADATA.items():
        if s_name.strip().lower() in existing_names:
            continue
        
        code = meta["code"]
        if code in existing_codes:
            suffix = 1
            while f"{code}_{suffix}"[:20] in existing_codes:
                suffix += 1
            code = f"{code}_{suffix}"[:20]
        
        new_subj = Subject(
            school_id=school_id,
            name=s_name,
            short_code=code,
            required_room_type=meta["room"],
            color_hex=meta["color"]
        )
        db.add(new_subj)
        existing_names.add(s_name.strip().lower())
        existing_codes.add(code)
        added_count += 1
        
    if added_count > 0:
        await db.commit()
    return added_count


async def seed_standard_rooms_for_school(db: AsyncSession, school_id: str):
    """
    Yangi maktab uchun maxsus xonalar (lab, IT, sport zal) yaratish
    """
    from database.models import Room
    
    rooms_data = [
        ("IT-Zal", "Informatika va axborot texnologiyalari xonasi", 35, "COMPUTER_LAB"),
        ("Lab-1", "Fizika va Biologiya laboratoriyasi", 35, "LABORATORY"),
        ("Lab-2", "Kimyo laboratoriyasi", 35, "LABORATORY"),
        ("Sport Zal", "Katta sport majmuasi", 60, "GYM"),
    ]
    for rnum, rname, rcap, rtype in rooms_data:
        existing = await db.scalar(
            select(Room).where(
                Room.school_id == school_id,
                Room.room_number == rnum
            )
        )
        if not existing:
            db.add(Room(
                school_id=school_id,
                room_number=rnum,
                name=rname,
                capacity=rcap,
                room_type=rtype
            ))
    await db.commit()


async def normalize_school_subjects(db: AsyncSession, school_id: str):
    """
    Mavjud maktabdagi fanlarning imloviy xatolarini to'g'rilash (o'chirmasdan)
    va o'qituvchilarning biriktiruvlarini saqlab qolish.
    """
    from database.models import Subject, Teacher
    
    sub_res = await db.execute(select(Subject).where(Subject.school_id == school_id))
    subjects = sub_res.scalars().all()
    
    for s in subjects:
        low_name = s.name.strip().lower()
        if low_name in NAME_SPELLING_CORRECTIONS:
            official_name = NAME_SPELLING_CORRECTIONS[low_name]
            old_name = s.name
            s.name = official_name
            if official_name in SUBJECT_METADATA:
                s.required_room_type = SUBJECT_METADATA[official_name]["room"]
                s.color_hex = SUBJECT_METADATA[official_name]["color"]
                s.short_code = SUBJECT_METADATA[official_name]["code"]
            
            # O'qituvchilarning primary_subject nomini ham sinxronlash
            tch_res = await db.execute(
                select(Teacher).where(
                    Teacher.school_id == school_id,
                    Teacher.primary_subject == old_name
                )
            )
            for t in tch_res.scalars().all():
                t.primary_subject = official_name
                
    await db.commit()
    # Yetishmayotgan barcha rasmiy fanlarni to'ldiramiz
    await seed_official_subjects_for_school(db, school_id)

