'use client';

import React, { useState, useMemo, useEffect } from 'react';
import {
  Plus,
  Users,
  Clock,
  Trash2,
  Edit3,
  X,
  Check,
  ArrowUpDown,
  BookOpen,
  DoorOpen,
  User,
  GraduationCap,
  Sparkles,
  Calendar,
  AlertCircle,
  RotateCcw,
  Globe
} from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';
import { curriculumApi, classesApi } from '@/lib/api';
import {
  filterTeachersForSubject,
  getAvailableRoomsForClass,
  getRecommendedRoomId
} from '@/lib/subjectUtils';

export interface ClassItem {
  id: string;
  name: string;
  gradeLevel: number;
  studentCount: number;
  shift: '1-smena' | '2-smena';
  language?: 'UZBEK' | 'RUSSIAN' | 'QARDOSH';
  classMaster?: string;
}

export interface ClassSubjectItem {
  id: string;
  classId: string;
  className: string;
  subjectId: string;
  subjectName: string;
  subjectCode: string;
  colorHex: string;
  teacherId: string;
  teacherName: string;
  roomNumber?: string;
  weeklyHours: number;
  quarterTotalHours: number;
  weeksInQuarter: number;
}

export const ClassesModule: React.FC = () => {
  const { classes, addClass, updateClass, deleteClass, teachers, subjects, rooms } = useSchoolData();

  // Barcha sinflarning o'tiladigan fanlari (allocations)
  const [allocations, setAllocations] = useState<ClassSubjectItem[]>([]);
  const [isLoadingAllocs, setIsLoadingAllocs] = useState(false);

  // Tanlangan sinf (uning fanlarini to'liq ko'rish va boshqarish modali)
  const [selectedClass, setSelectedClass] = useState<ClassItem | null>(null);

  // Tanlangan sinf ichida yangi fan qo'shish formasi
  const [isAddingSubject, setIsAddingSubject] = useState(false);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [selectedTeacherId, setSelectedTeacherId] = useState('');
  const [selectedRoomId, setSelectedRoomId] = useState('');
  const [newWeeklyHours, setNewWeeklyHours] = useState(4);
  const [isSubmittingSubject, setIsSubmittingSubject] = useState(false);

  // Yangi sinf yaratish modali
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState('');
  const [gradeLevel, setGradeLevel] = useState(5);
  const [studentCount, setStudentCount] = useState(28);
  const [shift, setShift] = useState<'1-smena' | '2-smena'>('1-smena');
  const [language, setLanguage] = useState<'UZBEK' | 'RUSSIAN' | 'QARDOSH'>('UZBEK');
  const [classMaster, setClassMaster] = useState(teachers[0]?.fullName || 'Tayinlanmagan');

  // Sinfni tahrirlash (Edit) holati
  const [isEditingClassInfo, setIsEditingClassInfo] = useState(false);
  const [editName, setEditName] = useState('');
  const [editGradeLevel, setEditGradeLevel] = useState(5);
  const [editStudentCount, setEditStudentCount] = useState(28);
  const [editShift, setEditShift] = useState<'1-smena' | '2-smena'>('1-smena');
  const [editLanguage, setEditLanguage] = useState<'UZBEK' | 'RUSSIAN' | 'QARDOSH'>('UZBEK');
  const [editClassMaster, setEditClassMaster] = useState('');
  const [isApplyingCurriculum, setIsApplyingCurriculum] = useState(false);

  // 1. O'QUV REJASINI (FANLARNI) BACKENDDAN YUKLASH
  const fetchAllocations = async () => {
    setIsLoadingAllocs(true);
    try {
      const data = await curriculumApi.getAll();
      if (data && Array.isArray(data)) {
        setAllocations(
          data.map((item: any) => ({
            id: item.id,
            classId: item.class_id,
            className: item.class_name,
            subjectId: item.subject_id,
            subjectName: item.subject_name,
            subjectCode: item.subject_code,
            colorHex: item.color_hex || '#1E40AF',
            teacherId: item.teacher_id,
            teacherName: item.teacher_name,
            roomNumber: item.room_number,
            weeklyHours: item.weekly_hours,
            quarterTotalHours: item.quarter_total_hours,
            weeksInQuarter: item.weeks_in_quarter || 9,
          }))
        );
      }
    } catch (err) {
      console.warn("O'quv rejasi yuklanmadi:", err);
    } finally {
      setIsLoadingAllocs(false);
    }
  };

  useEffect(() => {
    fetchAllocations();
  }, []);

  // 2. SINFLARNI BOSQICHI (GRADE) BO'YICHA KICHIKDAN KATTAGA TARTIBLASH
  const sortedClasses = useMemo(() => {
    return [...classes].sort((a, b) => {
      if (a.gradeLevel !== b.gradeLevel) {
        return a.gradeLevel - b.gradeLevel;
      }
      return a.name.localeCompare(b.name, 'uz', { numeric: true });
    });
  }, [classes]);

  // Har bir sinf uchun fanlar xaritasi (qidiruv tezligi uchun)
  const classAllocationsMap = useMemo(() => {
    const map = new Map<string, ClassSubjectItem[]>();
    for (const alloc of allocations) {
      // ham ID, ham Name bo'yicha bog'laymiz
      const keys = [alloc.classId, alloc.className];
      for (const k of keys) {
        if (!k) continue;
        const cur = map.get(k) || [];
        if (!cur.some((x) => x.id === alloc.id)) {
          cur.push(alloc);
          map.set(k, cur);
        }
      }
    }
    return map;
  }, [allocations]);

  // Tanlangan sinfga tegishli fanlar
  const currentClassSubjects = useMemo(() => {
    if (!selectedClass) return [];
    return classAllocationsMap.get(selectedClass.id) || classAllocationsMap.get(selectedClass.name) || [];
  }, [selectedClass, classAllocationsMap]);

  // Tanlangan sinfning umumiy haftalik soatlari
  const totalWeeklyHours = useMemo(() => {
    return currentClassSubjects.reduce((sum, item) => sum + (item.weeklyHours || 0), 0);
  }, [currentClassSubjects]);

  // Yangi sinf qo'shish
  const handleAddClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const newClass: ClassItem = {
      id: `c_${Date.now()}`,
      name: name.trim(),
      gradeLevel: Number(gradeLevel),
      studentCount: Number(studentCount),
      shift,
      language,
      classMaster: classMaster || 'Tayinlanmagan',
    };

    addClass(newClass);
    setShowAddModal(false);
    setName('');
    setLanguage('UZBEK');
    setClassMaster(teachers[0]?.fullName || 'Tayinlanmagan');

    // Yangi sinf uchun avtomatik yaratilgan o'quv rejasini qayta yuklaymiz
    setTimeout(() => {
      fetchAllocations();
    }, 600);
  };

  // Davlat tayanch o'quv rejasini qayta qo'llash
  const handleReapplyTemplateCurriculum = async (cls: ClassItem) => {
    if (!cls?.id) return;
    setIsApplyingCurriculum(true);
    try {
      await classesApi.applyCurriculum(cls.id);
      await fetchAllocations();
    } catch (err) {
      console.warn("Davlat o'quv rejasini qo'llashda xatolik:", err);
    } finally {
      setIsApplyingCurriculum(false);
    }
  };

  // Tanlangan fanning mutaxassis o'qituvchilari (Faqat shu fanni o'tadiganlar)
  const availableTeachers = useMemo(() => {
    if (!selectedSubjectId) return [];
    const subj = subjects.find((s) => s.id === selectedSubjectId);
    return filterTeachersForSubject(teachers, subj);
  }, [teachers, subjects, selectedSubjectId]);

  // Tanlangan sinf uchun ruxsat etilgan xonalar: faqat shaxsiy xonasi yoki laboratoriya/maxsus xonalar
  const availableRooms = useMemo(() => {
    if (!selectedClass) return rooms.filter((r) => r.roomType !== 'GENERAL');
    return getAvailableRoomsForClass(selectedClass.name, rooms);
  }, [rooms, selectedClass]);

  // Sinf ustiga bosilganda uning fanlari modalini ochish
  const handleOpenClassDetail = async (cls: ClassItem) => {
    setSelectedClass(cls);
    setIsAddingSubject(false);
    setIsEditingClassInfo(false);
    setEditName(cls.name);
    setEditGradeLevel(cls.gradeLevel);
    setEditStudentCount(cls.studentCount);
    setEditShift(cls.shift);
    setEditLanguage(cls.language || 'UZBEK');
    setEditClassMaster(cls.classMaster || 'Biriktirilmagan');

    // Ushbu sinfning fanlarini to'g'ridan-to'g'ri yangilash
    try {
      const classAllocs = await curriculumApi.getByClass(cls.id);
      if (classAllocs && Array.isArray(classAllocs) && classAllocs.length > 0) {
        setAllocations((prev) => {
          const others = prev.filter((a) => a.classId !== cls.id && a.className !== cls.name);
          const formatted = classAllocs.map((item: any) => ({
            id: item.id,
            classId: item.class_id,
            className: item.class_name,
            subjectId: item.subject_id,
            subjectName: item.subject_name,
            subjectCode: item.subject_code,
            colorHex: item.color_hex || '#1E40AF',
            teacherId: item.teacher_id,
            teacherName: item.teacher_name,
            roomNumber: item.room_number,
            weeklyHours: item.weekly_hours,
            quarterTotalHours: item.quarter_total_hours,
            weeksInQuarter: item.weeks_in_quarter || 9,
          }));
          return [...others, ...formatted];
        });
      }
    } catch (err) {
      console.warn("Sinf fanlarini yuklashda xatolik:", err);
    }

    // Formani boshlang'ich qiymatlarga moslash:
    if (subjects.length > 0) {
      const firstSubj = subjects[0];
      setSelectedSubjectId(firstSubj.id);
      
      const matchedTeachers = filterTeachersForSubject(teachers, firstSubj);
      setSelectedTeacherId(matchedTeachers[0]?.id || '');

      const classRooms = getAvailableRoomsForClass(cls.name, rooms);
      setSelectedRoomId(getRecommendedRoomId(firstSubj, cls.name, classRooms));
    }
  };

  // Fan tanlanganda faqat o'sha fanning o'qituvchisini va mos xonasini avtomatik tanlash
  const handleSubjectChange = (subjId: string) => {
    setSelectedSubjectId(subjId);
    const subj = subjects.find((s) => s.id === subjId);
    if (subj) {
      const matched = filterTeachersForSubject(teachers, subj);
      setSelectedTeacherId(matched[0]?.id || '');
      if (selectedClass) {
        const classRooms = getAvailableRoomsForClass(selectedClass.name, rooms);
        setSelectedRoomId(getRecommendedRoomId(subj, selectedClass.name, classRooms));
      }
    }
  };

  // Sinfga yangi fan biriktirish
  const handleAllocateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass || !selectedSubjectId || !selectedTeacherId) return;

    const subj = subjects.find((s) => s.id === selectedSubjectId);
    const teacher = teachers.find((t) => t.id === selectedTeacherId);
    const room = rooms.find((r) => r.id === selectedRoomId);

    if (!subj || !teacher) return;

    setIsSubmittingSubject(true);
    try {
      const res = await curriculumApi.allocate({
        class_id: selectedClass.id,
        subject_id: subj.id,
        teacher_id: teacher.id,
        preferred_room_id: room?.id,
        term: 1,
        quarter_total_hours: newWeeklyHours * 9,
        weeks_in_quarter: 9,
        weekly_hours: newWeeklyHours,
        max_hours_per_day: 2,
      });

      const newAllocItem: ClassSubjectItem = {
        id: res.id || `alloc_${Date.now()}`,
        classId: selectedClass.id,
        className: selectedClass.name,
        subjectId: subj.id,
        subjectName: subj.name,
        subjectCode: subj.code,
        colorHex: subj.colorHex,
        teacherId: teacher.id,
        teacherName: teacher.fullName,
        roomNumber: room?.roomNumber,
        weeklyHours: newWeeklyHours,
        quarterTotalHours: newWeeklyHours * 9,
        weeksInQuarter: 9,
      };

      setAllocations((prev) => [...prev, newAllocItem]);
      setIsAddingSubject(false);
    } catch (err: any) {
      alert("Fanni biriktirishda xatolik: " + (err.message || 'Server xatosi'));
    } finally {
      setIsSubmittingSubject(false);
    }
  };

  // Sinf faniga o'qituvchi biriktirish yoki o'zgartirish
  const handleAssignTeacherToSubject = async (allocationId: string, teacherId: string) => {
    try {
      const teacher = teachers.find((t) => t.id === teacherId);
      // Optimistik yangilash
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
    } catch (err: any) {
      console.error("O'qituvchini biriktirishda xatolik:", err);
      alert("O'qituvchini biriktirishda xatolik yuz berdi");
    }
  };

  // Sinfdan fanni olib tashlash (Delete Allocation)
  const handleDeleteAllocation = async (allocationId: string, subjectName: string) => {
    if (!confirm(`Haqiqatan ham "${subjectName}" fanini ushbu sinf o'quv rejasidan olib tashlamoqchimisiz?`)) {
      return;
    }

    try {
      await curriculumApi.deleteAllocation(allocationId);
      setAllocations((prev) => prev.filter((a) => a.id !== allocationId));
    } catch (err) {
      alert("O'chirishda xatolik yuz berdi");
    }
  };

  // Sinf ma'lumotlarini tahrirlashni saqlash
  const handleSaveClassEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass || !editName) return;

    updateClass(selectedClass.id, {
      name: editName,
      gradeLevel: Number(editGradeLevel),
      studentCount: Number(editStudentCount),
      shift: editShift,
      language: editLanguage,
      classMaster: editClassMaster,
    });

    setSelectedClass({
      ...selectedClass,
      name: editName,
      gradeLevel: Number(editGradeLevel),
      studentCount: Number(editStudentCount),
      shift: editShift,
      language: editLanguage,
      classMaster: editClassMaster,
    });

    setIsEditingClassInfo(false);
  };

  const handleDeleteClass = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Sinfni o'chirmoqchimisiz?")) {
      deleteClass(id);
      if (selectedClass?.id === id) {
        setSelectedClass(null);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Yuqori Panel */}
      <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-gray-900 text-lg">Maktab Sinflari & O'tiladigan Fanlar</h3>
            <span className="text-[11px] font-semibold text-[#1E40AF] bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full flex items-center gap-1">
              <ArrowUpDown className="w-3 h-3" />
              Kichikdan kattaga tartiblangan
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Jami <span className="font-bold text-gray-900">{classes.length} ta sinf</span>. Sinf ustiga bosib, <span className="text-[#1E40AF] font-bold">unga o'tiladigan fanlar ro'yxatini</span> ko'rishingiz va yangi fan biriktirishingiz mumkin.
          </p>
        </div>

        <button
          onClick={() => {
            setClassMaster(teachers[0]?.fullName || 'Tayinlanmagan');
            setShowAddModal(true);
          }}
          className="flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-medium text-sm px-5 py-2.5 rounded-xl shadow-sm transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Yangi Sinf Qo'shish</span>
        </button>
      </div>

      {/* Sinflar Kartalari Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {sortedClasses.map((cls) => {
          const classSubs = classAllocationsMap.get(cls.id) || classAllocationsMap.get(cls.name) || [];
          const weeklySum = classSubs.reduce((sum, s) => sum + s.weeklyHours, 0);

          return (
            <div
              key={cls.id}
              onClick={() => handleOpenClassDetail(cls)}
              className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200/90 shadow-sm hover:shadow-lg hover:border-[#1E40AF] transition-all cursor-pointer relative group overflow-hidden flex flex-col justify-between"
            >
              {/* Hoverda Fanlarni ko'rish ko'rsatkichi */}
              <div className="absolute top-3 right-12 opacity-0 group-hover:opacity-100 transition flex items-center gap-1 text-[11px] font-bold text-[#1E40AF] bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-lg shadow-xs">
                <BookOpen className="w-3 h-3 text-[#1E40AF]" />
                <span>Fanlarni ko'rish</span>
              </div>

              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#1E40AF] font-black text-lg flex items-center justify-center border border-blue-100 group-hover:scale-105 transition">
                      {cls.name}
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 text-base group-hover:text-[#1E40AF] transition">
                        {cls.gradeLevel}-sinf ({cls.name})
                      </h4>
                      <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                        <span className="flex items-center gap-1 font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                          <Clock className="w-3 h-3" />
                          {cls.shift}
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-100 flex items-center gap-1">
                          <Globe className="w-2.5 h-2.5" />
                          {cls.language === 'RUSSIAN' ? "Rus tili" : cls.language === 'QARDOSH' ? "Qardosh til" : "O'zbek tili"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* O'chirish tugmasi */}
                  <button
                    onClick={(e) => handleDeleteClass(e, cls.id)}
                    className="opacity-0 group-hover:opacity-100 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="Sinfni o'chirish"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* O'tiladigan fanlar ko'rsatkichi (Pills) */}
                <div className="mt-4 pt-3 border-t border-gray-100">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="font-semibold text-gray-700 flex items-center gap-1">
                      <BookOpen className="w-3.5 h-3.5 text-[#1E40AF]" />
                      O'tiladigan fanlar:
                    </span>
                    <span className="text-[11px] font-bold text-[#1E40AF] bg-blue-50 px-2 py-0.5 rounded-full">
                      {classSubs.length} ta fan • {weeklySum} soat/hafta
                    </span>
                  </div>

                  {classSubs.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {classSubs.slice(0, 4).map((s) => (
                        <span
                          key={s.id}
                          className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-gray-50 text-gray-700 border border-gray-200"
                        >
                          {s.subjectName} <span className="text-gray-400 font-bold">({s.weeklyHours}s)</span>
                        </span>
                      ))}
                      {classSubs.length > 4 && (
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-blue-50 text-[#1E40AF] border border-blue-200">
                          +{classSubs.length - 4} yana
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 italic">Hali fanlar biriktirilmagan (bosing va qo'shing)</p>
                  )}
                </div>
              </div>

              {/* Pastki qism: O'quvchilar va Rahbar */}
              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                <div className="text-gray-600 flex items-center gap-1.5 font-medium">
                  <Users className="w-3.5 h-3.5 text-gray-400" />
                  <span>{cls.studentCount} o'quvchi</span>
                </div>
                <div className="text-gray-500 truncate max-w-[140px] text-right">
                  Rahbar: <span className="font-bold text-gray-800">{cls.classMaster}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* ASOSIY MODAL: TANLANGAN SINF TAFSILOTLARI VA UNGA O'TILADIGAN FANLAR      */}
      {/* ========================================================================= */}
      {selectedClass && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
          <div className="bg-[#FFFFFF] rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 max-h-[92vh] flex flex-col">
            
            {/* Modal Sarlavhasi va Boshqaruv */}
            <div className="flex items-start justify-between pb-4 border-b border-gray-100">
              <div className="flex items-center gap-3.5">
                <div className="w-14 h-14 rounded-2xl bg-[#1E40AF] text-white font-black text-2xl flex items-center justify-center shadow-md">
                  {selectedClass.name}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-bold text-gray-900">
                      {selectedClass.name} — O'tiladigan Fanlar va O'quv Rejasi
                    </h3>
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-md">
                      {selectedClass.shift}
                    </span>
                    <span className="text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {selectedClass.language === 'RUSSIAN' ? "Rus tili" : selectedClass.language === 'QARDOSH' ? "Qardosh til" : "O'zbek tili"}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 flex items-center gap-3">
                    <span>Bosqich: <strong className="text-gray-800">{selectedClass.gradeLevel}-sinf</strong></span>
                    <span>•</span>
                    <span>O'quvchilar: <strong className="text-gray-800">{selectedClass.studentCount} nafar</strong></span>
                    <span>•</span>
                    <span>Rahbar: <strong className="text-gray-800">{selectedClass.classMaster}</strong></span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsEditingClassInfo(!isEditingClassInfo)}
                  className={`p-2 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition ${
                    isEditingClassInfo
                      ? 'bg-blue-50 border-[#1E40AF] text-[#1E40AF]'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                  title="Sinf ma'lumotlarini tahrirlash"
                >
                  <Edit3 className="w-4 h-4" />
                  <span className="hidden sm:inline">Tahrirlash</span>
                </button>
                <button
                  onClick={() => setSelectedClass(null)}
                  className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Sinf ma'lumotlarini tezkor tahrirlash (ochilganda) */}
            {isEditingClassInfo && (
              <form onSubmit={handleSaveClassEdit} className="bg-gray-50 p-4 rounded-xl border border-gray-200 mt-4 space-y-3">
                <div className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                  <Edit3 className="w-3.5 h-3.5 text-[#1E40AF]" />
                  Sinf asosiy ma'lumotlarini o'zgartirish:
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <label className="text-[11px] font-semibold text-gray-600 block mb-1">Nomi:</label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-gray-600 block mb-1">Bosqich:</label>
                    <input
                      type="number"
                      value={editGradeLevel}
                      onChange={(e) => setEditGradeLevel(Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-gray-600 block mb-1">O'quvchilar soni:</label>
                    <input
                      type="number"
                      value={editStudentCount}
                      onChange={(e) => setEditStudentCount(Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-gray-600 block mb-1">Smena:</label>
                    <select
                      value={editShift}
                      onChange={(e) => setEditShift(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 bg-white border border-gray-300 rounded-lg text-sm font-medium focus:ring-2 focus:ring-[#1E40AF] outline-none"
                    >
                      <option value="1-smena">1-smena</option>
                      <option value="2-smena">2-smena</option>
                    </select>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-semibold text-gray-600">Ta'lim tili:</label>
                      <select
                        value={editLanguage}
                        onChange={(e) => setEditLanguage(e.target.value as any)}
                        className="px-3 py-1 bg-white border border-gray-300 rounded-lg text-xs font-semibold text-gray-800 outline-none"
                      >
                        <option value="UZBEK">O'zbek tili</option>
                        <option value="RUSSIAN">Rus tili</option>
                        <option value="QARDOSH">Qardosh til</option>
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-semibold text-gray-600">Rahbar:</label>
                      <select
                        value={editClassMaster}
                        onChange={(e) => setEditClassMaster(e.target.value)}
                        className="px-3 py-1 bg-white border border-gray-300 rounded-lg text-xs font-semibold text-gray-800 outline-none"
                      >
                        <option value="Tayinlanmagan">Tayinlanmagan</option>
                        {teachers.map((t) => (
                          <option key={t.id} value={t.fullName}>
                            {t.fullName} ({t.subject})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setIsEditingClassInfo(false)}
                      className="px-3 py-1 text-xs text-gray-600 hover:bg-gray-200 rounded-lg"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-1 text-xs bg-[#1E40AF] hover:bg-blue-800 text-white font-bold rounded-lg shadow-xs"
                    >
                      Saqlash
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* Statistika Qatori */}
            <div className="grid grid-cols-3 gap-3 my-4">
              <div className="bg-blue-50/70 border border-blue-100 rounded-xl p-3 text-center">
                <span className="text-[11px] font-medium text-blue-700 block">Jami Fanlar</span>
                <span className="text-lg font-black text-[#1E40AF]">{currentClassSubjects.length} ta fan</span>
              </div>
              <div className="bg-emerald-50/70 border border-emerald-100 rounded-xl p-3 text-center">
                <span className="text-[11px] font-medium text-emerald-700 block">Haftalik Yuklama</span>
                <span className="text-lg font-black text-emerald-800">{totalWeeklyHours} soat / hafta</span>
              </div>
              <div className="bg-purple-50/70 border border-purple-100 rounded-xl p-3 text-center">
                <span className="text-[11px] font-medium text-purple-700 block">Choraklik Jami</span>
                <span className="text-lg font-black text-purple-800">{totalWeeklyHours * 9} soat</span>
              </div>
            </div>

            {/* Yangi Fan Qo'shish Tugmasi va Formasi */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-bold text-gray-900 text-sm flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-[#1E40AF]" />
                  Ushbu sinfga biriktirilgan fanlar ro'yxati
                </h4>
                <button
                  onClick={() => setIsAddingSubject(!isAddingSubject)}
                  className="flex items-center gap-1.5 text-xs font-bold text-[#10B981] hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded-xl transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{isAddingSubject ? "Yopish" : "+ Fan biriktirish"}</span>
                </button>
              </div>

              {/* Inline Yangi Fan Biriktirish Formasi */}
              {isAddingSubject && (
                <form
                  onSubmit={handleAllocateSubject}
                  className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-200 space-y-3 mb-4 animate-in fade-in"
                >
                  <div className="text-xs font-bold text-emerald-900 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{selectedClass.name} sinfiga yangi fan va o'qituvchi biriktirish:</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-gray-700 block mb-1">Fan:</label>
                      <select
                        value={selectedSubjectId}
                        onChange={(e) => handleSubjectChange(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-xl text-xs font-bold text-gray-900 outline-none focus:ring-2 focus:ring-[#10B981]"
                      >
                        {subjects.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name} ({s.code})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-gray-700 block mb-1">
                        O'qituvchi ({availableTeachers.length} nafar):
                      </label>
                      <select
                        value={selectedTeacherId}
                        onChange={(e) => setSelectedTeacherId(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-xl text-xs font-bold text-gray-900 outline-none focus:ring-2 focus:ring-[#10B981]"
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

                    <div>
                      <label className="text-[11px] font-semibold text-gray-700 block mb-1">Haftalik soat:</label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={newWeeklyHours}
                        onChange={(e) => setNewWeeklyHours(Number(e.target.value))}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-xl text-xs font-bold text-gray-900 outline-none focus:ring-2 focus:ring-[#10B981]"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-gray-700 block mb-1">
                        Xona (shaxsiy yoki laboratoriya):
                      </label>
                      <select
                        value={selectedRoomId}
                        onChange={(e) => setSelectedRoomId(e.target.value)}
                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-xl text-xs font-bold text-gray-900 outline-none focus:ring-2 focus:ring-[#10B981]"
                      >
                        <option value="">Biriktirilmagan</option>
                        {availableRooms.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.roomNumber} ({r.name})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsAddingSubject(false)}
                      className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-lg transition"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmittingSubject}
                      className="px-5 py-1.5 text-xs bg-[#10B981] hover:bg-emerald-600 text-white font-bold rounded-xl shadow transition"
                    >
                      {isSubmittingSubject ? "Saqlanmoqda..." : "Fanni Biriktirish"}
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Fanlar Ro'yxati (Scrollable Grid) */}
            <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
              {currentClassSubjects.length > 0 ? (
                currentClassSubjects.map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 rounded-xl border border-gray-200 bg-white hover:border-[#1E40AF]/40 hover:bg-blue-50/20 transition flex items-center justify-between gap-3 shadow-2xs"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center font-black text-white text-xs shadow-xs"
                        style={{ backgroundColor: item.colorHex || '#1E40AF' }}
                      >
                        {item.subjectCode || 'FAN'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h5 className="font-bold text-gray-900 text-sm">{item.subjectName}</h5>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-gray-100 text-gray-700">
                            {item.weeklyHours} soat / hafta
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-1.5">
                          {/* O'qituvchi tanlash / biriktirish */}
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
                              onChange={(e) => handleAssignTeacherToSubject(item.id, e.target.value)}
                              className="bg-transparent outline-none cursor-pointer text-xs font-bold"
                              title="Fanga o'qituvchi biriktirish"
                            >
                              <option value="">O'qituvchi biriktirilmagan (Tanlang...)</option>
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

                          {item.roomNumber && (
                            <span className="flex items-center gap-1 text-xs text-gray-500 bg-gray-50 border border-gray-200 px-2 py-1 rounded-lg">
                              <DoorOpen className="w-3 h-3 text-gray-400" />
                              {item.roomNumber}
                            </span>
                          )}
                          <span className="text-[11px] text-gray-400">
                            (Chorakda: {item.quarterTotalHours} soat)
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteAllocation(item.id, item.subjectName)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                      title="Fanni sinfdan olib tashlash"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                  <BookOpen className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-gray-700">Ushbu sinfga hali fanlar biriktirilmagan</p>
                  <p className="text-xs text-gray-400 mt-0.5 mb-3">
                    Tepadagi <strong>"+ Fan biriktirish"</strong> tugmasi orqali darslar taqsimotini kiriting
                  </p>
                  <button
                    onClick={() => setIsAddingSubject(true)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-[#10B981] hover:bg-emerald-600 px-4 py-2 rounded-xl shadow-xs transition"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Fan Biriktirish</span>
                  </button>
                </div>
              )}
            </div>

            {/* Modal Pastki Tugmasi */}
            <div className="pt-4 border-t border-gray-100 mt-4 flex items-center justify-between">
              <span className="text-xs text-gray-400">
                O'zgarishlar PostgreSQL Neon ma'lumotlar bazasida avtomatik saqlanadi.
              </span>
              <button
                onClick={() => setSelectedClass(null)}
                className="px-5 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold rounded-xl transition"
              >
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: YANGI SINF YARATISH                                              */}
      {/* ========================================================================= */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <h3 className="text-lg font-bold text-[#1E40AF]">Yangi Sinf Qo'shish</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 text-gray-400 hover:text-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddClass} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Sinf Nomi:</label>
                  <input
                    type="text"
                    required
                    placeholder="Masalan: 5-A"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-bold"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Bosqich (Grade):</label>
                  <input
                    type="number"
                    min="1"
                    max="11"
                    value={gradeLevel}
                    onChange={(e) => setGradeLevel(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">O'quvchilar soni:</label>
                  <input
                    type="number"
                    min="1"
                    value={studentCount}
                    onChange={(e) => setStudentCount(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-bold"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Smena:</label>
                  <select
                    value={shift}
                    onChange={(e) => setShift(e.target.value as any)}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none bg-white font-medium"
                  >
                    <option value="1-smena">1-smena (Ertalab)</option>
                    <option value="2-smena">2-smena (Tushdan keyin)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">
                  Ta'lim tili (O'qitish tili):
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-semibold text-gray-900"
                >
                  <option value="UZBEK">🇺🇿 O'zbek tili (1-ilova standarti)</option>
                  <option value="RUSSIAN">🇷🇺 Rus tili (2-ilova standarti)</option>
                  <option value="QARDOSH">🌐 Qardosh til — qozoq, tojik, qirg'iz, turkman (3-ilova standarti)</option>
                </select>
                <div className="mt-2 p-2.5 bg-blue-50/80 border border-blue-200/70 rounded-xl text-xs text-blue-800 flex items-start gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <span>
                    <strong>2026-2027 davlat o'quv rejasi:</strong> Sinf yaratilganda tanlangan til va bosqichga mos barcha fanlar hamda haftalik dars soatlari avtomatik kiritiladi.
                  </span>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">
                  Sinf Rahbari:
                </label>
                <select
                  value={classMaster}
                  onChange={(e) => setClassMaster(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-semibold text-gray-900"
                >
                  <option value="Tayinlanmagan">Tayinlanmagan</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.fullName}>
                      {t.fullName} ({t.subject})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-[#10B981] hover:bg-emerald-600 text-white font-medium rounded-xl shadow transition"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
