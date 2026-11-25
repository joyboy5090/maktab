import sys
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from services.generator import (
    TimetableGeneratorCSP,
    Room as CSPRoom,
    Teacher as CSPTeacher,
    SchoolClass as CSPSchoolClass,
    Subject as CSPSubject,
    LessonRequirement as CSPLessonReq,
    ScheduledSlot
)

from database.models import (
    Teacher, Room, SchoolClass, Subject, ClassSubjectAllocation, TimetableEntry
)

class TimetableService:
    @staticmethod
    async def generate_and_save_schedule(
        db: AsyncSession,
        school_id: str,
        term: int = 1,
        slots_per_day: int = 6
    ) -> Dict[str, Any]:
        """
        1. Maktabga tegishli tanlangan chorak (term) dagi barcha sinflarning
           fanlar yuklamasini (o'quv rejasini) o'qiydi.
        2. CSP Backtracking generatorini ishga tushiradi.
        3. Natijalarni bazadagi timetable_entries jadvaliga saqlaydi.
        """
        # A. Bazadan ma'lumotlarni yuklab olish
        teachers_res = await db.execute(select(Teacher).where(Teacher.school_id == school_id))
        db_teachers = teachers_res.scalars().all()

        rooms_res = await db.execute(select(Room).where(Room.school_id == school_id))
        db_rooms = rooms_res.scalars().all()

        classes_res = await db.execute(select(SchoolClass).where(SchoolClass.school_id == school_id))
        db_classes = classes_res.scalars().all()

        subjects_res = await db.execute(select(Subject).where(Subject.school_id == school_id))
        db_subjects = subjects_res.scalars().all()

        # Aynan shu chorakka (term) tegishli fan yuklamalarini olamiz!
        alloc_res = await db.execute(
            select(ClassSubjectAllocation).where(
                ClassSubjectAllocation.school_id == school_id,
                ClassSubjectAllocation.term == term
            )
        )
        db_allocations = alloc_res.scalars().all()

        if not db_allocations:
            return {
                "success": False,
                "message": f"{term}-chorak uchun sinflarga birorta ham fan biriktirilmagan. Iltimos, avval 'O'quv Rejasi' bo'limida sinflarga fanlar va choraklik soatlarni kiriting."
            }

        if not db_classes or not db_teachers or not db_rooms or not db_subjects:
            return {
                "success": False,
                "message": "Generatsiya uchun ma'lumotlar yetarli emas (o'qituvchilar yoki xonalar kiritilmagan)."
            }

        # B. CSP modellariga o'giramiz
        csp_rooms = [
            CSPRoom(id=r.id, number=r.room_number, capacity=r.capacity, room_type=r.room_type)
            for r in db_rooms
        ]

        csp_teachers = [
            CSPTeacher(
                id=t.id,
                name=t.full_name,
                max_weekly_hours=9999,  # Haftalik soat cheklovi olib tashlangan
                max_daily_hours=max(t.max_daily_hours or 6, slots_per_day)
            )
            for t in db_teachers
        ]

        csp_classes = [
            CSPSchoolClass(id=c.id, name=c.name, student_count=c.student_count, shift=c.shift)
            for c in db_classes
        ]

        csp_subjects = [
            CSPSubject(
                id=s.id,
                name=s.name,
                short_code=s.short_code,
                color_hex=s.color_hex,
                required_room_type=s.required_room_type
            )
            for s in db_subjects
        ]

        # C. Har bir sinf uchun uning o'z sinf xonasini (home room) aniqlash
        # Masalan: "5-A" sinf uchun "5-A xona"
        class_home_rooms: Dict[str, str] = {}
        for c in db_classes:
            c_name_clean = c.name.strip().lower()
            for r in db_rooms:
                r_type = (r.room_type or "").upper()
                r_num_clean = r.room_number.strip().lower()
                r_name_clean = (r.name or "").strip().lower()
                if (
                    c_name_clean in r_num_clean or 
                    c_name_clean in r_name_clean or
                    r_num_clean.startswith(c_name_clean)
                ):
                    class_home_rooms[c.id] = r.id
                    break

        # Har bir sinf uchun biriktirilgan choraklik yuklama (haftalik soatlar) asosida dars talablari
        csp_reqs: List[CSPLessonReq] = []
        for alloc in db_allocations:
            subj = next((s for s in db_subjects if s.id == alloc.subject_id), None)
            s_req_room = (subj.required_room_type or "GENERAL").upper() if subj else "GENERAL"
            
            # Asosiy darslar sinfning o'z xonasida bo'ladi
            pref_room = alloc.preferred_room_id
            if "LAB" not in s_req_room and "SPORT" not in s_req_room and "KOMP" not in s_req_room and "GYM" not in s_req_room:
                pref_room = class_home_rooms.get(alloc.class_id, pref_room)

            hours_to_schedule = int(round(alloc.weekly_hours)) if alloc.weekly_hours else 0
            if alloc.weekly_hours and alloc.weekly_hours > 0 and hours_to_schedule == 0:
                hours_to_schedule = 1
            for i in range(hours_to_schedule):
                csp_reqs.append(
                    CSPLessonReq(
                        id=f"{alloc.id}_{i}",
                        class_id=alloc.class_id,
                        subject_id=alloc.subject_id,
                        teacher_id=alloc.teacher_id,
                        preferred_room_id=pref_room,
                        max_per_day=alloc.max_hours_per_day or 2
                    )
                )

        # D. CSP Algoritmini ishga tushirish
        solver = TimetableGeneratorCSP(
            classes=csp_classes,
            teachers=csp_teachers,
            rooms=csp_rooms,
            subjects=csp_subjects,
            requirements=csp_reqs,
            slots_per_day=slots_per_day
        )

        solution = solver.solve()

        if not solution:
            return {
                "success": False,
                "message": f"{term}-chorak o'quv rejasidagi soatlar bo'yicha ziddiyatsiz jadval tuzib bo'lmadi. Xonalar bandligi yoki smena to'siq bo'lmoqda."
            }

        # E. Ushbu chorak uchun eski jadvalni tozalash va yangisini saqlash
        await db.execute(
            delete(TimetableEntry).where(
                TimetableEntry.school_id == school_id,
                TimetableEntry.term == term
            )
        )

        new_entries = [
            TimetableEntry(
                school_id=school_id,
                term=term,
                day=slot.day,
                lesson_order=slot.slot,
                class_id=slot.lesson.class_id,
                subject_id=slot.lesson.subject_id,
                teacher_id=slot.lesson.teacher_id,
                room_id=slot.room.id,
            )
            for slot in solution
        ]

        db.add_all(new_entries)
        await db.commit()

        return {
            "success": True,
            "message": f"{term}-chorak dars jadvali muvaffaqiyatli tuzildi! Jami {len(new_entries)} ta dars joylashtirildi.",
            "total_lessons_scheduled": len(new_entries),
            "term": term
        }
