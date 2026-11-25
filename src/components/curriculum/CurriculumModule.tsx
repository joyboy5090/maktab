'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Plus,
  BookOpen,
  Calendar,
  Clock,
  Trash2,
  Sparkles,
  Calculator,
  User,
  DoorOpen,
  CheckCircle2,
  Layers,
  ArrowRight
} from 'lucide-react';
import { curriculumApi, timetableApi } from '@/lib/api';
import { useSchoolData } from '@/context/SchoolDataContext';
import {
  filterTeachersForSubject,
  getAvailableRoomsForClass,
  getRecommendedRoomId
} from '@/lib/subjectUtils';

export interface AllocationItem {
  id: string;
  className: string;
  classId: string;
  subjectName: string;
  subjectCode: string;
  colorHex: string;
  teacherName: string;
  teacherId: string;
  roomNumber: string;
  term: number;
  quarterTotalHours: number;
  weeksInQuarter: number;
  weeklyHours: number;
  maxPerDay: number;
}

export const CurriculumModule: React.FC<{ onNavigateToTimetable?: () => void }> = ({
  onNavigateToTimetable,
}) => {
  const { classes, teachers, subjects, rooms } = useSchoolData();

  const [allocations, setAllocations] = useState<AllocationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedClass, setSelectedClass] = useState<string>('5-A');
  const [selectedTerm, setSelectedTerm] = useState<number>(1);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);

  // Form states
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [selectedTeacherId, setSelectedTeacherId] = useState<string>('');
  const [selectedRoomId, setSelectedRoomId] = useState<string>('');
  const [quarterHours, setQuarterHours] = useState<number>(36);
  const [weeksInTerm, setWeeksInTerm] = useState<number>(9);
  const [maxDaily, setMaxDaily] = useState<number>(2);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // PostgreSQL Neon bazasidan o'quv rejasini (allocations) yuklash
  const loadAllocations = async () => {
    setIsLoading(true);
    try {
      const data = await curriculumApi.getAll();
      if (data && Array.isArray(data)) {
        setAllocations(
          data.map((item: any) => ({
            id: item.id,
            className: item.class_name,
            classId: item.class_id,
            subjectName: item.subject_name,
            subjectCode: item.subject_code,
            colorHex: item.color_hex || '#1E40AF',
            teacherName: item.teacher_name,
            teacherId: item.teacher_id,
            roomNumber: item.room_number || '-',
            term: item.term || 1,
            quarterTotalHours: item.quarter_total_hours || 36,
            weeksInQuarter: item.weeks_in_quarter || 9,
            weeklyHours: item.weekly_hours || 4,
            maxPerDay: item.max_hours_per_day || 2,
          }))
        );
      }
    } catch (err) {
      console.warn("O'quv rejasini yuklashda xatolik:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllocations();
  }, []);

  // Tanlangan sinf uchun faqat shaxsiy xona yoki laboratoriya/maxsus xonalar
  const availableRooms = useMemo(() => {
    return getAvailableRoomsForClass(selectedClass, rooms);
  }, [rooms, selectedClass]);

  // Tanlangan fanga mos mutaxassis o'qituvchilar (Faqat shu fanni o'tadiganlar)
  const availableTeachers = useMemo(() => {
    if (!selectedSubjectId) return [];
    const subj = subjects.find((s) => s.id === selectedSubjectId);
    return filterTeachersForSubject(teachers, subj);
  }, [teachers, subjects, selectedSubjectId]);

  // Standart qiymatlarni o'rnatish
  useEffect(() => {
    const currentClass = selectedClass || classes[0]?.name || '';
    if (classes.length > 0 && !selectedClass) {
      setSelectedClass(classes[0].name);
    }
    if (subjects.length > 0 && !selectedSubjectId) {
      const firstSubj = subjects[0];
      setSelectedSubjectId(firstSubj.id);
      const matched = filterTeachersForSubject(teachers, firstSubj);
      setSelectedTeacherId(matched[0]?.id || '');
      const clsRooms = getAvailableRoomsForClass(currentClass, rooms);
      setSelectedRoomId(getRecommendedRoomId(firstSubj, currentClass, clsRooms));
    }
  }, [subjects, teachers, rooms, classes, selectedClass]);

  const handleSubjectSelect = (subjId: string) => {
    setSelectedSubjectId(subjId);
    const subj = subjects.find((s) => s.id === subjId);
    if (subj) {
      const matched = filterTeachersForSubject(teachers, subj);
      setSelectedTeacherId(matched[0]?.id || '');
      const clsRooms = getAvailableRoomsForClass(selectedClass, rooms);
      setSelectedRoomId(getRecommendedRoomId(subj, selectedClass, clsRooms));
    }
  };

  // Avtomatik haftalik soat hisobi
  const calculatedWeeklyHours = Math.max(1, Math.round(quarterHours / (weeksInTerm || 1)));

  // Yangi fan biriktirish
  const handleAddAllocation = async (e: React.FormEvent) => {
    e.preventDefault();
    const cls = classes.find((c) => c.name === selectedClass);
    const subj = subjects.find((s) => s.id === selectedSubjectId);
    const teacher = teachers.find((t) => t.id === selectedTeacherId);
    const room = rooms.find((r) => r.id === selectedRoomId);

    if (!cls || !subj || !teacher) {
      alert("Iltimos, sinf, fan va o'qituvchini to'liq tanlang");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await curriculumApi.allocate({
        class_id: cls.id,
        subject_id: subj.id,
        teacher_id: teacher.id,
        preferred_room_id: room?.id,
        term: selectedTerm,
        quarter_total_hours: Number(quarterHours),
        weeks_in_quarter: Number(weeksInTerm),
        weekly_hours: calculatedWeeklyHours,
        max_hours_per_day: Number(maxDaily),
      });

      const newItem: AllocationItem = {
        id: res.id || `alloc_${Date.now()}`,
        className: cls.name,
        classId: cls.id,
        subjectName: subj.name,
        subjectCode: subj.code,
        colorHex: subj.colorHex,
        teacherName: teacher.fullName,
        teacherId: teacher.id,
        roomNumber: room?.roomNumber || '-',
        term: selectedTerm,
        quarterTotalHours: Number(quarterHours),
        weeksInQuarter: Number(weeksInTerm),
        weeklyHours: calculatedWeeklyHours,
        maxPerDay: Number(maxDaily),
      };

      setAllocations((prev) => [newItem, ...prev]);
      setShowAddModal(false);
    } catch (err: any) {
      alert("Fanni saqlashda xatolik: " + (err.message || 'Server xatosi'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAssignTeacher = async (allocationId: string, teacherId: string) => {
    try {
      const teacher = teachers.find((t) => t.id === teacherId);
      setAllocations((prev) =>
        prev.map((a) =>
          a.id === allocationId
            ? { ...a, teacherId: teacherId || '', teacherName: teacher?.fullName || '' }
            : a
        )
      );

      await curriculumApi.updateAllocation(allocationId, {
        teacher_id: teacherId || undefined,
      });
    } catch (err) {
      console.error("O'qituvchini biriktirishda xatolik:", err);
      alert("O'qituvchini biriktirishda xatolik yuz berdi");
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Ushbu fanni mazkur sinf o'quv rejasidan olib tashlamoqchimisiz?")) {
      try {
        await curriculumApi.deleteAllocation(id);
        setAllocations((prev) => prev.filter((a) => a.id !== id));
      } catch (err) {
        alert("O'chirishda xatolik yuz berdi");
      }
    }
  };

  // Tanlangan sinf va chorak bo'yicha filtr
  const filtered = useMemo(() => {
    return allocations.filter((a) => {
      const matchesClass = a.className === selectedClass || a.classId === selectedClass;
      const matchesTerm = a.term === selectedTerm;
      return matchesClass && matchesTerm;
    });
  }, [allocations, selectedClass, selectedTerm]);

  // Umumiy haftalik yuklama
  const totalWeeklyForClass = filtered.reduce((sum, item) => sum + item.weeklyHours, 0);
  const totalQuarterForClass = filtered.reduce((sum, item) => sum + item.quarterTotalHours, 0);

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar */}
      <div className="bg-[#FFFFFF] p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-[#1E40AF] uppercase tracking-wider mb-1">
            <Layers className="w-4 h-4" />
            <span>O'quv Dasturi & Dars Soatlari Taqsimoti</span>
          </div>
          <h2 className="text-xl font-black text-gray-900">
            Sinflar O'quv Rejasi (Choraklik Taqsimot)
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Har bir sinfga qaysi fanlar o'tilishi va bir chorak davomidagi jami dars soatlarini
            belgilang. Dars jadvali aynan shu yuklamaga asosan tuziladi.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Chorak Switcher */}
          <div className="flex items-center bg-gray-100 p-1 rounded-xl border border-gray-200 text-xs font-bold">
            {[1, 2, 3, 4].map((term) => (
              <button
                key={term}
                onClick={() => setSelectedTerm(term)}
                className={`px-3 py-1.5 rounded-lg transition ${
                  selectedTerm === term
                    ? 'bg-[#1E40AF] text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {term}-chorak
              </button>
            ))}
          </div>

          {/* Sinf Tanlash Dropdown (Bazadagi barcha sinflar) */}
          <div className="flex items-center gap-2">
            <select
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              className="bg-white border border-gray-300 text-gray-900 text-sm font-bold rounded-xl focus:ring-2 focus:ring-[#1E40AF] px-3.5 py-2 outline-none shadow-sm"
            >
              {classes.map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name} sinf
                </option>
              ))}
            </select>
          </div>

          {/* O'qituvchilar Ehtiyoji Tahlili Tugmasi */}
          <a
            href="/dashboard/teachers"
            className="flex items-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-xs px-3.5 py-2.5 rounded-xl border border-indigo-200 transition"
          >
            <Calculator className="w-4 h-4 text-indigo-600" />
            <span>O'qituvchilar Ehtiyoji</span>
          </a>

          {/* Yangi Fan Biriktirish Tugmasi */}
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-sm transition active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Sinfga Fan Biriktirish</span>
          </button>
        </div>
      </div>

      {/* 2. Sinf Yuklamasi Statistikasi */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#FFFFFF] p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-500 font-medium">Haftalik umumiy dars yuklamasi</div>
            <div className="text-2xl font-black text-gray-900 mt-1">
              {totalWeeklyForClass} <span className="text-sm font-normal text-gray-500">soat/hafta</span>
            </div>
            <div className="text-[11px] text-[#10B981] font-semibold mt-0.5">
              Me'yoriy sanitariya talablariga mos (max 30s)
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-[#1E40AF] flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-[#FFFFFF] p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-500 font-medium">{selectedTerm}-chorakdagi umumiy soatlar</div>
            <div className="text-2xl font-black text-gray-900 mt-1">
              {totalQuarterForClass} <span className="text-sm font-normal text-gray-500">soat</span>
            </div>
            <div className="text-[11px] text-gray-400 font-medium mt-0.5">
              Taxminiy 9 o'quv haftasi hisobida
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-[#10B981] flex items-center justify-center">
            <Calculator className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-blue-900 font-bold uppercase tracking-wider">Dars Jadvaliga Tayyormi?</div>
            <div className="text-xs text-blue-800 mt-1">
              {filtered.length > 0 ? `${filtered.length} ta fan to'liq taqsimlangan` : "Fanlar kiritilmagan"}
            </div>
            {onNavigateToTimetable && (
              <button
                onClick={onNavigateToTimetable}
                className="mt-2 text-xs font-bold text-[#1E40AF] hover:underline flex items-center gap-1"
              >
                Jadval generatoriga o'tish <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-md">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 3. O'quv Rejasi Jadvali */}
      <div className="bg-[#FFFFFF] rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
          <div className="text-xs font-bold text-gray-700">
            {selectedClass} sinfi uchun {selectedTerm}-chorak o'quv fani va soatlari ro'yxati:
          </div>
          <div className="text-xs text-gray-500">Jami {filtered.length} ta fan</div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-3.5 px-5">Fan Nomi</th>
                <th className="py-3.5 px-5">Biriktirilgan O'qituvchi</th>
                <th className="py-3.5 px-5">Xona</th>
                <th className="py-3.5 px-5 text-center">Choraklik Jami Soat</th>
                <th className="py-3.5 px-5 text-center">Haftalik Dars Soati</th>
                <th className="py-3.5 px-5 text-center">Kunlik Maksimal</th>
                <th className="py-3.5 px-5 text-right">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {filtered.length > 0 ? (
                filtered.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/60 transition">
                    <td className="py-3.5 px-5">
                      <div className="flex items-center gap-2.5">
                        <span
                          style={{ backgroundColor: item.colorHex }}
                          className="w-3 h-3 rounded-full inline-block"
                        ></span>
                        <div>
                          <div className="font-bold text-gray-900">{item.subjectName}</div>
                          <div className="text-[11px] text-gray-400 font-mono">{item.subjectCode}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-5">
                      <div
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold transition ${
                          item.teacherId
                            ? 'bg-blue-50/70 border-blue-200 text-blue-900'
                            : 'bg-amber-50/70 border-amber-200 text-amber-900'
                        }`}
                      >
                        <User
                          className={`w-3.5 h-3.5 shrink-0 ${
                            item.teacherId ? 'text-[#1E40AF]' : 'text-amber-600'
                          }`}
                        />
                        <select
                          value={item.teacherId || ''}
                          onChange={(e) => handleAssignTeacher(item.id, e.target.value)}
                          className="bg-transparent outline-none cursor-pointer text-xs font-bold"
                          title="Fanga o'qituvchi biriktirish"
                        >
                          <option value="">Biriktirilmagan (Tanlang...)</option>
                          {(() => {
                            const subj = subjects.find((s) => s.name === item.subjectName);
                            const matched = filterTeachersForSubject(teachers, subj);
                            const list = matched.length > 0 ? matched : teachers;
                            return list.map((t) => (
                              <option key={t.id} value={t.id}>
                                {t.fullName} ({t.subject})
                              </option>
                            ));
                          })()}
                        </select>
                      </div>
                    </td>
                    <td className="py-3.5 px-5">
                      <span className="inline-flex items-center gap-1 bg-gray-100 px-2 py-0.5 rounded text-xs font-medium text-gray-700">
                        <DoorOpen className="w-3 h-3 text-gray-400" />
                        {item.roomNumber}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 text-center">
                      <span className="font-bold text-gray-900 bg-blue-50 text-[#1E40AF] px-2.5 py-1 rounded-lg text-xs">
                        {item.quarterTotalHours} soat
                      </span>
                      <div className="text-[10px] text-gray-400 mt-0.5">({item.weeksInQuarter} hafta)</div>
                    </td>
                    <td className="py-3.5 px-5 text-center">
                      <span className="font-black text-emerald-700 bg-emerald-100/70 px-3 py-1 rounded-lg text-xs">
                        {item.weeklyHours} soat / hafta
                      </span>
                    </td>
                    <td className="py-3.5 px-5 text-center text-xs text-gray-600 font-medium">
                      Kuniga max {item.maxPerDay} soat
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                        title="O'chirish"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-gray-400 text-xs">
                    Ushbu sinf uchun {selectedTerm}-chorakda hali fanlar biriktirilmagan.
                    <br />
                    Yuqoridagi <strong>"Sinfga Fan Biriktirish"</strong> tugmasini bosing.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Modal: Yangi Fan Biriktirish */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <div>
                <h3 className="text-lg font-bold text-[#1E40AF]">
                  {selectedClass} Sinfga Fan & Choraklik Soat Biriktirish
                </h3>
                <p className="text-xs text-gray-400">{selectedTerm}-chorak o'quv dasturi uchun</p>
              </div>
            </div>

            <form onSubmit={handleAddAllocation} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Fan:</label>
                  <select
                    value={selectedSubjectId}
                    onChange={(e) => handleSubjectSelect(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none bg-white font-medium"
                  >
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">O'qituvchi:</label>
                  <select
                    value={selectedTeacherId}
                    onChange={(e) => setSelectedTeacherId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none bg-white font-medium"
                  >
                    {availableTeachers.length > 0 ? (
                      availableTeachers.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.fullName} ({t.subject})
                        </option>
                      ))
                    ) : (
                      <option value="">Bu fan bo'yicha o'qituvchi topilmadi</option>
                    )}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">
                  Afzal ko'rilgan Xona:
                </label>
                <select
                  value={selectedRoomId}
                  onChange={(e) => setSelectedRoomId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none bg-white font-medium"
                >
                  <option value="">Biriktirilmagan</option>
                  {availableRooms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.roomNumber} ({r.name})
                    </option>
                  ))}
                </select>
              </div>

              {/* CHORAKLIK VA HAFTALIK SOATLAR */}
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200/80 space-y-3">
                <div className="text-xs font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Calculator className="w-4 h-4 text-[#1E40AF]" />
                  Dars Soatlari Hisobi
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-gray-700 block mb-1">
                      Choraklik Jami Soat:
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="120"
                      value={quarterHours}
                      onChange={(e) => setQuarterHours(Number(e.target.value))}
                      className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-700 block mb-1">
                      Chorakdagi Haftalar:
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="15"
                      value={weeksInTerm}
                      onChange={(e) => setWeeksInTerm(Number(e.target.value))}
                      className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                    />
                  </div>
                </div>

                {/* Avtomatik hisoblangan haftalik dars */}
                <div className="bg-white p-3 rounded-lg border border-blue-200 flex items-center justify-between text-xs">
                  <span className="text-gray-600 font-medium">Haftalik dars jadvaliga tushadigan soat:</span>
                  <span className="font-black text-sm text-[#1E40AF] bg-blue-50 px-2 py-0.5 rounded">
                    {calculatedWeeklyHours} soat / hafta
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-gray-500">
                  Kuniga maksimal: <strong>{maxDaily} soat</strong>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 text-sm bg-[#10B981] hover:bg-emerald-600 text-white font-medium rounded-xl shadow transition"
                  >
                    {isSubmitting ? "Saqlanmoqda..." : "Biriktirish"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
