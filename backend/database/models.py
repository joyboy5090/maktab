import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, ForeignKey, DateTime, Text, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database.connection import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class School(Base):
    __tablename__ = "schools"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    subdomain = Column(String(100), unique=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="school", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="school", cascade="all, delete-orphan")
    classes = relationship("SchoolClass", back_populates="school", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="school", cascade="all, delete-orphan")

class Subscription(Base):
    """SaaS obuna va limitlar jadvali"""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    plan_name = Column(String(100), default="Standard Pro", nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    max_students = Column(Integer, default=1000, nullable=False)
    max_teachers = Column(Integer, default=60, nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_subscriptions_school", "school_id"),
    )

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True)
    role = Column(String(50), default="TEACHER", nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    school = relationship("School", back_populates="users")

    __table_args__ = (
        CheckConstraint("role IN ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER')", name="ck_users_role"),
        Index("idx_users_email", "email"),
        Index("idx_users_school", "school_id"),
    )

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    full_name = Column(String(200), nullable=False)
    primary_subject = Column(String(500))
    max_weekly_hours = Column(Integer, default=24, nullable=False)
    max_daily_hours = Column(Integer, default=5, nullable=False)
    unavailable_slots = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    school = relationship("School", back_populates="teachers")

    __table_args__ = (
        Index("idx_teachers_school", "school_id"),
    )

class TeacherAvailability(Base):
    """O'qituvchining dars berishi mumkin bo'lgan bo'sh vaqtlari"""
    __tablename__ = "teacher_availabilities"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=False), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    day = Column(String(30), nullable=False)
    lesson_order = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "day IN ('Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY')",
            name="ck_teacher_avail_day"
        ),
        UniqueConstraint("school_id", "teacher_id", "day", "lesson_order", name="uq_teacher_avail_slot"),
        Index("idx_teacher_avail_school", "school_id"),
    )

class Room(Base):
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    room_number = Column(String(50), nullable=False)
    name = Column(String(100))
    capacity = Column(Integer, default=30, nullable=False)
    room_type = Column(String(50), default="GENERAL", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    school = relationship("School", back_populates="rooms")
    __table_args__ = (
        CheckConstraint(
            "room_type IN ('GENERAL', 'LABORATORY', 'GYM', 'COMPUTER_LAB', 'LANGUAGE_LAB', 'Oddiy xona', 'Laboratoriya', 'Sport zal', 'Kompyuter xonasi')",
            name="ck_rooms_room_type"
        ),
        UniqueConstraint("school_id", "room_number", name="uq_school_room"),
        Index("idx_rooms_school", "school_id"),
    )

class SchoolClass(Base):
    __tablename__ = "classes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    grade_level = Column(Integer, nullable=False)
    student_count = Column(Integer, default=25, nullable=False)
    shift = Column(String(50), default="MORNING", nullable=False)
    language = Column(String(50), default="UZBEK", nullable=False)
    class_master = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    school = relationship("School", back_populates="classes")
    __table_args__ = (
        CheckConstraint(
            "shift IN ('MORNING', 'AFTERNOON', '1-smena', '2-smena')",
            name="ck_classes_shift"
        ),
        UniqueConstraint("school_id", "name", name="uq_school_class"),
        Index("idx_classes_school", "school_id"),
    )

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    short_code = Column(String(20), nullable=False)
    required_room_type = Column(String(50), default="GENERAL", nullable=False)
    color_hex = Column(String(10), default="#1E40AF")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    school = relationship("School", back_populates="subjects")
    __table_args__ = (
        CheckConstraint(
            "required_room_type IN ('GENERAL', 'LABORATORY', 'GYM', 'COMPUTER_LAB', 'LANGUAGE_LAB', 'Oddiy xona', 'Laboratoriya', 'Sport zal', 'Kompyuter xonasi')",
            name="ck_subjects_room_type"
        ),
        UniqueConstraint("school_id", "short_code", name="uq_school_subject_code"),
        Index("idx_subjects_school", "school_id"),
    )

class ClassSubjectAllocation(Base):
    __tablename__ = "class_subject_allocations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(UUID(as_uuid=False), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=False), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=False), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    preferred_room_id = Column(UUID(as_uuid=False), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    
    term = Column(Integer, default=1, nullable=False)
    quarter_total_hours = Column(Integer, default=36, nullable=False)
    weeks_in_quarter = Column(Integer, default=9, nullable=False)
    weekly_hours = Column(Float, nullable=False)
    max_hours_per_day = Column(Integer, default=2, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("school_id", "class_id", "subject_id", "term", name="uq_class_sub_term"),
        Index("idx_allocations_school_term", "school_id", "term"),
    )

class TimeSlot(Base):
    """Qo'ng'iroqlar jadvali (dars soatlari vaqtlari)"""
    __tablename__ = "time_slots"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    lesson_order = Column(Integer, nullable=False)
    shift = Column(String(50), default="MORNING", nullable=False)
    start_time = Column(String(20), nullable=False)
    end_time = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "shift IN ('MORNING', 'AFTERNOON', '1-smena', '2-smena')",
            name="ck_time_slots_shift"
        ),
        UniqueConstraint("school_id", "shift", "lesson_order", name="uq_school_shift_slot"),
        Index("idx_timeslots_school", "school_id"),
    )

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    term = Column(Integer, default=1, nullable=False)
    day = Column(String(30), nullable=False)
    lesson_order = Column(Integer, nullable=False)
    class_id = Column(UUID(as_uuid=False), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=False), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=False), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    room_id = Column(UUID(as_uuid=False), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "day IN ('Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY')",
            name="ck_timetable_day"
        ),
        UniqueConstraint("school_id", "term", "day", "lesson_order", "class_id", name="uq_class_slot_term"),
        Index("idx_timetable_school_term", "school_id", "term"),
        Index("idx_timetable_class", "class_id"),
    )

class AuditLog(Base):
    """Audit loglar: har bir o'zgarishlar tarixi"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(100), nullable=False)
    old_data = Column(JSONB, nullable=True)
    new_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("idx_audit_logs_school", "school_id"),
    )


class RefreshToken(Base):
    """Refresh tokenlar, rotatsiya va reuse detection jadvali"""
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
    )


class TimetableJob(Base):
    """Asinxron dars jadvali generatsiya vazifalari"""
    __tablename__ = "timetable_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    school_id = Column(UUID(as_uuid=False), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    term = Column(Integer, default=1, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    result_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'done', 'failed')", name="ck_timetable_jobs_status"),
        Index("idx_timetable_jobs_school_status", "school_id", "status"),
    )
