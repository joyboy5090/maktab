import pytest
import random
import time
from services.generator import (
    normalize_shift,
    normalize_room_type,
    TimetableGeneratorCSP,
    SchoolClass,
    Teacher,
    Room,
    Subject,
    LessonRequirement,
)
from services.timetable_service import TimetableService

def test_normalize_shift():
    assert normalize_shift("1-smena") == "MORNING"
    assert normalize_shift("MORNING") == "MORNING"
    assert normalize_shift("2-smena") == "AFTERNOON"
    assert normalize_shift("AFTERNOON") == "AFTERNOON"
    assert normalize_shift(None) == "MORNING"

def test_normalize_room_type():
    assert normalize_room_type("Kimyo laboratoriyasi") == "LABORATORY"
    assert normalize_room_type("Sport zal") == "GYM"
    assert normalize_room_type("Kompyuter xonasi") == "COMPUTER_LAB"
    assert normalize_room_type("Adabiyot") == "GENERAL"
    assert normalize_room_type("Matematika") == "GENERAL"
    assert normalize_room_type(None) == "GENERAL"

def test_csp_generator_simple_solve():
    classes = [
        SchoolClass(id="c1", name="5-A", student_count=25, shift="MORNING")
    ]
    teachers = [
        Teacher(id="t1", name="Vali Aliyev", max_daily_hours=4, max_weekly_hours=20),
        Teacher(id="t2", name="Ali Valiyev", max_daily_hours=4, max_weekly_hours=20)
    ]
    rooms = [
        Room(id="r1", number="101", capacity=30, room_type="GENERAL")
    ]
    subjects = [
        Subject(id="s1", name="Matematika", short_code="MAT", required_room_type="GENERAL"),
        Subject(id="s2", name="Fizika", short_code="FIZ", required_room_type="GENERAL")
    ]
    # 4 math lessons, 3 physics lessons
    requirements = [
        LessonRequirement(id=f"m_{i}", class_id="c1", subject_id="s1", teacher_id="t1", preferred_room_id="r1", max_per_day=1)
        for i in range(4)
    ] + [
        LessonRequirement(id=f"p_{i}", class_id="c1", subject_id="s2", teacher_id="t2", preferred_room_id="r1", max_per_day=1)
        for i in range(3)
    ]

    progress_calls = []
    def on_progress(current, total):
        progress_calls.append((current, total))

    csp = TimetableGeneratorCSP(
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        requirements=requirements,
        slots_per_day=6,
        max_candidates=30,
        timeout_seconds=15.0,
        on_progress=on_progress
    )

    solution = csp.solve()
    assert solution is not None
    assert len(solution) == 7

    # Check hard constraint: No teacher overlap
    teacher_slots = set()
    for entry in solution:
        key = (entry.lesson.teacher_id, entry.day, entry.slot)
        assert key not in teacher_slots, f"Duplicate slot for teacher: {key}"
        teacher_slots.add(key)

    # Check hard constraint: No class overlap
    class_slots = set()
    for entry in solution:
        key = (entry.lesson.class_id, entry.day, entry.slot)
        assert key not in class_slots, f"Duplicate slot for class: {key}"
        class_slots.add(key)

    # Check progress callbacks were invoked
    assert len(progress_calls) > 0

def test_csp_daily_and_weekly_hours_limit():
    classes = [
        SchoolClass(id="c1", name="5-A", student_count=25, shift="MORNING")
    ]
    # Teacher with strict max 2 hours daily and max 5 hours weekly
    teachers = [
        Teacher(id="t1", name="Strict Teacher", max_daily_hours=2, max_weekly_hours=5)
    ]
    rooms = [
        Room(id="r1", number="101", capacity=30, room_type="GENERAL")
    ]
    subjects = [
        Subject(id="s1", name="Matematika", short_code="MAT", required_room_type="GENERAL")
    ]
    requirements = [
        LessonRequirement(id=f"req_{i}", class_id="c1", subject_id="s1", teacher_id="t1", preferred_room_id="r1")
        for i in range(5)
    ]

    csp = TimetableGeneratorCSP(
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        requirements=requirements,
        slots_per_day=6,
        timeout_seconds=5.0
    )

    solution = csp.solve()
    assert solution is not None
    assert len(solution) == 5

    # Check daily limit <= 2
    daily_count = {}
    for entry in solution:
        daily_count[entry.day] = daily_count.get(entry.day, 0) + 1
    for count in daily_count.values():
        assert count <= 2

def test_max_per_day_single_occurrence_and_penalty():
    """1. max_per_day default qiymati 1 va ayni bir fan takrorida jarima (+50) tekshiruvi"""
    req = LessonRequirement(id="l1", class_id="c1", subject_id="s1", teacher_id="t1")
    assert req.max_per_day == 1

    classes = [SchoolClass(id="c1", name="5-A", student_count=20)]
    teachers = [Teacher(id="t1", name="Ustoz")]
    rooms = [Room(id="r1", number="101", capacity=25)]
    subjects = [Subject(id="s1", name="Matematika", short_code="MAT")]
    csp = TimetableGeneratorCSP(classes, teachers, rooms, subjects, [req])

    # Dastlab bir kunda dars yo'q, is_hard_valid True bo'lishi kerak
    assert csp.is_hard_valid(req, "Dushanba", 1, rooms[0], max_per_day=1) is True

    # 1-soatga joylashtiramiz
    csp.assign(req, "Dushanba", 1, rooms[0])

    # Endi max_per_day=1 bo'lsa, shu kuni 2-soatga qo'yish rad etiladi
    req2 = LessonRequirement(id="l2", class_id="c1", subject_id="s1", teacher_id="t1")
    assert csp.is_hard_valid(req2, "Dushanba", 2, rooms[0], max_per_day=1) is False
    # Agar max_per_day=2 bo'lsa, ruxsat beriladi
    assert csp.is_hard_valid(req2, "Dushanba", 2, rooms[0], max_per_day=2) is True

    # Takrorlangan fan uchun jarima (+50) qo'shilishini tekshiramiz (50 - 25(sinf) - 8(ustoz) = 17)
    penalty = csp.calculate_slot_penalty(req2, "Dushanba", 2, rooms[0])
    assert penalty == 17

def test_class_gap_penalty_and_continuous_slots():
    """2. Sinf uchun oyna (gap) bo'lganda katta jarima (+100) va 1-soat bonusi"""
    classes = [SchoolClass(id="c1", name="5-A", student_count=20)]
    teachers = [Teacher(id="t1", name="Ustoz 1"), Teacher(id="t2", name="Ustoz 2")]
    rooms = [Room(id="r1", number="101", capacity=25)]
    subjects = [Subject(id="s1", name="Matematika", short_code="MAT"), Subject(id="s2", name="Tarix", short_code="TAR")]
    csp = TimetableGeneratorCSP(classes, teachers, rooms, subjects, [])

    req1 = LessonRequirement(id="l1", class_id="c1", subject_id="s1", teacher_id="t1")
    req2 = LessonRequirement(id="l2", class_id="c1", subject_id="s2", teacher_id="t2")

    # 1-dars 1-soatga qo'yilsa jarima kamroq bo'lishi kerak
    pen_slot1 = csp.calculate_slot_penalty(req1, "Dushanba", 1, rooms[0])
    pen_slot3 = csp.calculate_slot_penalty(req1, "Dushanba", 3, rooms[0])
    assert pen_slot1 < pen_slot3

    # 1-soatga tayinlaymiz
    csp.assign(req1, "Dushanba", 1, rooms[0])

    # Endi 2-soat (ketma-ket) bilan 4-soat (oyna qoldiradigan) jarimasini solishtiramiz
    pen_continuous = csp.calculate_slot_penalty(req2, "Dushanba", 2, rooms[0])
    pen_with_gap = csp.calculate_slot_penalty(req2, "Dushanba", 4, rooms[0])

    assert pen_with_gap >= pen_continuous + 100

def test_specialized_rooms_and_preferred_room():
    """3. Maxsus xonalar ixtisoslashuvi va preferred_room_id bonusi"""
    classes = [SchoolClass(id="c1", name="5-A", student_count=20)]
    teachers = [Teacher(id="t1", name="IT Ustoz"), Teacher(id="t2", name="Oddiy Ustoz")]
    rooms = [
        Room(id="r_it", number="IT-1", capacity=25, room_type="COMPUTER_LAB"),
        Room(id="r_gen", number="101", capacity=25, room_type="GENERAL"),
        Room(id="r_gym", number="Sport", capacity=50, room_type="GYM"),
    ]
    subjects = [
        Subject(id="s_inf", name="Informatika", short_code="INF", required_room_type="COMPUTER_LAB"),
        Subject(id="s_ona", name="Ona tili", short_code="ONA", required_room_type="GENERAL"),
    ]
    csp = TimetableGeneratorCSP(classes, teachers, rooms, subjects, [])

    req_inf = LessonRequirement(id="l_inf", class_id="c1", subject_id="s_inf", teacher_id="t1")
    req_ona = LessonRequirement(id="l_ona", class_id="c1", subject_id="s_ona", teacher_id="t2", preferred_room_id="r_gen")

    # Informatika faqat IT-xonasiga ruxsat etiladi, Oddiy xona yoki Sport zalga mutlaqo ruxsat etilmaydi
    assert csp.is_hard_valid(req_inf, "Dushanba", 1, rooms[0]) is True
    assert csp.is_hard_valid(req_inf, "Dushanba", 1, rooms[1]) is False
    assert csp.is_hard_valid(req_inf, "Dushanba", 1, rooms[2]) is False

    # Ona tili sport zal yoki IT-zalga ruxsat etilmaydi
    assert csp.is_hard_valid(req_ona, "Dushanba", 1, rooms[0]) is False
    assert csp.is_hard_valid(req_ona, "Dushanba", 1, rooms[2]) is False
    assert csp.is_hard_valid(req_ona, "Dushanba", 1, rooms[1]) is True

    # preferred_room_id bo'lsa bonus (-20)
    pen_preferred = csp.calculate_slot_penalty(req_ona, "Dushanba", 1, rooms[1])
    assert pen_preferred < 0

def test_timeout_returns_none_when_impossible():
    """5. Timeout bo'lganda chala natija qaytmasdan None qaytishi"""
    classes = [SchoolClass(id="c1", name="5-A", student_count=20)]
    teachers = [Teacher(id="t1", name="Ustoz", max_weekly_hours=1)] # Faqat 1 soat ruxsat
    rooms = [Room(id="r1", number="101", capacity=25)]
    subjects = [Subject(id="s1", name="Fan", short_code="FAN")]
    # 10 soat dars talab qilinmoqda, lekin o'qituvchining haftalik limiti 1 soat!
    requirements = [
        LessonRequirement(id=f"l_{i}", class_id="c1", subject_id="s1", teacher_id="t1")
        for i in range(10)
    ]
    csp = TimetableGeneratorCSP(classes, teachers, rooms, subjects, requirements, timeout_seconds=0.1)
    solution = csp.solve()
    assert solution is None
    assert len(csp.unplaced) > 0
    assert "reason" in csp.unplaced[0]


def test_parse_unavailable_slots():
    parsed = TimetableService._parse_unavailable_slots([
        ["Dushanba", 1],
        {"day": "Juma", "slot": 6},
    ])
    assert parsed == {("Dushanba", 1), ("Juma", 6)}


def test_property_random_inputs_zero_conflicts_and_constraints_respected():
    """
    Property-test: 20 ta tasodifiy maktab konfiguratsiyasi uchun:
    - Nol teacher/room/sinf to'qnashuvi
    - unavailable_slots, max_daily_hours, max_weekly_hours, xona turi cheklovlari buzilmaydi
    - len(scheduled) + len(unplaced) == len(requirements)
    """
    days = TimetableGeneratorCSP.DAYS
    for seed in range(20):
        rng = random.Random(seed)
        num_classes = rng.randint(2, 5)
        classes = [
            SchoolClass(
                id=f"c_{i}",
                name=f"{5 + i}-A",
                student_count=rng.randint(18, 32),
                shift=rng.choice(["MORNING", "AFTERNOON"]),
            )
            for i in range(num_classes)
        ]

        num_teachers = rng.randint(3, 7)
        teachers = []
        for i in range(num_teachers):
            unavail = {
                (rng.choice(days), rng.randint(1, 6))
                for _ in range(rng.randint(0, 4))
            }
            teachers.append(
                Teacher(
                    id=f"t_{i}",
                    name=f"Teacher {i}",
                    max_daily_hours=rng.randint(2, 5),
                    max_weekly_hours=rng.randint(4, 20),
                    unavailable_slots=unavail,
                )
            )

        rooms = [
            Room(id=f"r_gen_{i}", number=f"10{i}", capacity=35, room_type="GENERAL")
            for i in range(num_classes)
        ] + [
            Room(id="r_it", number="IT-1", capacity=35, room_type="COMPUTER_LAB"),
            Room(id="r_gym", number="Sport", capacity=50, room_type="GYM"),
            Room(id="r_lab", number="Lab-1", capacity=35, room_type="LABORATORY"),
        ]

        subjects = [
            Subject(id="s_mat", name="Matematika", short_code="MAT", required_room_type="GENERAL"),
            Subject(id="s_inf", name="Informatika", short_code="INF", required_room_type="COMPUTER_LAB"),
            Subject(id="s_spo", name="Jismoniy tarbiya", short_code="SPO", required_room_type="GYM"),
            Subject(id="s_kim", name="Kimyo", short_code="KIM", required_room_type="LABORATORY"),
        ]

        requirements = []
        num_reqs = rng.randint(10, 35)
        for i in range(num_reqs):
            cls_idx = rng.randrange(num_classes)
            subj = rng.choice(subjects)
            teacher = rng.choice(teachers)
            pref = f"r_gen_{cls_idx}" if subj.required_room_type == "GENERAL" else None
            requirements.append(
                LessonRequirement(
                    id=f"req_{seed}_{i}",
                    class_id=classes[cls_idx].id,
                    subject_id=subj.id,
                    teacher_id=teacher.id,
                    preferred_room_id=pref,
                    max_per_day=2,
                )
            )

        csp = TimetableGeneratorCSP(
            classes=classes,
            teachers=teachers,
            rooms=rooms,
            subjects=subjects,
            requirements=requirements,
            slots_per_day=6,
            timeout_seconds=5.0,
        )
        scheduled, unplaced = csp.solve_partial()

        assert len(scheduled) + len(unplaced) == len(requirements)

        teacher_map = {t.id: t for t in teachers}
        class_map = {c.id: c for c in classes}
        subj_map = {s.id: s for s in subjects}

        teacher_occ = set()
        room_occ = set()
        class_occ = set()
        t_daily = {}
        t_weekly = {}

        for entry in scheduled:
            c = class_map[entry.lesson.class_id]
            shift = normalize_shift(c.shift)
            s = subj_map[entry.lesson.subject_id]

            # Zero class conflict
            c_key = (entry.day, entry.slot, c.id)
            assert c_key not in class_occ
            class_occ.add(c_key)

            # Zero room conflict
            r_key = (shift, entry.day, entry.slot, entry.room.id)
            assert r_key not in room_occ
            room_occ.add(r_key)

            # Zero teacher conflict & teacher constraints
            if entry.lesson.teacher_id:
                t_key = (shift, entry.day, entry.slot, entry.lesson.teacher_id)
                assert t_key not in teacher_occ
                teacher_occ.add(t_key)

                teacher = teacher_map[entry.lesson.teacher_id]
                assert (entry.day, entry.slot) not in teacher.unavailable_slots
                t_daily[(teacher.id, entry.day)] = t_daily.get((teacher.id, entry.day), 0) + 1
                t_weekly[teacher.id] = t_weekly.get(teacher.id, 0) + 1
                assert t_daily[(teacher.id, entry.day)] <= teacher.max_daily_hours
                assert t_weekly[teacher.id] <= teacher.max_weekly_hours

            # Room specialization & preferred room
            req_type = normalize_room_type(s.required_room_type)
            r_type = normalize_room_type(entry.room.room_type)
            if req_type in ("COMPUTER_LAB", "GYM", "LABORATORY"):
                assert r_type == req_type
            elif entry.lesson.preferred_room_id:
                assert entry.room.id == entry.lesson.preferred_room_id
