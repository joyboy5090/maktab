import os
import logging
import asyncio
from dotenv import load_dotenv

# Env yuklash
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from core.config import get_async_db_url
from schemas.schemas import validate_password_strength

logger = logging.getLogger("init_db")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

raw_alembic_url = os.getenv("ALEMBIC_DATABASE_URL", "").strip()
async_url = get_async_db_url(raw_alembic_url) if raw_alembic_url else "postgresql+asyncpg://localhost/placeholder"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from database.models import (
    School, User, Teacher, Room, SchoolClass, Subject
)

engine = create_async_engine(async_url, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init():
    if not os.getenv("ALEMBIC_DATABASE_URL", "").strip() and AsyncSessionLocal.kw.get("bind") is engine:
        # Agar testlar AsyncSessionLocal ni mock qilmagan bo'lsa, ALEMBIC_DATABASE_URL majburiy
        if not raw_alembic_url:
            raise RuntimeError("XATO: ALEMBIC_DATABASE_URL (owner rol) env o'zgaruvchisi belgilanmagan!")

    async with AsyncSessionLocal() as session:
        # Tekshiramiz: maktab bormi?
        res = await session.execute(select(School).limit(1))
        existing_school = res.scalar_one_or_none()

        if existing_school:
            print(f"   ✓ Maktab allaqachon mavjud: {existing_school.name}")
            school_id = existing_school.id
        else:
            print("2. Boshlang'ich maktab yaratilmoqda...")
            school = School(
                name="142-Umumta'lim Maktabi",
                slug="maktab142",
                subdomain="maktab142",
                email="admin@maktab142.uz",
                phone="+998 71 200 42 42",
                address="Toshkent shahri, Yunusobod tumani",
                is_active=True
            )
            session.add(school)
            await session.commit()
            await session.refresh(school)
            school_id = school.id
            print(f"   ✓ Maktab yaratildi: {school.name} (ID: {school_id})")

        # 2.1 Haqiqiy admin foydalanuvchini yaratish (hashed password bilan)
        from core.security import get_password_hash
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "").strip()
        admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "")
        if not admin_email or not admin_password:
            raise RuntimeError("XATO: DEFAULT_ADMIN_EMAIL va DEFAULT_ADMIN_PASSWORD env o'zgaruvchilari belgilanmagan!")
        validate_password_strength(admin_password)

        u_res = await session.execute(select(User).where(User.email == admin_email))
        admin_user = u_res.scalar_one_or_none()
        if not admin_user:
            print("2.1 Admin foydalanuvchi yaratilmoqda...")
            admin_user = User(
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                first_name="Rustam",
                last_name="Karimov",
                role="SCHOOL_ADMIN",
                school_id=school_id,
                is_active=True
            )
            session.add(admin_user)
            await session.commit()
            logger.info("Admin foydalanuvchi yaratildi: %s", admin_email)
        else:
            logger.info("Admin foydalanuvchi allaqachon mavjud, parol o'zgartirilmadi: %s", admin_email)

        # 3. Fanlar
        sub_res = await session.execute(select(Subject).where(Subject.school_id == school_id).limit(1))
        if not sub_res.scalar_one_or_none():
            print("3. Fanlar katalogi kiritilmoqda...")
            subjects_data = [
                ("Biologiya", "BIO", "#14B8A6", "Laboratoriya"),
                ("Fizika", "FIZ", "#8B5CF6", "Laboratoriya"),
                ("Geografiya", "GEO", "#059669", "Oddiy xona"),
                ("Informatika", "INF", "#0284C7", "Kompyuter xonasi"),
                ("Ingliz tili", "ENG", "#10B981", "Oddiy xona"),
                ("Jismoniy tarbiya", "SPORT", "#F59E0B", "Sport zal"),
                ("Kimyo", "KIM", "#EC4899", "Laboratoriya"),
                ("Matematika", "MAT", "#1E40AF", "Oddiy xona"),
                ("Ona tili va adabiyot", "ONA", "#6366F1", "Oddiy xona"),
                ("Tarix", "TAR", "#D97706", "Oddiy xona"),
            ]
            for sname, scode, scolor, sroom in subjects_data:
                session.add(Subject(
                    school_id=school_id,
                    name=sname,
                    short_code=scode,
                    color_hex=scolor,
                    required_room_type=sroom
                ))
            await session.commit()
            print("   ✓ Fanlar kiritildi!")
        else:
            print("   ✓ Fanlar allaqachon mavjud.")

        # 4. Xonalar
        room_res = await session.execute(select(Room).where(Room.school_id == school_id).limit(1))
        if not room_res.scalar_one_or_none():
            print("4. Xonalar kiritilmoqda...")
            rooms_data = [
                ("5-A xona", "5-A sinf xonasi", 32, "GENERAL"),
                ("5-B xona", "5-B sinf xonasi", 30, "GENERAL"),
                ("6-A xona", "6-A sinf xonasi", 32, "GENERAL"),
                ("6-B xona", "6-B sinf xonasi", 30, "GENERAL"),
                ("7-A xona", "7-A sinf xonasi", 30, "GENERAL"),
                ("7-B xona", "7-B sinf xonasi", 30, "GENERAL"),
                ("9-A xona", "9-A sinf xonasi", 35, "GENERAL"),
                ("10-A xona", "10-A sinf xonasi", 30, "GENERAL"),
                ("Lab-1", "Fizika Laboratoriyasi", 35, "LABORATORY"),
                ("Lab-2", "Kimyo Laboratoriyasi", 35, "LABORATORY"),
                ("IT-Zal", "Informatika xonasi", 35, "COMPUTER_LAB"),
                ("Sport Zal", "Katta sport majmuasi", 60, "GYM"),
            ]
            for rnum, rname, rcap, rtype in rooms_data:
                session.add(Room(
                    school_id=school_id,
                    room_number=rnum,
                    name=rname,
                    capacity=rcap,
                    room_type=rtype
                ))
            await session.commit()
            print("   ✓ Xonalar kiritildi!")
        else:
            print("   ✓ Xonalar allaqachon mavjud.")

        # 5. O'qituvchilar
        t_res = await session.execute(select(Teacher).where(Teacher.school_id == school_id).limit(1))
        if not t_res.scalar_one_or_none():
            print("5. O'qituvchilar kiritilmoqda...")
            teachers_data = [
                ("Dilnoza Oripova", "Biologiya", 18),
                ("Bobur Eshmatov", "Fizika", 16),
                ("Malika Karimova", "Ingliz tili", 18),
                ("Jasur Rahimov", "Jismoniy tarbiya", 22),
                ("Otabek Yusupov", "Kimyo", 16),
                ("Alisher Qodirov", "Matematika", 20),
            ]
            for tname, tsubj, thours in teachers_data:
                session.add(Teacher(
                    school_id=school_id,
                    full_name=tname,
                    primary_subject=tsubj,
                    max_weekly_hours=thours,
                    max_daily_hours=4
                ))
            await session.commit()
            print("   ✓ O'qituvchilar kiritildi!")
        else:
            print("   ✓ O'qituvchilar allaqachon mavjud.")

        # 6. Sinflar
        c_res = await session.execute(select(SchoolClass).where(SchoolClass.school_id == school_id).limit(1))
        if not c_res.scalar_one_or_none():
            print("6. Sinflar kiritilmoqda...")
            classes_data = [
                ("5-A", 5, 28, "1-smena"),
                ("5-B", 5, 26, "1-smena"),
                ("6-A", 6, 30, "1-smena"),
                ("7-B", 7, 25, "2-smena"),
                ("9-A", 9, 32, "1-smena"),
                ("10-A", 10, 24, "2-smena"),
            ]
            for cname, cgrade, ccount, cshift in classes_data:
                session.add(SchoolClass(
                    school_id=school_id,
                    name=cname,
                    grade_level=cgrade,
                    student_count=ccount,
                    shift=cshift
                ))
            await session.commit()
            print("   ✓ Sinflar kiritildi!")
        else:
            print("   ✓ Sinflar allaqachon mavjud.")

    print("\n🎉 TABRIKLAYMIZ! Barcha jadvallar va boshlang'ich ma'lumotlar PostgreSQL bazasida muvaffaqiyatli yaratildi!")

if __name__ == "__main__":
    asyncio.run(init())
