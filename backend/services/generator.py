"""
Avtomatlashtirilgan Maktab Dars Jadvali Generatori (CSP Backtracking Solver)
Implements Hard & Soft Constraints, shift normalization, teacher & student workload caps,
gap elimination, specialized room matching, candidate grouping, randomized restart, and timeout.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set, Callable, Any
import time

# --- STANDARTLASHTIRISH VA NORMALIZATSIYA ---

def normalize_shift(shift: Optional[str]) -> str:
    """1-smena / 2-smena yoki MORNING / AFTERNOON nomlarini standartlashtiradi"""
    if not shift:
        return "MORNING"
    s = str(shift).upper().strip()
    if "1" in s or "MORNING" in s:
        return "MORNING"
    if "2" in s or "AFTERNOON" in s:
        return "AFTERNOON"
    return "MORNING"

ROOM_TYPE_MAP: Dict[str, str] = {
    "GENERAL": "GENERAL",
    "ODDIY XONA": "GENERAL",
    "ODDIY": "GENERAL",
    "LANGUAGE_LAB": "GENERAL",
    "COMPUTER_LAB": "COMPUTER_LAB",
    "KOMPYUTER XONASI": "COMPUTER_LAB",
    "KOMPYUTER": "COMPUTER_LAB",
    "IT-ZAL": "COMPUTER_LAB",
    "IT": "COMPUTER_LAB",
    "GYM": "GYM",
    "SPORT ZAL": "GYM",
    "SPORTZAL": "GYM",
    "SPORT": "GYM",
    "LABORATORY": "LABORATORY",
    "LABORATORIYA": "LABORATORY",
    "KIMYO LABORATORIYASI": "LABORATORY",
    "FIZIKA LABORATORIYASI": "LABORATORY",
    "BIOLOGIYA LABORATORIYASI": "LABORATORY",
}

def normalize_room_type(rt: Optional[str]) -> str:
    """Xona turlarini aniq xarita (map) orqali standart kodlarga normalashtiradi"""
    if not rt:
        return "GENERAL"
    u = str(rt).upper().strip()
    return ROOM_TYPE_MAP.get(u, "GENERAL")

# --- DATA MODELLAR ---

@dataclass(frozen=True)
class Room:
    id: str
    number: str
    capacity: int
    room_type: str = "GENERAL"

@dataclass(frozen=True)
class Teacher:
    id: str
    name: str
    max_weekly_hours: int = 36
    max_daily_hours: int = 6
    unavailable_slots: Set[Tuple[str, int]] = field(default_factory=set)

@dataclass(frozen=True)
class SchoolClass:
    id: str
    name: str
    student_count: int
    shift: str = "MORNING"

@dataclass(frozen=True)
class Subject:
    id: str
    name: str
    short_code: str
    color_hex: str = "#1E40AF"
    required_room_type: str = "GENERAL"

@dataclass
class LessonRequirement:
    id: str
    class_id: str
    subject_id: str
    teacher_id: str
    preferred_room_id: Optional[str] = None
    max_per_day: int = 1  # 1. Default qiymati 1 marta

@dataclass
class ScheduledSlot:
    day: str
    slot: int  # 1..6-soat
    lesson: LessonRequirement
    room: Room

# --- ASOSIY GENERATOR CSP KLASSI ---

class TimetableGeneratorCSP:
    DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"]

    def __init__(
        self,
        classes: List[SchoolClass],
        teachers: List[Teacher],
        rooms: List[Room],
        subjects: List[Subject],
        requirements: List[LessonRequirement],
        slots_per_day: int = 6,
        max_candidates: int = 50,
        timeout_seconds: float = 30.0,
        on_progress: Optional[Callable[[int, int], None]] = None
    ):
        self.classes = {c.id: c for c in classes}
        self.teachers = {t.id: t for t in teachers}
        self.rooms = {r.id: r for r in rooms}
        self.subjects = {s.id: s for s in subjects}
        self.requirements = requirements
        self.slots_per_day = slots_per_day
        self.max_candidates = max_candidates
        self.timeout_seconds = timeout_seconds
        self.on_progress = on_progress

        # O(1) Constraint checking set va dictionary'lar
        # (shift, day, slot, teacher_id) -> bandlik
        self.teacher_occupancy: Set[Tuple[str, str, int, str]] = set()
        # (shift, day, slot, room_id) -> bandlik
        self.room_occupancy: Set[Tuple[str, str, int, str]] = set()
        # (day, slot, class_id) -> bandlik
        self.class_occupancy: Set[Tuple[str, int, str]] = set()

        # O'qituvchi yuklamalari
        self.teacher_weekly_count: Dict[str, int] = {}
        self.teacher_daily_count: Dict[Tuple[str, str], int] = {}
        self.teacher_daily_slots: Dict[Tuple[str, str], List[int]] = {}

        # 2. Sinf (o'quvchilar) kunlik dars soatlarini kuzatish: (class_id, day) -> [slot1, slot2...]
        self.class_daily_slots: Dict[Tuple[str, str], List[int]] = {}

        # Sinfning kunlik fan soni: (class_id, day, subject_id) -> count
        self.daily_subject_count: Dict[Tuple[str, str, str], int] = {}

        # Natija: lesson_id -> ScheduledSlot
        self.assignments: Dict[str, ScheduledSlot] = {}
        self.unplaced: List[Dict[str, Any]] = []
        self.start_time: float = 0.0
        self.is_timed_out: bool = False

    def is_hard_valid(
        self,
        lesson: LessonRequirement,
        day: str,
        slot: int,
        room: Room,
        max_per_day: int = 1
    ) -> bool:
        """
        Barcha qat'iy cheklovlarni (Hard Constraints) tekshiradi.
        1. max_per_day parametri orqali dinamik tekshiruv.
        3. Maxsus xonalar ixtisoslashuvi qat'iy nazorati.
        """
        target_class = self.classes[lesson.class_id]
        shift = normalize_shift(target_class.shift)

        # 1. O'qituvchi shu smenada, shu kuni va shu soatda band emasmi?
        if lesson.teacher_id and (shift, day, slot, lesson.teacher_id) in self.teacher_occupancy:
            return False

        # 2. O'qituvchining maxsus bo'sh bo'lmagan soatlari va limitlari
        if lesson.teacher_id:
            teacher = self.teachers.get(lesson.teacher_id)
            if teacher:
                if (day, slot) in teacher.unavailable_slots:
                    return False

                # a) O'qituvchining kunlik maksimal soat limiti
                cur_daily_hours = self.teacher_daily_count.get((lesson.teacher_id, day), 0)
                if cur_daily_hours >= teacher.max_daily_hours:
                    return False

                # b) O'qituvchining haftalik maksimal soat limiti
                cur_weekly_hours = self.teacher_weekly_count.get(lesson.teacher_id, 0)
                if cur_weekly_hours >= teacher.max_weekly_hours:
                    return False

        # 3. Sinf shu vaqtda boshqa darsda emasmi?
        if (day, slot, lesson.class_id) in self.class_occupancy:
            return False

        # 4. Xona shu smenada va soatda band emasmi?
        if (shift, day, slot, room.id) in self.room_occupancy:
            return False

        # 5. Xona sig'imi tekshiruvi (8 o'quvchi xatolik toleransi bilan)
        if room.capacity < (target_class.student_count - 8):
            return False

        # 6. Maxsus xonalar ixtisoslashuvi
        subject = self.subjects[lesson.subject_id]
        req_type = normalize_room_type(subject.required_room_type)
        r_type = normalize_room_type(room.room_type)

        # Maxsus xona talab qiladigan fanlar (COMPUTER_LAB, GYM, LABORATORY) faqat o'z xonasiga qo'yilsin
        # (boshqa maxsus xonaga yoki oddiy xonaga mutlaqo qo'yilmasin)
        if req_type in ("COMPUTER_LAB", "GYM", "LABORATORY"):
            if r_type != req_type:
                return False
        elif req_type == "GENERAL":
            # Oddiy fanlar IT-zal yoki Sport zalga kiritilmasligi kerak
            if r_type in ("COMPUTER_LAB", "GYM"):
                return False
            # Asosiy darslar o'zining sinf xonasida (preferred_room_id) bo'lishi shart
            if lesson.preferred_room_id and room.id != lesson.preferred_room_id:
                return False

        # 7. Sinf uchun fanning kunlik dars soati limiti (dinamik max_per_day tekshiruvi)
        cur_sub_count = self.daily_subject_count.get((lesson.class_id, day, lesson.subject_id), 0)
        if cur_sub_count >= max_per_day:
            return False

        return True

    def calculate_slot_penalty(self, lesson: LessonRequirement, day: str, slot: int, room: Room) -> int:
        """
        Yumshoq cheklovlar (Soft constraints) jarima ballini hisoblash:
        - Fan takrori jarimasi (+50)
        - Sinf oyna jarimasi (+100) va 1-soatdan boshlash bonusi (-20)
        - Xona afzalligi bonusi (-20)
        - O'qituvchi derazasini kamaytirish bonusi (-8)
        """
        penalty = 0
        subject = self.subjects[lesson.subject_id]
        req_type = normalize_room_type(subject.required_room_type)
        r_type = normalize_room_type(room.room_type)

        # Preference 1: Agar shu kunda fanning takrori bo'lsa, katta jarima (+50)
        cur_sub_count = self.daily_subject_count.get((lesson.class_id, day, lesson.subject_id), 0)
        if cur_sub_count > 0:
            penalty += 50

        # Preference 2: Sinf (o'quvchilar) uchun "oyna" (bo'sh soat) bo'lmasligi va 1-soatdan boshlanishi
        c_day_key = (lesson.class_id, day)
        existing_class_slots = self.class_daily_slots.get(c_day_key, [])
        if existing_class_slots:
            min_cs = min(existing_class_slots)
            max_cs = max(existing_class_slots)
            if slot == min_cs - 1 or slot == max_cs + 1:
                penalty -= 25  # Ketma-ket, uzilishlarsiz dars bonusi
            elif slot < min_cs - 1 or slot > max_cs + 1:
                penalty += 100  # Sinf uchun oyna (bo'sh soat) qoldirishga qat'iy jarima!
        else:
            # Ushbu kunda sinfning birinchi darsi: 1-soatdan boshlanishi kerak
            if slot == 1:
                penalty -= 20
            else:
                penalty += 35 * (slot - 1)  # 1-soatni tashlab 2, 3... soatdan boshlashga jarima

        # Preference 3: O'qituvchi darslari orasidagi darcha (oyna)larni qisqartirish
        if lesson.teacher_id:
            existing_teacher_slots = self.teacher_daily_slots.get((lesson.teacher_id, day), [])
            if existing_teacher_slots:
                min_ts = min(existing_teacher_slots)
                max_ts = max(existing_teacher_slots)
                if slot < min_ts - 1 or slot > max_ts + 1:
                    penalty += 10
                else:
                    penalty -= 8

        # Preference 4: Xona ixtisoslashuvi va preferred_room_id
        if req_type == "GENERAL" and r_type != "GENERAL":
            penalty += 80  # Oddiy fan maxsus xonani egallamasligi uchun katta jarima

        if lesson.preferred_room_id:
            if room.id == lesson.preferred_room_id:
                penalty -= 20  # Biriktirilgan xonaga tushsa sezilarli bonus
            else:
                penalty += 15

        # Preference 5: Og'ir akademik fanlarni 1-4 soatlarga joylashtirish
        if slot > 4 and subject.short_code in ["MAT", "FIZ", "KIM"]:
            penalty += 5

        # Preference 6: Kunlik darslar muvozanati (har kunga teng taqsimlash, haftaning barcha kunlariga dars qo'yish)
        cur_day_count = len(existing_class_slots)
        if cur_day_count >= 5:
            penalty += 45 * (cur_day_count - 4)  # 5 yoki 6-dars bo'lsa boshqa bo'sh kunlarga ustunlik berish
        elif cur_day_count == 0:
            penalty -= 20  # Hali darsi yo'q bo'sh kunlarga dars qo'yishni kuchli rag'batlantirish

        return penalty

    def assign(self, lesson: LessonRequirement, day: str, slot: int, room: Room):
        """Darsni tanlangan vaqt va xonaga tayinlash"""
        target_class = self.classes[lesson.class_id]
        shift = normalize_shift(target_class.shift)

        if lesson.teacher_id:
            self.teacher_occupancy.add((shift, day, slot, lesson.teacher_id))
            self.teacher_weekly_count[lesson.teacher_id] = self.teacher_weekly_count.get(lesson.teacher_id, 0) + 1
            t_day_key = (lesson.teacher_id, day)
            self.teacher_daily_count[t_day_key] = self.teacher_daily_count.get(t_day_key, 0) + 1
            self.teacher_daily_slots.setdefault(t_day_key, []).append(slot)

        self.room_occupancy.add((shift, day, slot, room.id))
        self.class_occupancy.add((day, slot, lesson.class_id))

        # Sinf kunlik slotlarini yozish
        c_day_key = (lesson.class_id, day)
        self.class_daily_slots.setdefault(c_day_key, []).append(slot)

        sub_key = (lesson.class_id, day, lesson.subject_id)
        self.daily_subject_count[sub_key] = self.daily_subject_count.get(sub_key, 0) + 1

        self.assignments[lesson.id] = ScheduledSlot(day=day, slot=slot, lesson=lesson, room=room)

        if self.on_progress:
            self.on_progress(len(self.assignments), len(self.requirements))

    def unassign(self, lesson: LessonRequirement, day: str, slot: int, room: Room):
        """Orqaga qaytish (Backtrack) paytida barcha bandlikni to'g'ri tozalash"""
        target_class = self.classes[lesson.class_id]
        shift = normalize_shift(target_class.shift)

        if lesson.teacher_id:
            self.teacher_occupancy.remove((shift, day, slot, lesson.teacher_id))
            self.teacher_weekly_count[lesson.teacher_id] -= 1
            t_day_key = (lesson.teacher_id, day)
            self.teacher_daily_count[t_day_key] -= 1
            self.teacher_daily_slots[t_day_key].remove(slot)

        self.room_occupancy.remove((shift, day, slot, room.id))
        self.class_occupancy.remove((day, slot, lesson.class_id))

        # Sinf kunlik slotlarini tozalash
        c_day_key = (lesson.class_id, day)
        if c_day_key in self.class_daily_slots:
            self.class_daily_slots[c_day_key].remove(slot)
            if not self.class_daily_slots[c_day_key]:
                del self.class_daily_slots[c_day_key]

        sub_key = (lesson.class_id, day, lesson.subject_id)
        self.daily_subject_count[sub_key] -= 1
        if self.daily_subject_count[sub_key] == 0:
            del self.daily_subject_count[sub_key]

        del self.assignments[lesson.id]

    def reset_state(self):
        """Urinishlar orasida barcha tuzilmalarni to'liq tozalash"""
        self.teacher_occupancy.clear()
        self.room_occupancy.clear()
        self.class_occupancy.clear()
        self.teacher_weekly_count.clear()
        self.teacher_daily_count.clear()
        self.teacher_daily_slots.clear()
        self.class_daily_slots.clear()
        self.daily_subject_count.clear()
        self.assignments.clear()
        self.unplaced.clear()

    def _build_unplaced_entry(self, lesson: LessonRequirement, reason: str) -> Dict[str, Any]:
        cls_obj = self.classes.get(lesson.class_id)
        subj_obj = self.subjects.get(lesson.subject_id)
        teacher_obj = self.teachers.get(lesson.teacher_id) if lesson.teacher_id else None
        return {
            "lesson_id": lesson.id,
            "class_id": lesson.class_id,
            "class_name": cls_obj.name if cls_obj else lesson.class_id,
            "subject_id": lesson.subject_id,
            "subject_name": subj_obj.name if subj_obj else lesson.subject_id,
            "teacher_id": lesson.teacher_id,
            "teacher_name": teacher_obj.name if teacher_obj else None,
            "reason": reason,
        }

    def _get_candidate_rooms(self, lesson: LessonRequirement) -> List[Room]:
        subject = self.subjects[lesson.subject_id]
        req_type = normalize_room_type(subject.required_room_type)
        if req_type in ("COMPUTER_LAB", "GYM", "LABORATORY"):
            return [r for r in self.rooms.values() if normalize_room_type(r.room_type) == req_type]
        if lesson.preferred_room_id and lesson.preferred_room_id in self.rooms:
            return [self.rooms[lesson.preferred_room_id]]
        return list(self.rooms.values())

    def _run_solver(self) -> Tuple[List[ScheduledSlot], List[Dict[str, Any]]]:
        """
        Qat'iy ziddiyatsiz dars jadvali generatsiyasi:
        Hech qanday holatda o'qituvchi, xona, sinf to'qnashuvi yoki cheklov buzilishiga yo'l qo'ymaydi.
        Joylashmagan darslar sabablari bilan unplaced ro'yxatiga yoziladi.
        """
        from collections import defaultdict

        self.reset_state()
        self.start_time = time.time()
        self.is_timed_out = False

        class_reqs = defaultdict(list)
        for r in self.requirements:
            class_reqs[r.class_id].append(r)

        for class_id, reqs in class_reqs.items():
            if self.is_timed_out:
                for lesson in reqs:
                    if lesson.id not in self.assignments:
                        self.unplaced.append(self._build_unplaced_entry(lesson, "Algoritm vaqt limiti (timeout) tugadi"))
                continue

            sub_counts = defaultdict(int)
            for r in reqs:
                sub_counts[r.subject_id] += 1

            reqs.sort(
                key=lambda r: (
                    0 if normalize_room_type(self.subjects[r.subject_id].required_room_type) != "GENERAL" else 1,
                    -sub_counts[r.subject_id]
                )
            )

            # Avval max_per_day=1 bilan urinib ko'ramiz; agar imkonsiz bo'lsa sinf holatini tozalab max_per_day=2 bilan urinamiz
            assigned_before = set(self.assignments.keys())
            success = self._backtrack_class(reqs, 0, max_per_day=1)
            if not success and not self.is_timed_out:
                for r in reqs:
                    if r.id in self.assignments and r.id not in assigned_before:
                        s = self.assignments[r.id]
                        self.unassign(r, s.day, s.slot, s.room)
                success = self._backtrack_class(reqs, 0, max_per_day=2)

            # Qat'iy fallback: faqat is_hard_valid == True bo'lgan bo'sh slotlarga joylashtirish (to'qnashuv TAQIQLANADI)
            unassigned = [r for r in reqs if r.id not in self.assignments]
            for lesson in unassigned:
                if (time.time() - self.start_time) > self.timeout_seconds:
                    self.is_timed_out = True
                    self.unplaced.append(self._build_unplaced_entry(lesson, "Algoritm vaqt limiti (timeout) tugadi"))
                    continue

                rooms = self._get_candidate_rooms(lesson)
                best_slot = None
                best_penalty = float("inf")
                best_room = None
                effective_max_per_day = max(lesson.max_per_day, 2)

                c_day_len = lambda d: len(self.class_daily_slots.get((class_id, d), []))
                sorted_days = sorted(self.DAYS, key=c_day_len)

                for day in sorted_days:
                    for slot in range(1, self.slots_per_day + 1):
                        for room in rooms:
                            if self.is_hard_valid(lesson, day, slot, room, max_per_day=effective_max_per_day):
                                p = c_day_len(day) * 30 + self.calculate_slot_penalty(lesson, day, slot, room)
                                if p < best_penalty:
                                    best_penalty = p
                                    best_slot = (day, slot)
                                    best_room = room

                if best_slot and best_room:
                    self.assign(lesson, best_slot[0], best_slot[1], best_room)
                else:
                    self.unplaced.append(
                        self._build_unplaced_entry(
                            lesson,
                            "O'qituvchi, xona yoki soat cheklovlari sababli ziddiyatsiz joy topilmadi"
                        )
                    )

        return list(self.assignments.values()), list(self.unplaced)

    def solve(self) -> Optional[List[ScheduledSlot]]:
        """
        Faqat 100% darslar ziddiyatsiz joylashganda yechim qaytaradi; aks holda None.
        Joylashmagan darslar self.unplaced da saqlanadi.
        """
        slots, unplaced = self._run_solver()
        if unplaced or len(slots) != len(self.requirements) or self.is_timed_out:
            return None
        return slots

    def solve_partial(self) -> Tuple[List[ScheduledSlot], List[Dict[str, Any]]]:
        """
        Ziddiyatsiz joylashgan darslar va joylashmagan darslar ro'yxatini qaytaradi.
        """
        return self._run_solver()

    def _backtrack_class(self, req_list: List[LessonRequirement], index: int, max_per_day: int = 1) -> bool:
        """
        Rekursiv Backtracking funksiyasi.
        4. Har bir (day, slot) juftligi uchun faqat 1 ta eng mos xona tanlanadi.
        5. Timeout bo'lganda False qaytaradi.
        """
        # 5. Timeout tekshiruvi: vaqt tugasa False qaytaradi
        if (time.time() - self.start_time) > self.timeout_seconds:
            self.is_timed_out = True
            return False

        if index >= len(req_list):
            return True

        lesson = req_list[index]

        # 4. Har bir (day, slot) juftligi uchun mos xonalarni tekshiramiz
        subject = self.subjects[lesson.subject_id]
        req_type = normalize_room_type(subject.required_room_type)
        if lesson.preferred_room_id and lesson.preferred_room_id in self.rooms:
            rooms_to_check = [self.rooms[lesson.preferred_room_id]]
        elif req_type in ("COMPUTER_LAB", "GYM", "LABORATORY"):
            rooms_to_check = [r for r in self.rooms.values() if normalize_room_type(r.room_type) == req_type]
            if not rooms_to_check:
                rooms_to_check = list(self.rooms.values())
        else:
            rooms_to_check = list(self.rooms.values())

        # Kunlarni sinfda darslar soni kamligiga qarab saralash (teng taqsimlash uchun)
        c_day_len = lambda d: len(self.class_daily_slots.get((lesson.class_id, d), []))
        sorted_days = sorted(self.DAYS, key=c_day_len)

        slot_candidates: List[Tuple[int, str, int, Room]] = []
        for day in sorted_days:
            for slot in range(1, self.slots_per_day + 1):
                best_room: Optional[Room] = None
                min_penalty = float("inf")

                for room in rooms_to_check:
                    if self.is_hard_valid(lesson, day, slot, room, max_per_day):
                        penalty = self.calculate_slot_penalty(lesson, day, slot, room)
                        if penalty < min_penalty:
                            min_penalty = penalty
                            best_room = room

                if best_room is not None:
                    slot_candidates.append((min_penalty, day, slot, best_room))

        # 4. Nomzodlarni eng kam jarima balli bo'yicha saralash
        slot_candidates.sort(key=lambda x: x[0])

        # 4. Saralangan nomzodlardan max_candidates (30) tasini sinab ko'rish
        for penalty, day, slot, room in slot_candidates[:self.max_candidates]:
            if self.is_timed_out:
                return False

            self.assign(lesson, day, slot, room)
            if self._backtrack_class(req_list, index + 1, max_per_day):
                return True
            self.unassign(lesson, day, slot, room)

        return False
