import re
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, field_validator

def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Parol kamida 8 ta belgidan iborat bo'lishi kerak")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Parol UTF-8 da ko'pi bilan 72 bayt bo'lishi kerak")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Parolda kamida 1 ta katta harf bo'lishi kerak")
    if not re.search(r"\d", v):
        raise ValueError("Parolda kamida 1 ta raqam bo'lishi kerak")
    return v

# Auth Schemas
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: str
    school_id: Optional[str] = None
    email: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "TEACHER"
    school_id: Optional[str] = None

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)

# School Tenant Schemas
class SchoolCreate(BaseModel):
    name: str
    slug: str
    subdomain: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class SchoolResponse(SchoolCreate):
    id: str
    is_active: bool

class TeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    primary_subject: Optional[str] = None
    max_weekly_hours: Optional[int] = None
    max_daily_hours: Optional[int] = None

class RoomUpdate(BaseModel):
    room_number: Optional[str] = None
    name: Optional[str] = None
    capacity: Optional[int] = None
    room_type: Optional[str] = None

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    grade_level: Optional[int] = None
    student_count: Optional[int] = None
    shift: Optional[str] = None

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    short_code: Optional[str] = None
    required_room_type: Optional[str] = None
    color_hex: Optional[str] = None

# Teacher Schemas
class TeacherCreate(BaseModel):
    full_name: str
    primary_subject: Optional[str] = None
    max_weekly_hours: int = 24
    max_daily_hours: int = 5

class TeacherResponse(TeacherCreate):
    id: str
    school_id: str

# Room Schemas
class RoomCreate(BaseModel):
    room_number: str
    name: Optional[str] = None
    capacity: int = 30
    room_type: str = "GENERAL"

class RoomResponse(RoomCreate):
    id: str
    school_id: str

# Class Schemas
class ClassCreate(BaseModel):
    name: str
    grade_level: int
    student_count: int = 25
    shift: str = "MORNING"
    language: str = "UZBEK"

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    grade_level: Optional[int] = None
    student_count: Optional[int] = None
    shift: Optional[str] = None
    language: Optional[str] = None

class ClassResponse(ClassCreate):
    id: str
    school_id: str

# Subject Schemas
class SubjectCreate(BaseModel):
    name: str
    short_code: str
    required_room_type: str = "GENERAL"
    color_hex: str = "#1E40AF"

class SubjectResponse(SubjectCreate):
    id: str
    school_id: str

# CURRICULUM (Sinfga fan biriktirish va choraklik soatlar taqsimoti)
class AllocationCreate(BaseModel):
    class_id: str
    subject_id: str
    teacher_id: Optional[str] = None
    preferred_room_id: Optional[str] = None
    term: int = 1                     # 1, 2, 3, 4 - chorak
    quarter_total_hours: int = 36     # Choraklik umumiy dars soatlari
    weeks_in_quarter: int = 9         # Chorakdagi haftalar soni
    weekly_hours: float = 4           # Haftalik dars soati
    max_hours_per_day: int = 2        # Kunlik maksimal dars soati

class AllocationUpdate(BaseModel):
    teacher_id: Optional[str] = None
    preferred_room_id: Optional[str] = None
    weekly_hours: Optional[float] = None
    quarter_total_hours: Optional[int] = None
    max_hours_per_day: Optional[int] = None

class AllocationResponse(BaseModel):
    id: str
    school_id: str
    class_id: str
    class_name: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    color_hex: Optional[str] = None
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    preferred_room_id: Optional[str] = None
    room_number: Optional[str] = None
    term: int
    quarter_total_hours: int
    weeks_in_quarter: int
    weekly_hours: float
    max_hours_per_day: int

# Timetable Generation & Slot Schemas
class GenerateTimetableRequest(BaseModel):
    term: int = 1
    slots_per_day: int = 6

class TimetableItemResponse(BaseModel):
    id: str
    term: int
    day: str
    lesson_order: int
    class_id: str
    class_name: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    color_hex: Optional[str] = None
    teacher_id: str
    teacher_name: Optional[str] = None
    room_id: str
    room_number: Optional[str] = None
