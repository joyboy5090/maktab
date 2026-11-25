import time
from collections import defaultdict
from services.generator import (
    TimetableGeneratorCSP,
    SchoolClass,
    Teacher,
    Room,
    Subject,
    LessonRequirement,
    normalize_shift,
    normalize_room_type,
)
from services.generator_cpsat import TimetableGeneratorCPSAT


def _verify_zero_conflicts(solution, classes, teachers, subjects):
    class_map = {c.id: c for c in classes}
    teacher_map = {t.id: t for t in teachers}
    subj_map = {s.id: s for s in subjects}

    class_occ = set()
    teacher_occ = set()
    room_occ = set()
    t_daily = defaultdict(int)
    t_weekly = defaultdict(int)

    for entry in solution:
        c = class_map[entry.lesson.class_id]
        sh = normalize_shift(c.shift)
        s = subj_map[entry.lesson.subject_id]

        assert (entry.day, entry.slot, c.id) not in class_occ
        class_occ.add((entry.day, entry.slot, c.id))

        assert (sh, entry.day, entry.slot, entry.room.id) not in room_occ
        room_occ.add((sh, entry.day, entry.slot, entry.room.id))

        if entry.lesson.teacher_id:
            assert (sh, entry.day, entry.slot, entry.lesson.teacher_id) not in teacher_occ
            teacher_occ.add((sh, entry.day, entry.slot, entry.lesson.teacher_id))

            t = teacher_map[entry.lesson.teacher_id]
            assert (entry.day, entry.slot) not in t.unavailable_slots
            t_daily[(t.id, entry.day)] += 1
            t_weekly[t.id] += 1
            assert t_daily[(t.id, entry.day)] <= t.max_daily_hours
            assert t_weekly[t.id] <= t.max_weekly_hours

        req_rt = normalize_room_type(s.required_room_type)
        r_rt = normalize_room_type(entry.room.room_type)
        if req_rt in ("COMPUTER_LAB", "GYM", "LABORATORY"):
            assert r_rt == req_rt
        elif entry.lesson.preferred_room_id:
            assert entry.room.id == entry.lesson.preferred_room_id


def _count_class_gaps(solution):
    by_class_day = defaultdict(list)
    for entry in solution:
        by_class_day[(entry.lesson.class_id, entry.day)].append(entry.slot)
    gaps = 0
    for slots in by_class_day.values():
        s_sorted = sorted(slots)
        if s_sorted[0] != 1:
            gaps += s_sorted[0] - 1
        for a, b in zip(s_sorted, s_sorted[1:]):
            if b - a > 1:
                gaps += b - a - 1
    return gaps


def test_cpsat_small_dataset_zero_conflicts_and_unavailable_slots():
    classes = [
        SchoolClass(id="c1", name="5-A", student_count=26, shift="MORNING"),
        SchoolClass(id="c2", name="5-B", student_count=24, shift="MORNING"),
    ]
    teachers = [
        Teacher(id="t1", name="Matematik", max_daily_hours=4, max_weekly_hours=18, unavailable_slots={("Dushanba", 1)}),
        Teacher(id="t2", name="Informatik", max_daily_hours=4, max_weekly_hours=18),
        Teacher(id="t3", name="Sportchi", max_daily_hours=4, max_weekly_hours=18),
    ]
    rooms = [
        Room(id="r1", number="5-A xona", capacity=30, room_type="GENERAL"),
        Room(id="r2", number="5-B xona", capacity=30, room_type="GENERAL"),
        Room(id="r_it", number="IT-1", capacity=30, room_type="COMPUTER_LAB"),
        Room(id="r_gym", number="Sport", capacity=50, room_type="GYM"),
    ]
    subjects = [
        Subject(id="s_mat", name="Matematika", short_code="MAT", required_room_type="GENERAL"),
        Subject(id="s_inf", name="Informatika", short_code="INF", required_room_type="COMPUTER_LAB"),
        Subject(id="s_spo", name="Jismoniy tarbiya", short_code="SPO", required_room_type="GYM"),
    ]
    requirements = [
        LessonRequirement(id=f"c1_mat_{i}", class_id="c1", subject_id="s_mat", teacher_id="t1", preferred_room_id="r1", max_per_day=1)
        for i in range(5)
    ] + [
        LessonRequirement(id=f"c2_mat_{i}", class_id="c2", subject_id="s_mat", teacher_id="t1", preferred_room_id="r2", max_per_day=1)
        for i in range(5)
    ] + [
        LessonRequirement(id=f"c1_inf_{i}", class_id="c1", subject_id="s_inf", teacher_id="t2", max_per_day=1)
        for i in range(2)
    ] + [
        LessonRequirement(id=f"c2_inf_{i}", class_id="c2", subject_id="s_inf", teacher_id="t2", max_per_day=1)
        for i in range(2)
    ] + [
        LessonRequirement(id=f"c1_spo_{i}", class_id="c1", subject_id="s_spo", teacher_id="t3", max_per_day=1)
        for i in range(2)
    ]

    solver = TimetableGeneratorCPSAT(classes, teachers, rooms, subjects, requirements, slots_per_day=6, max_time_in_seconds=10.0)
    solution = solver.solve()
    assert solution is not None
    assert len(solution) == len(requirements)
    assert solver.unplaced == []
    _verify_zero_conflicts(solution, classes, teachers, subjects)


def test_cpsat_infeasible_diagnostics():
    classes = [SchoolClass(id="c1", name="5-A", student_count=25)]
    teachers = [Teacher(id="t1", name="Ustoz", max_weekly_hours=2, max_daily_hours=2)]
    rooms = [Room(id="r1", number="101", capacity=30, room_type="GENERAL")]
    subjects = [Subject(id="s1", name="Matematika", short_code="MAT", required_room_type="GENERAL")]
    requirements = [
        LessonRequirement(id=f"req_{i}", class_id="c1", subject_id="s1", teacher_id="t1", preferred_room_id="r1")
        for i in range(6)
    ]

    solver = TimetableGeneratorCPSAT(classes, teachers, rooms, subjects, requirements, max_time_in_seconds=5.0)
    solution = solver.solve()
    assert solution is None
    assert len(solver.diagnostics) > 0
    assert any("max_weekly_hours" in d for d in solver.diagnostics)
    assert len(solver.unplaced) == 6


def test_cpsat_medium_22_classes_benchmark_and_comparison():
    """22 sinfli real ko'rinishdagi maktab to'plamida CP-SAT vs legacy taqqoslash."""
    num_classes = 22
    classes = [
        SchoolClass(
            id=f"c_{i}",
            name=f"{5 + (i // 4)}-{chr(65 + (i % 4))}",
            student_count=28,
            shift="MORNING" if i % 2 == 0 else "AFTERNOON",
        )
        for i in range(num_classes)
    ]
    rooms = [
        Room(id=f"r_gen_{i}", number=f"{100 + i}", capacity=32, room_type="GENERAL")
        for i in range(num_classes)
    ] + [
        Room(id="r_it_1", number="IT-1", capacity=32, room_type="COMPUTER_LAB"),
        Room(id="r_it_2", number="IT-2", capacity=32, room_type="COMPUTER_LAB"),
        Room(id="r_gym_1", number="Sport-1", capacity=60, room_type="GYM"),
        Room(id="r_gym_2", number="Sport-2", capacity=60, room_type="GYM"),
        Room(id="r_lab_1", number="Lab-1", capacity=32, room_type="LABORATORY"),
    ]
    subjects = [
        Subject(id="s_mat", name="Matematika", short_code="MAT", required_room_type="GENERAL"),
        Subject(id="s_ona", name="Ona tili", short_code="ONA", required_room_type="GENERAL"),
        Subject(id="s_eng", name="Ingliz tili", short_code="ENG", required_room_type="GENERAL"),
        Subject(id="s_tar", name="Tarix", short_code="TAR", required_room_type="GENERAL"),
        Subject(id="s_inf", name="Informatika", short_code="INF", required_room_type="COMPUTER_LAB"),
        Subject(id="s_spo", name="Jismoniy tarbiya", short_code="SPO", required_room_type="GYM"),
        Subject(id="s_fiz", name="Fizika", short_code="FIZ", required_room_type="LABORATORY"),
    ]

    # Har bir fan uchun yetarli o'qituvchilar (5 ta guruhda taqsimlangan)
    teachers = []
    for subj in subjects:
        for g in range(4):
            teachers.append(
                Teacher(
                    id=f"t_{subj.short_code}_{g}",
                    name=f"{subj.name} Ustoz {g}",
                    max_daily_hours=6,
                    max_weekly_hours=36,
                )
            )

    weekly_plan = [
        ("s_mat", "MAT", 5, 2),
        ("s_ona", "ONA", 4, 2),
        ("s_eng", "ENG", 4, 2),
        ("s_tar", "TAR", 2, 1),
        ("s_inf", "INF", 2, 1),
        ("s_spo", "SPO", 2, 1),
        ("s_fiz", "FIZ", 2, 1),
    ]

    requirements = []
    for i, cls in enumerate(classes):
        g = i % 4
        for s_id, code, hrs, mpd in weekly_plan:
            pref = f"r_gen_{i}" if s_id in ("s_mat", "s_ona", "s_eng", "s_tar") else None
            for h in range(hrs):
                requirements.append(
                    LessonRequirement(
                        id=f"{cls.id}_{s_id}_{h}",
                        class_id=cls.id,
                        subject_id=s_id,
                        teacher_id=f"t_{code}_{g}",
                        preferred_room_id=pref,
                        max_per_day=mpd,
                    )
                )

    t0 = time.perf_counter()
    cpsat = TimetableGeneratorCPSAT(classes, teachers, rooms, subjects, requirements, slots_per_day=6, max_time_in_seconds=15.0)
    cpsat_solution = cpsat.solve()
    cpsat_time = time.perf_counter() - t0

    assert cpsat_solution is not None
    assert len(cpsat_solution) == len(requirements)
    _verify_zero_conflicts(cpsat_solution, classes, teachers, subjects)
    cpsat_gaps = _count_class_gaps(cpsat_solution)

    t1 = time.perf_counter()
    legacy = TimetableGeneratorCSP(classes, teachers, rooms, subjects, requirements, slots_per_day=6, timeout_seconds=15.0)
    legacy_slots, legacy_unplaced = legacy.solve_partial()
    legacy_time = time.perf_counter() - t1
    legacy_gaps = _count_class_gaps(legacy_slots)

    print(
        f"\n[Benchmark 22 classes / {len(requirements)} lessons] "
        f"CP-SAT: {len(cpsat_solution)}/{len(requirements)} in {cpsat_time:.2f}s (gaps={cpsat_gaps}) | "
        f"Legacy: {len(legacy_slots)}/{len(requirements)} (unplaced={len(legacy_unplaced)}) in {legacy_time:.2f}s (gaps={legacy_gaps})"
    )
    assert cpsat_gaps <= legacy_gaps or len(cpsat_solution) >= len(legacy_slots)
