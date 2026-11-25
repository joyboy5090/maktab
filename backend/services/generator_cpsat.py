"""
Google OR-Tools CP-SAT asosidagi Maktab Dars Jadvali Generatori.
Barcha sinflar, o'qituvchilar va xonalar bo'yicha global optimallashtirishni amalga oshiradi.
"""
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Any
from ortools.sat.python import cp_model

from services.generator import (
    Room,
    Teacher,
    SchoolClass,
    Subject,
    LessonRequirement,
    ScheduledSlot,
    normalize_shift,
    normalize_room_type,
)


class TimetableGeneratorCPSAT:
    DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"]

    def __init__(
        self,
        classes: List[SchoolClass],
        teachers: List[Teacher],
        rooms: List[Room],
        subjects: List[Subject],
        requirements: List[LessonRequirement],
        slots_per_day: int = 6,
        max_time_in_seconds: float = 30.0,
        timeout_seconds: Optional[float] = None,
        pinned_slots: Optional[List[ScheduledSlot]] = None,
    ):
        self.classes = {c.id: c for c in classes}
        self.teachers = {t.id: t for t in teachers}
        self.rooms = {r.id: r for r in rooms}
        self.subjects = {s.id: s for s in subjects}
        self.requirements = requirements
        self.slots_per_day = slots_per_day
        self.max_time_in_seconds = timeout_seconds if timeout_seconds is not None else max_time_in_seconds
        self.pinned_slots = pinned_slots or []
        self.unplaced: List[Dict[str, Any]] = []
        self.diagnostics: List[str] = []

    def _valid_rooms_for_lesson(self, lesson: LessonRequirement) -> List[Room]:
        target_class = self.classes[lesson.class_id]
        subject = self.subjects[lesson.subject_id]
        req_type = normalize_room_type(subject.required_room_type)

        valid_rooms: List[Room] = []
        for room in self.rooms.values():
            if room.capacity < (target_class.student_count - 8):
                continue
            r_type = normalize_room_type(room.room_type)
            if req_type in ("COMPUTER_LAB", "GYM", "LABORATORY"):
                if r_type != req_type:
                    continue
            elif req_type == "GENERAL":
                if r_type in ("COMPUTER_LAB", "GYM"):
                    continue
                if lesson.preferred_room_id and room.id != lesson.preferred_room_id:
                    continue
            valid_rooms.append(room)
        return valid_rooms

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

    def _diagnose_infeasibility(self) -> List[str]:
        """Infeasible holatda ehtimoliy ziddiyat sabablarini aniqlaydi."""
        issues: List[str] = []

        # 1. O'qituvchi haftalik va kunlik limitlari tekshiruvi
        teacher_req_count: Dict[str, int] = defaultdict(int)
        teacher_shift_count: Dict[Tuple[str, str], int] = defaultdict(int)
        for req in self.requirements:
            if req.teacher_id:
                teacher_req_count[req.teacher_id] += 1
                sh = normalize_shift(self.classes[req.class_id].shift)
                teacher_shift_count[(req.teacher_id, sh)] += 1

        total_weekly_slots = len(self.DAYS) * self.slots_per_day
        for tid, count in teacher_req_count.items():
            t = self.teachers.get(tid)
            if not t:
                continue
            if count > t.max_weekly_hours:
                issues.append(
                    f"O'qituvchi {t.name}: talab qilingan soat ({count}) > max_weekly_hours ({t.max_weekly_hours})"
                )
            max_by_daily = len(self.DAYS) * t.max_daily_hours
            if count > max_by_daily:
                issues.append(
                    f"O'qituvchi {t.name}: talab qilingan soat ({count}) > kunlik limit jami ({max_by_daily})"
                )
            avail_slots = total_weekly_slots - len(t.unavailable_slots)
            for (t_id, sh), sh_count in teacher_shift_count.items():
                if t_id == tid and sh_count > avail_slots:
                    issues.append(
                        f"O'qituvchi {t.name} ({sh}): talab qilingan soat ({sh_count}) > bo'sh vaqtlar ({avail_slots})"
                    )

        # 2. Sinf haftalik soat sig'imi
        class_req_count: Dict[str, int] = defaultdict(int)
        class_sub_count: Dict[Tuple[str, str], int] = defaultdict(int)
        class_sub_max: Dict[Tuple[str, str], int] = defaultdict(lambda: 1)
        for req in self.requirements:
            class_req_count[req.class_id] += 1
            key = (req.class_id, req.subject_id)
            class_sub_count[key] += 1
            class_sub_max[key] = max(class_sub_max[key], req.max_per_day)

        for cid, count in class_req_count.items():
            if count > total_weekly_slots:
                cname = self.classes[cid].name
                issues.append(f"Sinf {cname}: haftalik soat ({count}) > mavjud slotlar ({total_weekly_slots})")

        for (cid, sid), count in class_sub_count.items():
            max_sub_week = len(self.DAYS) * class_sub_max[(cid, sid)]
            if count > max_sub_week:
                cname = self.classes[cid].name
                sname = self.subjects[sid].name
                issues.append(
                    f"Sinf {cname}, fan {sname}: haftalik soat ({count}) > kunlik max * 6 ({max_sub_week})"
                )

        # 3. Maxsus xonalar sig'imi (smena bo'yicha)
        room_type_count: Dict[str, int] = defaultdict(int)
        for r in self.rooms.values():
            room_type_count[normalize_room_type(r.room_type)] += 1

        req_type_shift: Dict[Tuple[str, str], int] = defaultdict(int)
        for req in self.requirements:
            rt = normalize_room_type(self.subjects[req.subject_id].required_room_type)
            if rt in ("COMPUTER_LAB", "GYM", "LABORATORY"):
                sh = normalize_shift(self.classes[req.class_id].shift)
                req_type_shift[(rt, sh)] += 1

        for (rt, sh), cnt in req_type_shift.items():
            cap = room_type_count[rt] * total_weekly_slots
            if cnt > cap:
                issues.append(
                    f"Maxsus xona ({rt}, {sh}): talab qilingan dars ({cnt}) > mavjud xona-soat ({cap})"
                )

        if not issues:
            issues.append("Global ziddiyat: o'qituvchi, sinf va xonalar kesishuvi sababli yechim topilmadi")
        return issues

    def _solve_internal(self, allow_partial: bool = False) -> Tuple[List[ScheduledSlot], List[Dict[str, Any]]]:
        self.unplaced = []
        self.diagnostics = []

        if not self.requirements:
            return [], []

        model = cp_model.CpModel()

        # Indekslangan o'zgaruvchilar
        # x[(l_idx, d_idx, slot, r_id)] -> BoolVar
        x: Dict[Tuple[int, int, int, str], cp_model.IntVar] = {}
        lesson_vars: Dict[int, List[cp_model.IntVar]] = defaultdict(list)
        class_day_slot_vars: Dict[Tuple[str, int, int], List[cp_model.IntVar]] = defaultdict(list)
        class_day_vars: Dict[Tuple[str, int], List[cp_model.IntVar]] = defaultdict(list)
        class_sub_day_vars: Dict[Tuple[str, str, int], List[cp_model.IntVar]] = defaultdict(list)
        teacher_shift_day_slot_vars: Dict[Tuple[str, str, int, int], List[cp_model.IntVar]] = defaultdict(list)
        teacher_day_vars: Dict[Tuple[str, int], List[cp_model.IntVar]] = defaultdict(list)
        teacher_all_vars: Dict[str, List[cp_model.IntVar]] = defaultdict(list)
        room_shift_day_slot_vars: Dict[Tuple[str, str, int, int], List[cp_model.IntVar]] = defaultdict(list)

        class_sub_max_per_day: Dict[Tuple[str, str], int] = defaultdict(lambda: 1)
        class_total_reqs: Dict[str, int] = defaultdict(int)
        impossible_lessons: Set[int] = set()

        # Qotirilgan (pinned) darslar bandligini oldindan hisobga olamiz
        pinned_class_day_slot: Set[Tuple[str, int, int]] = set()
        pinned_teacher_shift_day_slot: Set[Tuple[str, str, int, int]] = set()
        pinned_room_shift_day_slot: Set[Tuple[str, str, int, int]] = set()
        pinned_teacher_day_count: Dict[Tuple[str, int], int] = defaultdict(int)
        pinned_teacher_weekly_count: Dict[str, int] = defaultdict(int)
        pinned_class_sub_day_count: Dict[Tuple[str, str, int], int] = defaultdict(int)

        day_to_idx = {d: i for i, d in enumerate(self.DAYS)}
        for ps in self.pinned_slots:
            d_idx = day_to_idx.get(ps.day)
            if d_idx is None:
                continue
            cls_obj = self.classes.get(ps.lesson.class_id)
            sh = normalize_shift(cls_obj.shift if cls_obj else None)
            pinned_class_day_slot.add((ps.lesson.class_id, d_idx, ps.slot))
            pinned_room_shift_day_slot.add((ps.room.id, sh, d_idx, ps.slot))
            pinned_class_sub_day_count[(ps.lesson.class_id, ps.lesson.subject_id, d_idx)] += 1
            if ps.lesson.teacher_id:
                pinned_teacher_shift_day_slot.add((ps.lesson.teacher_id, sh, d_idx, ps.slot))
                pinned_teacher_day_count[(ps.lesson.teacher_id, d_idx)] += 1
                pinned_teacher_weekly_count[ps.lesson.teacher_id] += 1

        for l_idx, lesson in enumerate(self.requirements):
            target_class = self.classes[lesson.class_id]
            shift = normalize_shift(target_class.shift)
            class_total_reqs[lesson.class_id] += 1
            cs_key = (lesson.class_id, lesson.subject_id)
            class_sub_max_per_day[cs_key] = max(class_sub_max_per_day[cs_key], lesson.max_per_day)

            teacher = self.teachers.get(lesson.teacher_id) if lesson.teacher_id else None
            valid_rooms = self._valid_rooms_for_lesson(lesson)
            if not valid_rooms:
                impossible_lessons.add(l_idx)
                continue

            for d_idx, day in enumerate(self.DAYS):
                for slot in range(1, self.slots_per_day + 1):
                    if (lesson.class_id, d_idx, slot) in pinned_class_day_slot:
                        continue
                    if teacher and (day, slot) in teacher.unavailable_slots:
                        continue
                    if lesson.teacher_id and (lesson.teacher_id, shift, d_idx, slot) in pinned_teacher_shift_day_slot:
                        continue
                    for room in valid_rooms:
                        if (room.id, shift, d_idx, slot) in pinned_room_shift_day_slot:
                            continue
                        var = model.new_bool_var(f"x_{l_idx}_{d_idx}_{slot}_{room.id}")
                        x[(l_idx, d_idx, slot, room.id)] = var
                        lesson_vars[l_idx].append(var)
                        class_day_slot_vars[(lesson.class_id, d_idx, slot)].append(var)
                        class_day_vars[(lesson.class_id, d_idx)].append(var)
                        class_sub_day_vars[(lesson.class_id, lesson.subject_id, d_idx)].append(var)
                        room_shift_day_slot_vars[(room.id, shift, d_idx, slot)].append(var)
                        if lesson.teacher_id:
                            teacher_shift_day_slot_vars[(lesson.teacher_id, shift, d_idx, slot)].append(var)
                            teacher_day_vars[(lesson.teacher_id, d_idx)].append(var)
                            teacher_all_vars[lesson.teacher_id].append(var)

            if not lesson_vars[l_idx]:
                impossible_lessons.add(l_idx)

        if impossible_lessons and not allow_partial:
            self.diagnostics = self._diagnose_infeasibility()
            reason = self.diagnostics[0] if self.diagnostics else "Mos xona yoki bo'sh vaqt topilmadi"
            self.unplaced = [self._build_unplaced_entry(self.requirements[i], reason) for i in impossible_lessons]
            return [], self.unplaced

        # 1. Hard constraints: Har dars bir marta (yoki partial rejimda <= 1)
        placed_vars: List[cp_model.IntVar] = []
        for l_idx, lesson in enumerate(self.requirements):
            vlist = lesson_vars[l_idx]
            if not vlist:
                continue
            if allow_partial:
                p_var = model.new_bool_var(f"placed_{l_idx}")
                model.add(sum(vlist) == p_var)
                placed_vars.append(p_var)
            else:
                model.add_exactly_one(vlist)

        # 2. Sinf bir vaqtda bitta dars
        for vlist in class_day_slot_vars.values():
            if len(vlist) > 1:
                model.add_at_most_one(vlist)

        # 3. O'qituvchi bir smenada bir vaqtda bitta dars
        for vlist in teacher_shift_day_slot_vars.values():
            if len(vlist) > 1:
                model.add_at_most_one(vlist)

        # 4. Xona bir smenada bir vaqtda bitta dars
        for vlist in room_shift_day_slot_vars.values():
            if len(vlist) > 1:
                model.add_at_most_one(vlist)

        # 5. O'qituvchi kunlik va haftalik limitlari (qotirilgan darslar hisobga olingan)
        for (tid, d_idx), vlist in teacher_day_vars.items():
            teacher = self.teachers.get(tid)
            if teacher:
                rem_daily = max(0, teacher.max_daily_hours - pinned_teacher_day_count[(tid, d_idx)])
                if len(vlist) > rem_daily:
                    model.add(sum(vlist) <= rem_daily)

        for tid, vlist in teacher_all_vars.items():
            teacher = self.teachers.get(tid)
            if teacher:
                rem_weekly = max(0, teacher.max_weekly_hours - pinned_teacher_weekly_count[tid])
                if len(vlist) > rem_weekly:
                    model.add(sum(vlist) <= rem_weekly)

        # 6. Fan bo'yicha kuniga max soat (qotirilgan darslar hisobga olingan)
        for (cid, sid, d_idx), vlist in class_sub_day_vars.items():
            max_pd = max(0, class_sub_max_per_day[(cid, sid)] - pinned_class_sub_day_count[(cid, sid, d_idx)])
            if len(vlist) > max_pd:
                model.add(sum(vlist) <= max_pd)

        # --- SOFT CONSTRAINTS (Maqsad funksiyasi) ---
        penalty_terms = []

        # A) Sinf darsi 1-soatdan boshlanishi va oynalar bo'lmasligi (vazn: 100)
        c_active: Dict[Tuple[str, int, int], cp_model.IntVar] = {}
        for cid in self.classes:
            for d_idx in range(len(self.DAYS)):
                for slot in range(1, self.slots_per_day + 1):
                    vlist = class_day_slot_vars.get((cid, d_idx, slot), [])
                    if vlist:
                        act = model.new_bool_var(f"ca_{cid}_{d_idx}_{slot}")
                        model.add(sum(vlist) == act)
                        c_active[(cid, d_idx, slot)] = act
                    else:
                        c_active[(cid, d_idx, slot)] = None  # type: ignore

                for slot in range(2, self.slots_per_day + 1):
                    cur_a = c_active[(cid, d_idx, slot)]
                    prev_a = c_active[(cid, d_idx, slot - 1)]
                    if cur_a is not None:
                        if prev_a is None:
                            penalty_terms.append(100 * cur_a)
                        else:
                            gap_var = model.new_bool_var(f"cgap_{cid}_{d_idx}_{slot}")
                            model.add(gap_var >= cur_a - prev_a)
                            penalty_terms.append(100 * gap_var)

        # B) Kunlar bo'yicha teng taqsimot (vazn: 40)
        num_days = len(self.DAYS)
        for cid, total_req in class_total_reqs.items():
            target_ceil = math.ceil(total_req / num_days)
            target_floor = total_req // num_days
            for d_idx in range(num_days):
                vlist = class_day_vars.get((cid, d_idx), [])
                if not vlist:
                    continue
                day_sum = sum(vlist)
                excess = model.new_int_var(0, self.slots_per_day, f"exc_{cid}_{d_idx}")
                deficit = model.new_int_var(0, self.slots_per_day, f"def_{cid}_{d_idx}")
                model.add(excess >= day_sum - target_ceil)
                model.add(deficit >= target_floor - day_sum)
                penalty_terms.append(40 * excess)
                penalty_terms.append(40 * deficit)

        # C) O'qituvchi oynalarini minimallashtirish (vazn: 15)
        teacher_shifts: Set[Tuple[str, str]] = {(tid, sh) for (tid, sh, _, _) in teacher_shift_day_slot_vars.keys()}
        for tid, sh in teacher_shifts:
            for d_idx in range(num_days):
                t_act: Dict[int, Optional[cp_model.IntVar]] = {}
                for slot in range(1, self.slots_per_day + 1):
                    vlist = teacher_shift_day_slot_vars.get((tid, sh, d_idx, slot), [])
                    if vlist:
                        ta = model.new_bool_var(f"ta_{tid}_{sh}_{d_idx}_{slot}")
                        model.add(sum(vlist) == ta)
                        t_act[slot] = ta
                    else:
                        t_act[slot] = None

                for slot in range(2, self.slots_per_day):
                    cur_t = t_act[slot]
                    prev_t = t_act[slot - 1]
                    next_t = t_act[slot + 1]
                    if prev_t is not None and next_t is not None:
                        if cur_t is None:
                            tgap = model.new_bool_var(f"tgap_{tid}_{sh}_{d_idx}_{slot}")
                            model.add(tgap >= prev_t + next_t - 1)
                            penalty_terms.append(15 * tgap)
                        else:
                            tgap = model.new_bool_var(f"tgap_{tid}_{sh}_{d_idx}_{slot}")
                            model.add(tgap >= prev_t + next_t - cur_t - 1)
                            penalty_terms.append(15 * tgap)

        # D) Bir kunda ayni fan takrorlanishini minimallashtirish (vazn: 50)
        for (cid, sid, d_idx), vlist in class_sub_day_vars.items():
            if len(vlist) > 1 and class_sub_max_per_day[(cid, sid)] > 1:
                rep = model.new_int_var(0, self.slots_per_day, f"rep_{cid}_{sid}_{d_idx}")
                model.add(rep >= sum(vlist) - 1)
                penalty_terms.append(50 * rep)

        # Objective
        if allow_partial:
            # Maksimal dars joylashtirish ustuvor, keyin jarimalarni minimallashtirish
            model.minimize(sum(penalty_terms) - sum(10000 * p for p in placed_vars))
        else:
            if penalty_terms:
                model.minimize(sum(penalty_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(self.max_time_in_seconds)
        solver.parameters.num_search_workers = 4

        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            self.diagnostics = self._diagnose_infeasibility()
            reason = self.diagnostics[0] if self.diagnostics else f"CP-SAT holati: {solver.status_name(status)}"
            self.unplaced = [self._build_unplaced_entry(r, reason) for r in self.requirements]
            return [], self.unplaced

        scheduled: List[ScheduledSlot] = []
        placed_indices: Set[int] = set()
        for (l_idx, d_idx, slot, r_id), var in x.items():
            if solver.value(var) == 1:
                scheduled.append(
                    ScheduledSlot(
                        day=self.DAYS[d_idx],
                        slot=slot,
                        lesson=self.requirements[l_idx],
                        room=self.rooms[r_id],
                    )
                )
                placed_indices.add(l_idx)

        if len(placed_indices) < len(self.requirements):
            self.diagnostics = self._diagnose_infeasibility()
            reason = self.diagnostics[0] if self.diagnostics else "Cheklovlar sababli joylashmadi"
            self.unplaced = [
                self._build_unplaced_entry(self.requirements[i], reason)
                for i in range(len(self.requirements))
                if i not in placed_indices
            ]

        return scheduled, self.unplaced

    def solve(self) -> Optional[List[ScheduledSlot]]:
        """
        Faqat barcha darslar ziddiyatsiz joylashganda ScheduledSlot ro'yxatini qaytaradi.
        Infeasible yoki vaqt tugasa None qaytaradi va self.diagnostics / self.unplaced ni to'ldiradi.
        """
        slots, unplaced = self._solve_internal(allow_partial=False)
        if unplaced or len(slots) != len(self.requirements):
            return None
        return slots

    def solve_partial(self) -> Tuple[List[ScheduledSlot], List[Dict[str, Any]]]:
        """Ziddiyatsiz joylashgan darslar hamda joylashmaganlar ro'yxatini qaytaradi."""
        return self._solve_internal(allow_partial=True)
