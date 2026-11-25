'use client';

import React, { useState, useMemo } from 'react';
import {
  Plus,
  BookOpen,
  Users,
  Phone,
  Mail,
  X,
  ChevronRight,
  DoorOpen,
  Trash2,
  UserPlus,
  ArrowUpDown
} from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';
import { TeacherItem } from '@/components/teachers/TeachersModule';

export interface SubjectItem {
  id: string;
  name: string;
  code: string;
  colorHex: string;
  requiredRoom: string;
}

export const SubjectsModule: React.FC = () => {
  const { teachers, addTeacher, deleteTeacher, subjects, addSubject, deleteSubject } = useSchoolData();

  // Yangi butunlay yangi fan qo'shish modali
  const [showAddSubjectModal, setShowAddSubjectModal] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [colorHex, setColorHex] = useState('#1E40AF');
  const [requiredRoom, setRequiredRoom] = useState('Oddiy xona');

  // Tanlangan fan (o'qituvchilarni ko'rish)
  const [selectedSubject, setSelectedSubject] = useState<SubjectItem | null>(null);

  // Modal ichida o'qituvchi qo'shish formasi ochiqligi
  const [isAddingTeacher, setIsAddingTeacher] = useState(false);
  const [teacherFullName, setTeacherFullName] = useState('');
  const [teacherPhone, setTeacherPhone] = useState('');
  const [teacherWeeklyHours, setTeacherWeeklyHours] = useState(20);

  // 3. FANLARNI ALIFBO BO'YICHA TARTIBLASH (A-Z)
  const sortedSubjects = useMemo(() => {
    return [...subjects].sort((a, b) => a.name.localeCompare(b.name, 'uz'));
  }, [subjects]);

  // Yangi fan kiritish
  const handleAddSubject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !code) return;

    const newSub: SubjectItem = {
      id: `s_${Date.now()}`,
      name,
      code: code.toUpperCase(),
      colorHex,
      requiredRoom,
    };

    addSubject(newSub);
    setShowAddSubjectModal(false);
    setName('');
    setCode('');
  };

  // Tanlangan fanga yangi o'qituvchi qo'shish
  const handleAddTeacherToSelectedSubject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSubject || !teacherFullName) return;

    const newTeacher: TeacherItem = {
      id: `t_${Date.now()}`,
      fullName: teacherFullName,
      subject: selectedSubject.name,
      email: `${teacherFullName.toLowerCase().replace(/\s+/g, '.')}@maktab142.uz`,
      phone: teacherPhone || '+998 90 000 00 00',
      weeklyHours: Number(teacherWeeklyHours),
      maxDailyHours: 4,
      availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
    };

    addTeacher(newTeacher);
    setIsAddingTeacher(false);
    setTeacherFullName('');
    setTeacherPhone('');
    setTeacherWeeklyHours(20);
  };

  // Birorta fandan dars beruvchi o'qituvchilarni aniq topish (soxta o'xshashliksiz)
  const getTeachersForSubject = (subjectName: string): TeacherItem[] => {
    if (!subjectName) return [];
    const sSub = subjectName.toLowerCase().replace(/['`ʻ’]/g, '').trim();
    return teachers.filter((t) => {
      const tSub = (t.subject || '').toLowerCase().replace(/['`ʻ’]/g, '').trim();
      if (tSub === sSub) return true;
      // Agar o'qituvchiga bir nechta fan biriktirilgan bo'lsa (vergul bilan)
      const list = tSub.split(/[,/;&]+/).map((x) => x.trim());
      return list.includes(sSub);
    });
  };

  return (
    <div className="space-y-6">
      {/* Yuqori Toolbar */}
      <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-gray-900 text-lg">Fanlar & O'qituvchilar Katalogi</h3>
            <span className="text-[11px] font-semibold text-[#1E40AF] bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full flex items-center gap-1">
              <ArrowUpDown className="w-3 h-3" />
              Alifbo bo'yicha (A-Z)
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Fanning ustiga bosib, undan dars beruvchi o'qituvchilarni ko'rishingiz va yangi o'qituvchi biriktirishingiz mumkin
          </p>
        </div>

        <button
          onClick={() => setShowAddSubjectModal(true)}
          className="flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-medium text-sm px-5 py-2.5 rounded-xl shadow-sm transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Yangi Fan Qo'shish</span>
        </button>
      </div>

      {/* Fanlar Grid Kartalari (Alifbo bo'yicha tartiblangan) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {sortedSubjects.map((sub) => {
          const subjectTeachers = getTeachersForSubject(sub.name);

          return (
            <div
              key={sub.id}
              onClick={() => {
                setSelectedSubject(sub);
                setIsAddingTeacher(false);
              }}
              className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200/90 shadow-sm hover:shadow-lg hover:border-[#1E40AF]/50 transition-all cursor-pointer group relative overflow-hidden"
            >
              <div
                style={{ backgroundColor: sub.colorHex }}
                className="absolute top-0 left-0 right-0 h-1.5 group-hover:h-2 transition-all"
              />

              <div className="flex items-center justify-between mt-1">
                <div className="flex items-center gap-3">
                  <div
                    style={{ backgroundColor: sub.colorHex }}
                    className="w-11 h-11 rounded-xl text-white font-black flex items-center justify-center text-xs shadow-md shadow-blue-500/10 group-hover:scale-105 transition"
                  >
                    {sub.code}
                  </div>
                  <div>
                    <h4 className="font-extrabold text-gray-900 text-base group-hover:text-[#1E40AF] transition">
                      {sub.name}
                    </h4>
                    <div className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                      <DoorOpen className="w-3.5 h-3.5 text-gray-400" />
                      <span>{sub.requiredRoom}</span>
                    </div>
                  </div>
                </div>

                <div
                  style={{ backgroundColor: `${sub.colorHex}18`, color: sub.colorHex }}
                  className="text-xs font-mono font-bold px-2 py-0.5 rounded-md"
                >
                  {sub.colorHex}
                </div>
              </div>

              <div className="mt-4 pt-3.5 border-t border-gray-100 flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-gray-700">
                  <Users className="w-4 h-4 text-gray-400" />
                  <span>
                    {subjectTeachers.length > 0 ? (
                      <span className="text-[#1E40AF] font-bold">{subjectTeachers.length} nafar o'qituvchi</span>
                    ) : (
                      <span className="text-gray-400 font-normal">O'qituvchi yo'q</span>
                    )}
                  </span>
                </div>

                <div className="text-[11px] font-bold text-[#10B981] flex items-center gap-0.5 group-hover:translate-x-1 transition">
                  <span>Ko'rish</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* MODAL 1: FANNING O'QITUVCHILARI VA SHU YERNING O'ZIDA QO'SHISH FORMASI */}
      {selectedSubject && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 max-h-[92vh] flex flex-col overflow-hidden">
            
            {/* Modal Sarlavhasi */}
            <div className="flex items-start justify-between pb-4 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div
                  style={{ backgroundColor: selectedSubject.colorHex }}
                  className="w-12 h-12 rounded-xl text-white font-black text-sm flex items-center justify-center shadow"
                >
                  {selectedSubject.code}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-black text-gray-900">{selectedSubject.name}</h3>
                    <span
                      style={{
                        backgroundColor: `${selectedSubject.colorHex}20`,
                        color: selectedSubject.colorHex,
                      }}
                      className="text-xs font-mono font-bold px-2 py-0.5 rounded"
                    >
                      {selectedSubject.code}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Talab qilinadigan xona turi: <strong>{selectedSubject.requiredRoom}</strong>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  title="Fanni o'chirish"
                  onClick={() => {
                    if (confirm(`"${selectedSubject.name}" fanini bazadan o'chirishni xohlaysizmi?`)) {
                      deleteSubject(selectedSubject.id);
                      setSelectedSubject(null);
                    }
                  }}
                  className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
                <button
                  onClick={() => {
                    setSelectedSubject(null);
                    setIsAddingTeacher(false);
                  }}
                  className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* O'qituvchilar bo'limi boshqaruvi */}
            <div className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <Users className="w-4 h-4 text-[#1E40AF]" />
                  <span>Dars beruvchi o'qituvchilar</span>
                  <span className="bg-blue-100 text-[#1E40AF] text-xs font-bold px-2 py-0.5 rounded-full">
                    {getTeachersForSubject(selectedSubject.name).length} nafar
                  </span>
                </h4>
                <p className="text-xs text-gray-500">
                  Ushbu fan bo'yicha maktabda dars beradigan barcha o'qituvchilar
                </p>
              </div>

              {!isAddingTeacher ? (
                <button
                  onClick={() => setIsAddingTeacher(true)}
                  className="flex items-center justify-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-sm transition active:scale-95"
                >
                  <Plus className="w-4 h-4" />
                  <span>+ Ushbu fanga o'qituvchi qo'shish</span>
                </button>
              ) : (
                <button
                  onClick={() => setIsAddingTeacher(false)}
                  className="flex items-center justify-center gap-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs px-3.5 py-2 rounded-xl transition"
                >
                  <X className="w-4 h-4" />
                  <span>Formani yopish</span>
                </button>
              )}
            </div>

            {/* O'QITUVCHI QO'SHISH FORMASI */}
            {isAddingTeacher && (
              <div className="mb-4 p-4 bg-blue-50/70 border border-blue-200 rounded-2xl animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#1E40AF]">
                    <UserPlus className="w-4 h-4" />
                    <span>Yangi {selectedSubject.name} o'qituvchisini kiritish</span>
                  </div>
                  <span className="text-[11px] text-gray-500 font-medium">Fani: {selectedSubject.name}</span>
                </div>

                <form onSubmit={handleAddTeacherToSelectedSubject} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-semibold text-gray-700 block mb-1">
                        O'qituvchi F.I.O:
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="Masalan: Sardor Komilov"
                        value={teacherFullName}
                        onChange={(e) => setTeacherFullName(e.target.value)}
                        className="w-full px-3.5 py-2 bg-white border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-medium"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-gray-700 block mb-1">
                        Telefon Raqami:
                      </label>
                      <input
                        type="text"
                        placeholder="+998 90 123 45 67"
                        value={teacherPhone}
                        onChange={(e) => setTeacherPhone(e.target.value)}
                        className="w-full px-3.5 py-2 bg-white border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-medium"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
                    <div>
                      <label className="text-xs font-semibold text-gray-700 block mb-1">
                        Haftalik Dars Yuklamasi:
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="36"
                        value={teacherWeeklyHours}
                        onChange={(e) => setTeacherWeeklyHours(Number(e.target.value))}
                        className="w-full px-3.5 py-2 bg-white border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setIsAddingTeacher(false)}
                        className="flex-1 py-2 text-xs font-semibold text-gray-600 bg-white border border-gray-300 hover:bg-gray-100 rounded-xl transition"
                      >
                        Bekor qilish
                      </button>
                      <button
                        type="submit"
                        className="flex-1 py-2 text-xs font-bold bg-[#10B981] hover:bg-emerald-600 text-white rounded-xl shadow-sm transition active:scale-95"
                      >
                        Saqlash va Biriktirish
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            )}

            {/* O'qituvchilar Ro'yxati */}
            <div className="overflow-y-auto flex-1 space-y-3 pr-1">
              {getTeachersForSubject(selectedSubject.name).length > 0 ? (
                getTeachersForSubject(selectedSubject.name).map((teacher) => (
                  <div
                    key={teacher.id}
                    className="p-4 bg-gray-50 rounded-xl border border-gray-200/80 hover:border-gray-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-100 text-[#1E40AF] font-black flex items-center justify-center text-sm">
                        {teacher.fullName.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-bold text-gray-900 text-sm">{teacher.fullName}</div>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 mt-0.5">
                          <span className="flex items-center gap-1">
                            <Phone className="w-3 h-3 text-gray-400" />
                            {teacher.phone}
                          </span>
                          <span className="flex items-center gap-1">
                            <Mail className="w-3 h-3 text-gray-400" />
                            {teacher.email}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-4 pt-2 sm:pt-0 border-t sm:border-t-0 border-gray-200">
                      <div className="text-right">
                        <div className="text-xs font-bold text-gray-900">
                          {teacher.weeklyHours} soat/hafta
                        </div>
                        <div className="text-[10px] text-gray-400">
                          kuniga max {teacher.maxDailyHours}s
                        </div>
                      </div>

                      <button
                        onClick={() => {
                          if (confirm(`${teacher.fullName} o'qituvchisini o'chirmoqchimisiz?`)) {
                            deleteTeacher(teacher.id);
                          }
                        }}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                        title="O'chirish"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-10 text-center bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200">
                  <div className="w-12 h-12 rounded-full bg-blue-50 text-[#1E40AF] flex items-center justify-center mx-auto mb-3">
                    <BookOpen className="w-6 h-6" />
                  </div>
                  <h5 className="font-bold text-gray-800 text-sm">
                    {selectedSubject.name} fanidan o'qituvchi kiritilmagan
                  </h5>
                  <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                    Dars jadvalini tuzish uchun ushbu fanga kamida bitta o'qituvchi biriktirilishi kerak.
                  </p>
                  {!isAddingTeacher && (
                    <button
                      onClick={() => setIsAddingTeacher(true)}
                      className="mt-4 inline-flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-semibold text-xs px-4 py-2 rounded-xl transition"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Hozir o'qituvchi qo'shish</span>
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Modal Pastki Qismi */}
            <div className="pt-4 border-t border-gray-100 flex justify-end">
              <button
                onClick={() => {
                  setSelectedSubject(null);
                  setIsAddingTeacher(false);
                }}
                className="px-5 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-xl transition"
              >
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: BUTUNLAY YANGI FAN KIRITISH */}
      {showAddSubjectModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 animate-in fade-in">
            <h3 className="text-lg font-bold text-[#1E40AF] mb-4">Yangi Fan Kiritish</h3>
            <form onSubmit={handleAddSubject} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Fan Nomi:</label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: Geografiya"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Qisqa Kod:</label>
                  <input
                    type="text"
                    required
                    maxLength={5}
                    placeholder="GEO"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none uppercase font-bold"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Rang tanlash:</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={colorHex}
                      onChange={(e) => setColorHex(e.target.value)}
                      className="w-10 h-9 p-0.5 border border-gray-300 rounded-lg cursor-pointer"
                    />
                    <span className="text-xs font-mono font-medium">{colorHex}</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Kerakli Xona Turi:</label>
                <select
                  value={requiredRoom}
                  onChange={(e) => setRequiredRoom(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none bg-white font-medium"
                >
                  <option value="Oddiy xona">Oddiy xona</option>
                  <option value="Laboratoriya">Laboratoriya</option>
                  <option value="Sport zal">Sport zal</option>
                  <option value="Kompyuter xonasi">Kompyuter xonasi</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAddSubjectModal(false)}
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
