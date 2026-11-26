import sys
import os
import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text, event

import database.connection as db_conn
from services.generator import (
    TimetableGeneratorCSP,
    Room as CSPRoom,
    Teacher as CSPTeacher,
    SchoolClass as CSPSchoolClass,
    Subject as CSPSubject,
    LessonRequirement as CSPLessonReq,
    ScheduledSlot
)
from services.generator_cpsat import TimetableGeneratorCPSAT

from database.models import (
    Teacher, Room, SchoolClass, Subject, ClassSubjectAllocation, TimetableEntry, TimetableJob
)

_process_pool = ProcessPoolExecutor(max_workers=2)


def _run_solver_in_process(
    csp_classes: List[CSPSchoolClass],
    csp_teachers: List[CSPTeacher],
    csp_rooms: List[CSPRoom],
    csp_subjects: List[CSPSubject],
    csp_reqs: List[CSPLessonReq],
    slots_per_day: int,
    save_partial: bool,
    solver_type: str,
    pinned_slots: Optional[List[ScheduledSlot]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """Alohida OS jarayonida (ProcessPoolExecutor) ishlaydigan sof CPU yechuvchi."""
    if solver_type == "legacy":
        solver = TimetableGeneratorCSP(
            classes=csp_classes,
            teachers=csp_teachers,
            rooms=csp_rooms,
            subjects=csp_subjects,
            requirements=csp_reqs,
            slots_per_day=slots_per_day,
        )
        if pinned_slots:
            for ps in pinned_slots:
                solver.assign(ps.lesson, ps.day, ps.slot, ps.room)
    else:
        solver = TimetableGeneratorCPSAT(
            classes=csp_classes,
            teachers=csp_teachers,
            rooms=csp_rooms,
            subjects=csp_subjects,
            requirements=csp_reqs,
            slots_per_day=slots_per_day,
            pinned_slots=pinned_slots,
        )

    if save_partial:
        solution, unplaced = solver.solve_partial()
    else:
        solution = solver.solve()
        unplaced = solver.unplaced

    all_placed = solution is not None and len(solution) == len(csp_reqs) and not unplaced
    slots_payload = [
        {
            "day": s.day,
            "slot": s.slot,
            "class_id": s.lesson.class_id,
            "subject_id": s.lesson.subject_id,
            "teacher_id": s.lesson.teacher_id,
            "room_id": s.room.id,
        }
        for s in (solution or [])
    ]
    return slots_payload, unplaced, all_placed

class TimetableService:
    @staticmethod
    def _parse_unavailable_slots(raw_slots: Any) -> set:
        parsed = set()
        if not raw_slots or not isinstance(raw_slots, list):
            return parsed
        for item in raw_slots:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                parsed.add((str(item[0]), int(item[1])))
            elif isinstance(item, dict) and "day" in item and "slot" in item:
                parsed.add((str(item["day"]), int(item["slot"])))
        return parsed

    @staticmethod
    async def generate_and_save_schedule(
        db: AsyncSession,
        school_id: str,
        term: int = 1,
        slots_per_day: int = 6,
        save_partial: bool = False,
        solver_type: str = "cpsat"
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
                max_weekly_hours=t.max_weekly_hours if t.max_weekly_hours is not None else 36,
                max_daily_hours=t.max_daily_hours if t.max_daily_hours is not None else 6,
                unavailable_slots=TimetableService._parse_unavailable_slots(getattr(t, "unavailable_slots", None))
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

        # D. Solver tanlovi: default OR-Tools CP-SAT, zaxira sifatida legacy CSP
        if solver_type == "legacy":
            solver = TimetableGeneratorCSP(
                classes=csp_classes,
                teachers=csp_teachers,
                rooms=csp_rooms,
                subjects=csp_subjects,
                requirements=csp_reqs,
                slots_per_day=slots_per_day
            )
        else:
            solver = TimetableGeneratorCPSAT(
                classes=csp_classes,
                teachers=csp_teachers,
                rooms=csp_rooms,
                subjects=csp_subjects,
                requirements=csp_reqs,
                slots_per_day=slots_per_day
            )

        if save_partial:
            solution, unplaced = await asyncio.to_thread(solver.solve_partial)
        else:
            solution = await asyncio.to_thread(solver.solve)
            unplaced = solver.unplaced

        all_placed = solution is not None and len(solution) == len(csp_reqs) and not unplaced

        if not all_placed and not save_partial:
            conflict_details = "; ".join(
                f"{u.get('class_name', '')} ({u.get('teacher_name', '')}): {u.get('reason', '')}"
                for u in (unplaced or [])[:3]
            )
            detail_suffix = f" Sabablar: {conflict_details}" if conflict_details else ""
            return {
                "success": False,
                "status": "failed",
                "message": (
                    f"{term}-chorak o'quv rejasidagi barcha darslarni "
                    f"({len(csp_reqs)} tadan {len(unplaced)} tasi joylashmadi) "
                    f"ziddiyatsiz joylashtirib bo'lmadi.{detail_suffix}"
                ),
                "total_lessons_scheduled": 0,
                "total_required": len(csp_reqs),
                "unplaced": unplaced,
                "term": term,
            }

        slots_to_save = solution or []
        if not slots_to_save:
            return {
                "success": False,
                "status": "failed",
                "message": f"{term}-chorak uchun birorta ham dars joylashtirib bo'lmadi.",
                "total_lessons_scheduled": 0,
                "total_required": len(csp_reqs),
                "unplaced": unplaced,
                "term": term,
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
            for slot in slots_to_save
        ]

        db.add_all(new_entries)
        await db.commit()

        if not all_placed:
            return {
                "success": False,
                "status": "partial",
                "message": f"{term}-chorak dars jadvali qisman tuzildi: {len(new_entries)}/{len(csp_reqs)} ta dars joylashtirildi, {len(unplaced)} ta dars joylashmadi.",
                "total_lessons_scheduled": len(new_entries),
                "total_required": len(csp_reqs),
                "unplaced": unplaced,
                "term": term,
            }

        return {
            "success": True,
            "status": "success",
            "message": f"{term}-chorak dars jadvali muvaffaqiyatli tuzildi! Jami {len(new_entries)} ta dars joylashtirildi.",
            "total_lessons_scheduled": len(new_entries),
            "total_required": len(csp_reqs),
            "unplaced": [],
            "term": term
        }

    @staticmethod
    async def execute_job_in_background(
        job_id: str,
        school_id: str,
        term: int = 1,
        slots_per_day: int = 6,
        save_partial: bool = False,
        solver_type: str = "cpsat",
    ) -> None:
        """
        Fon rejimida alohida jarayon (ProcessPoolExecutor) orqali jadvalni tuzadi
        va timetable_jobs jadvalini progress/natija bilan yangilaydi.
        """
        async with db_conn.AsyncSessionLocal() as db:
            @event.listens_for(db.sync_session, "after_begin")
            def _set_ctx(sync_sess, transaction, connection):
                connection.execute(
                    text(
                        "SELECT set_config('app.is_super_admin', 'off', true), "
                        "set_config('app.current_school_id', :sid, true)"
                    ),
                    {"sid": str(school_id)},
                )

            try:
                job = await db.get(TimetableJob, job_id)
                if not job:
                    return
                job.status = "running"
                job.progress = 15
                await db.commit()

                teachers_res = await db.execute(select(Teacher).where(Teacher.school_id == school_id))
                db_teachers = teachers_res.scalars().all()
                rooms_res = await db.execute(select(Room).where(Room.school_id == school_id))
                db_rooms = rooms_res.scalars().all()
                classes_res = await db.execute(select(SchoolClass).where(SchoolClass.school_id == school_id))
                db_classes = classes_res.scalars().all()
                subjects_res = await db.execute(select(Subject).where(Subject.school_id == school_id))
                db_subjects = subjects_res.scalars().all()
                alloc_res = await db.execute(
                    select(ClassSubjectAllocation).where(
                        ClassSubjectAllocation.school_id == school_id,
                        ClassSubjectAllocation.term == term,
                    )
                )
                db_allocations = alloc_res.scalars().all()

                if not db_allocations or not db_classes or not db_teachers or not db_rooms or not db_subjects:
                    job.status = "failed"
                    job.progress = 100
                    job.finished_at = datetime.now(timezone.utc)
                    job.result_json = {
                        "success": False,
                        "status": "failed",
                        "message": f"{term}-chorak uchun ma'lumotlar yetarli emas (fanlar, o'qituvchilar yoki xonalar kiritilmagan).",
                        "total_lessons_scheduled": 0,
                        "total_required": 0,
                        "unplaced": [],
                        "term": term,
                    }
                    await db.commit()
                    return

                csp_rooms = [CSPRoom(id=r.id, number=r.room_number, capacity=r.capacity, room_type=r.room_type) for r in db_rooms]
                csp_teachers = [
                    CSPTeacher(
                        id=t.id,
                        name=t.full_name,
                        max_weekly_hours=t.max_weekly_hours if t.max_weekly_hours is not None else 36,
                        max_daily_hours=t.max_daily_hours if t.max_daily_hours is not None else 6,
                        unavailable_slots=TimetableService._parse_unavailable_slots(getattr(t, "unavailable_slots", None)),
                    )
                    for t in db_teachers
                ]
                csp_classes = [CSPSchoolClass(id=c.id, name=c.name, student_count=c.student_count, shift=c.shift) for c in db_classes]
                csp_subjects = [
                    CSPSubject(id=s.id, name=s.name, short_code=s.short_code, color_hex=s.color_hex, required_room_type=s.required_room_type)
                    for s in db_subjects
                ]

                class_home_rooms: Dict[str, str] = {}
                for c in db_classes:
                    c_name_clean = c.name.strip().lower()
                    for r in db_rooms:
                        r_num_clean = r.room_number.strip().lower()
                        r_name_clean = (r.name or "").strip().lower()
                        if c_name_clean in r_num_clean or c_name_clean in r_name_clean or r_num_clean.startswith(c_name_clean):
                            class_home_rooms[c.id] = r.id
                            break

                # Qotirilgan (pinned) darslarni yuklaymiz — ular o'zgartirilmaydi
                pinned_res = await db.execute(
                    select(TimetableEntry).where(
                        TimetableEntry.school_id == school_id,
                        TimetableEntry.term == term,
                        TimetableEntry.is_pinned == True,
                    )
                )
                db_pinned = pinned_res.scalars().all()
                rooms_by_id = {r.id: r for r in csp_rooms}
                pinned_slots: List[ScheduledSlot] = []
                pinned_counts: Dict[Tuple[str, str], int] = {}
                for pe in db_pinned:
                    rm = rooms_by_id.get(pe.room_id)
                    if not rm:
                        continue
                    pinned_counts[(pe.class_id, pe.subject_id)] = pinned_counts.get((pe.class_id, pe.subject_id), 0) + 1
                    pinned_slots.append(
                        ScheduledSlot(
                            day=pe.day,
                            slot=pe.lesson_order,
                            lesson=CSPLessonReq(
                                id=f"pinned_{pe.id}",
                                class_id=pe.class_id,
                                subject_id=pe.subject_id,
                                teacher_id=pe.teacher_id or "",
                                preferred_room_id=pe.room_id,
                            ),
                            room=rm,
                        )
                    )

                csp_reqs: List[CSPLessonReq] = []
                for alloc in db_allocations:
                    subj = next((s for s in db_subjects if s.id == alloc.subject_id), None)
                    s_req_room = (subj.required_room_type or "GENERAL").upper() if subj else "GENERAL"
                    pref_room = alloc.preferred_room_id
                    if "LAB" not in s_req_room and "SPORT" not in s_req_room and "KOMP" not in s_req_room and "GYM" not in s_req_room:
                        pref_room = class_home_rooms.get(alloc.class_id, pref_room)

                    hours_to_schedule = int(round(alloc.weekly_hours)) if alloc.weekly_hours else 0
                    if alloc.weekly_hours and alloc.weekly_hours > 0 and hours_to_schedule == 0:
                        hours_to_schedule = 1
                    already_pinned = pinned_counts.get((alloc.class_id, alloc.subject_id), 0)
                    remaining_hours = max(0, hours_to_schedule - already_pinned)
                    for i in range(remaining_hours):
                        csp_reqs.append(
                            CSPLessonReq(
                                id=f"{alloc.id}_{i}",
                                class_id=alloc.class_id,
                                subject_id=alloc.subject_id,
                                teacher_id=alloc.teacher_id,
                                preferred_room_id=pref_room,
                                max_per_day=alloc.max_hours_per_day or 2,
                            )
                        )

                job.progress = 35
                await db.commit()

                loop = asyncio.get_running_loop()
                slots_payload, unplaced, all_placed = await loop.run_in_executor(
                    _process_pool,
                    _run_solver_in_process,
                    csp_classes,
                    csp_teachers,
                    csp_rooms,
                    csp_subjects,
                    csp_reqs,
                    slots_per_day,
                    save_partial,
                    solver_type,
                    pinned_slots,
                )

                job.progress = 85
                await db.commit()

                if not all_placed and not save_partial:
                    job.status = "failed"
                    job.progress = 100
                    job.finished_at = datetime.now(timezone.utc)
                    job.result_json = {
                        "success": False,
                        "status": "failed",
                        "message": f"{term}-chorak o'quv rejasidagi barcha darslarni ({len(csp_reqs)} tadan {len(unplaced)} tasi joylashmadi) ziddiyatsiz joylashtirib bo'lmadi.",
                        "total_lessons_scheduled": 0,
                        "total_required": len(csp_reqs),
                        "unplaced": unplaced,
                        "term": term,
                    }
                    await db.commit()
                    return

                if slots_payload or pinned_slots:
                    # Faqat qotirilmagan (is_pinned == False) darslarni o'chiramiz
                    await db.execute(
                        delete(TimetableEntry).where(
                            TimetableEntry.school_id == school_id,
                            TimetableEntry.term == term,
                            TimetableEntry.is_pinned == False,
                        )
                    )
                    db.add_all(
                        [
                            TimetableEntry(
                                school_id=school_id,
                                term=term,
                                day=item["day"],
                                lesson_order=item["slot"],
                                class_id=item["class_id"],
                                subject_id=item["subject_id"],
                                teacher_id=item["teacher_id"],
                                room_id=item["room_id"],
                            )
                            for item in slots_payload
                        ]
                    )

                job.status = "done" if all_placed else "failed"
                job.progress = 100
                job.finished_at = datetime.now(timezone.utc)
                job.result_json = {
                    "success": all_placed,
                    "status": "success" if all_placed else "partial",
                    "message": (
                        f"{term}-chorak dars jadvali muvaffaqiyatli tuzildi! Jami {len(slots_payload)} ta dars joylashtirildi."
                        if all_placed
                        else f"{term}-chorak jadvali qisman tuzildi: {len(slots_payload)}/{len(csp_reqs)} ta dars joylashtirildi, {len(unplaced)} ta dars joylashmadi."
                    ),
                    "total_lessons_scheduled": len(slots_payload),
                    "total_required": len(csp_reqs),
                    "unplaced": unplaced,
                    "term": term,
                }
                await db.commit()
            except Exception as exc:
                await db.rollback()
                job = await db.get(TimetableJob, job_id)
                if job:
                    job.status = "failed"
                    job.progress = 100
                    job.finished_at = datetime.now(timezone.utc)
                    job.result_json = {
                        "success": False,
                        "status": "failed",
                        "message": f"Generatsiya xatosi: {exc}",
                        "total_lessons_scheduled": 0,
                        "total_required": 0,
                        "unplaced": [],
                        "term": term,
                    }
                    await db.commit()
