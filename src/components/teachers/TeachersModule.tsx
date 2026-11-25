'use client';

import React, { useState, useMemo, useEffect } from 'react';
import {
  Plus,
  Search,
  Mail,
  Phone,
  BookOpen,
  Trash2,
  ArrowUpDown,
  Users,
  Calculator,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  SlidersHorizontal,
  Layers,
  Clock,
  UserCheck,
  TrendingUp,
  AlertCircle,
  Pencil,
  X
} from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';
import { teachersApi } from '@/lib/api';
import { TeacherWorkloadDemandResponse } from '@/types';

export interface TeacherItem {
  id: string;
  fullName: string;
  subject: string;
  email: string;
  phone: string;
  weeklyHours: number;
  maxDailyHours: number;
  availableDays: string[];
}

interface MultiSubjectSelectorProps {
  selectedSubjects: string[];
  onChange: (subjects: string[]) => void;
  allSubjects: { id: string; name: string; code?: string }[];
}

const MultiSubjectSelector: React.FC<MultiSubjectSelectorProps> = ({
  selectedSubjects,
  onChange,
  allSubjects,
}) => {
  const cleanList = selectedSubjects.filter(Boolean);
  const slotsToRender: string[] = [...cleanList];
  if (cleanList.length < allSubjects.length) {
    slotsToRender.push('');
  }

  const handleSlotChange = (index: number, val: string) => {
    if (!val) {
      if (index === 0) {
        onChange(['']);
      } else {
        const next = cleanList.filter((_, i) => i !== index);
        onChange(next.length > 0 ? next : ['']);
      }
      return;
    }

    const next = [...cleanList];
    if (index < next.length) {
      next[index] = val;
    } else {
      next.push(val);
    }
    onChange(next);
  };

  const handleRemoveSlot = (index: number) => {
    const next = cleanList.filter((_, i) => i !== index);
    onChange(next.length > 0 ? next : ['']);
  };

  return (
    <div className="space-y-2.5 bg-blue-50/50 p-3.5 rounded-2xl border border-blue-100/80">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-[#1E40AF]" />
          <span>Dars beradigan fanlari ({cleanList.length} ta tanlandi)</span>
        </label>
        <span className="text-[10px] text-gray-500 font-medium">
          Bir nechta fan tanlash mumkin
        </span>
      </div>

      <div className="space-y-2">
        {slotsToRender.map((currentVal, index) => {
          const isPrimary = index === 0;
          const available = allSubjects.filter(
            (s) => s.name === currentVal || !cleanList.includes(s.name)
          );

          return (
            <div key={index} className="space-y-1">
              <div className="flex items-center justify-between text-[11px] font-semibold text-gray-600">
                <span>
                  {isPrimary ? "1-Fan (Asosiy fan):" : `${index + 1}-Fan (Qo'shimcha fan):`}
                </span>
                {!isPrimary && currentVal && (
                  <button
                    type="button"
                    onClick={() => handleRemoveSlot(index)}
                    className="inline-flex items-center gap-1 text-[10px] text-rose-500 hover:text-rose-700 hover:bg-rose-50 px-1.5 py-0.5 rounded transition"
                  >
                    <X className="w-3 h-3" />
                    <span>O'chirish</span>
                  </button>
                )}
              </div>
              <select
                value={currentVal}
                onChange={(e) => handleSlotChange(index, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs sm:text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none font-medium bg-white"
              >
                <option value="">
                  {isPrimary
                    ? "-- Asosiy fanni tanlang --"
                    : `-- ${index + 1}-fanni tanlang (ixtiyoriy) --`}
                </option>
                {available.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name} {s.code ? `(${s.code})` : ''}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const TeachersModule: React.FC = () => {
  const { teachers, addTeacher, updateTeacher, deleteTeacher, subjects } = useSchoolData();

  // Tab: 'list' (o'qituvchilar) yoki 'demand' (dars soatlari va ortib qolgan soatlar tahlili)
  const [activeTab, setActiveTab] = useState<'list' | 'demand'>('demand');

  // Qidiruv va modal
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  // Tahrirlash modali
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTeacherId, setEditingTeacherId] = useState<string | null>(null);
  const [editFullName, setEditFullName] = useState('');
  const [editSubjects, setEditSubjects] = useState<string[]>(['']);
  const [editEmail, setEditEmail] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editWeeklyHours, setEditWeeklyHours] = useState(18);
  const [editMaxDailyHours, setEditMaxDailyHours] = useState(4);

  // Ehtiyoj va ortib qolgan soatlar tahlili parametrlari
  const [selectedTerm, setSelectedTerm] = useState<number>(1);
  const [standardRate, setStandardRate] = useState<number>(18); // 1 stavka dars me'yori (18 soat)
  const [demandData, setDemandData] = useState<TeacherWorkloadDemandResponse | null>(null);
  const [isDemandLoading, setIsDemandLoading] = useState(false);

  // Yangi o'qituvchi formasi
  const [newFullName, setNewFullName] = useState('');
  const [newSubjects, setNewSubjects] = useState<string[]>([subjects[0]?.name || 'Matematika']);
  const [newEmail, setNewEmail] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newWeeklyHours, setNewWeeklyHours] = useState(18);
  const [newMaxDailyHours, setNewMaxDailyHours] = useState(4);

  // Dars soatlari va ehtiyojni yuklash
  const fetchDemand = async (term = selectedTerm, rate = standardRate) => {
    setIsDemandLoading(true);
    try {
      const res = await teachersApi.getWorkloadDemand({ term, rate });
      if (res && res.summary) {
        setDemandData(res);
      }
    } catch (err) {
      console.warn("Ortib qolgan soatlarni yuklashda xatolik:", err);
    } finally {
      setIsDemandLoading(false);
    }
  };

  useEffect(() => {
    fetchDemand(selectedTerm, standardRate);
  }, [selectedTerm, standardRate]);

  // O'qituvchilarni fani bo'yicha saralash
  const sortedAndFilteredTeachers = useMemo(() => {
    const filtered = teachers.filter(
      (t) =>
        t.fullName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.subject.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return [...filtered].sort((a, b) => {
      const subComp = a.subject.localeCompare(b.subject, 'uz');
      if (subComp !== 0) return subComp;
      return a.fullName.localeCompare(b.fullName, 'uz');
    });
  }, [teachers, searchTerm]);

  const handleAddTeacher = async (e: React.FormEvent) => {
    e.preventDefault();
    const validSubs = newSubjects.map((s) => s.trim()).filter(Boolean);
    if (!newFullName.trim() || validSubs.length === 0) {
      alert("Iltimos, o'qituvchi F.I.O va kamida bitta dars beradigan fanni tanlang!");
      return;
    }

    const newTeacher: TeacherItem = {
      id: `t_${Date.now()}`,
      fullName: newFullName.trim(),
      subject: validSubs.join(', '),
      email: newEmail.trim() || `${newFullName.trim().toLowerCase().replace(/\s+/g, '.')}@maktab142.uz`,
      phone: newPhone.trim() || '+998 90 000 00 00',
      weeklyHours: Number(newWeeklyHours),
      maxDailyHours: Number(newMaxDailyHours),
      availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
    };

    addTeacher(newTeacher);
    setShowAddModal(false);
    setNewFullName('');
    setNewSubjects([subjects[0]?.name || 'Matematika']);
    setNewEmail('');
    setNewPhone('');
    setNewWeeklyHours(18);
    setNewMaxDailyHours(4);

    setTimeout(() => {
      fetchDemand(selectedTerm, standardRate);
    }, 500);
  };

  const handleOpenEditModal = (teacher: TeacherItem) => {
    setEditingTeacherId(teacher.id);
    setEditFullName(teacher.fullName);
    const parsed = teacher.subject
      ? teacher.subject
          .split(/[,/;&]+/)
          .map((s) => s.trim())
          .filter(Boolean)
      : [];
    setEditSubjects(parsed.length > 0 ? parsed : [subjects[0]?.name || 'Matematika']);
    setEditEmail(teacher.email || '');
    setEditPhone(teacher.phone || '');
    setEditWeeklyHours(teacher.weeklyHours || 18);
    setEditMaxDailyHours(teacher.maxDailyHours || 4);
    setShowEditModal(true);
  };

  const handleSaveEditTeacher = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTeacherId || !editFullName.trim()) return;

    const validSubs = editSubjects.map((s) => s.trim()).filter(Boolean);
    if (validSubs.length === 0) {
      alert("Kamida bitta fan tanlang!");
      return;
    }

    await updateTeacher(editingTeacherId, {
      fullName: editFullName.trim(),
      subject: validSubs.join(', '),
      email: editEmail.trim() || `${editFullName.trim().toLowerCase().replace(/\s+/g, '.')}@maktab142.uz`,
      phone: editPhone.trim() || '+998 90 000 00 00',
      weeklyHours: Number(editWeeklyHours),
      maxDailyHours: Number(editMaxDailyHours),
    });

    setShowEditModal(false);
    setEditingTeacherId(null);

    setTimeout(() => {
      fetchDemand(selectedTerm, standardRate);
    }, 500);
  };

  const handleDelete = (id: string) => {
    if (confirm("Haqiqatdan ham ushbu o'qituvchini o'chirmoqchimisiz?")) {
      deleteTeacher(id);
      setTimeout(() => {
        fetchDemand(selectedTerm, standardRate);
      }, 500);
    }
  };

  const handleQuickAddForSubject = (subjectName: string) => {
    setNewSubjects([subjectName]);
    setShowAddModal(true);
  };

  return (
    <div className="space-y-6">
      {/* 1. Asosiy Tab Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-3 sm:p-4 rounded-2xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-xl w-full sm:w-auto">
          <button
            onClick={() => setActiveTab('demand')}
            className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition ${
              activeTab === 'demand'
                ? 'bg-white text-[#1E40AF] shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Clock className="w-4 h-4 text-[#1E40AF]" />
            <span>Ortib Qolgan Soatlar Tahlili</span>
            {demandData && demandData.summary.total_overload_hours > 0 && (
              <span className="ml-1.5 px-2 py-0.5 rounded-full text-[11px] bg-rose-100 text-rose-700 font-extrabold animate-pulse">
                +{demandData.summary.total_overload_hours} soat ortgan
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('list')}
            className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition ${
              activeTab === 'list'
                ? 'bg-white text-[#1E40AF] shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>O'qituvchilar Ro'yxati</span>
            <span className="ml-1.5 px-2 py-0.5 rounded-full text-[11px] bg-blue-100 text-[#1E40AF]">
              {teachers.length}
            </span>
          </button>
        </div>

        <button
          onClick={() => {
            setNewSubjects([subjects[0]?.name || 'Matematika']);
            setShowAddModal(true);
          }}
          className="w-full sm:w-auto flex items-center justify-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-semibold text-xs sm:text-sm px-5 py-2.5 rounded-xl shadow-sm transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Yangi O'qituvchi Qo'shish</span>
        </button>
      </div>

      {/* 2. TAB: ORTIB QOLGAN SOATLAR TAHLILI */}
      {activeTab === 'demand' && (
        <div className="space-y-6">
          {/* Header Panel */}
          <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="font-extrabold text-gray-900 text-base sm:text-lg flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                Sinflar Dars Yuklamasi & Ortib Qolgan Soatlar
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                Sinflarga o'tilishi kerak bo'lgan darslar hajmi va mavjud o'qituvchilar me'yoridan ortib qolgan soatlarning aniq hisob-kitobi.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              {/* Chorak Tanlash */}
              <div className="flex items-center gap-1 bg-gray-50 border border-gray-200 p-1 rounded-xl text-xs font-semibold">
                <span className="text-gray-400 px-2 text-[11px]">Chorak:</span>
                {[1, 2, 3, 4].map((term) => (
                  <button
                    key={term}
                    onClick={() => setSelectedTerm(term)}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      selectedTerm === term
                        ? 'bg-[#1E40AF] text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {term}-chorak
                  </button>
                ))}
              </div>

              {/* 1 O'qituvchi me'yori (soat/hafta) */}
              <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-xl text-xs">
                <SlidersHorizontal className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-gray-600 font-medium">1 O'qituvchi me'yori:</span>
                <select
                  value={standardRate}
                  onChange={(e) => setStandardRate(Number(e.target.value))}
                  className="bg-transparent font-bold text-gray-900 outline-none cursor-pointer"
                >
                  <option value={16}>16 soat / hafta</option>
                  <option value={18}>18 soat (standart)</option>
                  <option value={20}>20 soat / hafta</option>
                  <option value={24}>24 soat / hafta</option>
                </select>
              </div>
            </div>
          </div>

          {/* KPI Xulosa Kartochkalari: Asosiy e'tibor soatlarga */}
          {demandData && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Jami Dars Soati */}
              <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
                <div className="flex items-center justify-between text-gray-500 text-xs mb-1">
                  <span>Jami Dars Soati</span>
                  <Clock className="w-4 h-4 text-blue-600" />
                </div>
                <div className="text-2xl sm:text-3xl font-black text-gray-900">
                  {demandData.summary.total_weekly_hours} soat
                </div>
                <div className="text-[11px] text-gray-400 mt-1">
                  {demandData.summary.total_classes} ta sinf bo'yicha haftalik hajm
                </div>
              </div>

              {/* Mavjud o'qituvchilar qamrovi */}
              <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
                <div className="flex items-center justify-between text-gray-500 text-xs mb-1">
                  <span>Qoplangan Darslar</span>
                  <UserCheck className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="text-2xl sm:text-3xl font-black text-emerald-700">
                  {demandData.summary.total_covered_hours} soat
                </div>
                <div className="text-[11px] text-gray-400 mt-1">
                  Mavjud {demandData.summary.total_current_teachers} nafar o'qituvchi normasi
                </div>
              </div>

              {/* ASOSIY: Ortib qolgan (ochiq) dars soatlari */}
              <div className={`p-5 rounded-2xl border shadow-md col-span-2 sm:col-span-1 ${
                demandData.summary.total_overload_hours > 0
                  ? 'bg-gradient-to-br from-rose-50 to-red-50 border-rose-300'
                  : 'bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-300'
              }`}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className={`font-black uppercase tracking-wider ${
                    demandData.summary.total_overload_hours > 0 ? 'text-rose-800' : 'text-emerald-800'
                  }`}>
                    Ortib Qolgan Soatlar
                  </span>
                  {demandData.summary.total_overload_hours > 0 ? (
                    <AlertTriangle className="w-5 h-5 text-rose-600 animate-bounce" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  )}
                </div>
                <div className={`text-2xl sm:text-3xl font-black ${
                  demandData.summary.total_overload_hours > 0 ? 'text-rose-700' : 'text-emerald-700'
                }`}>
                  {demandData.summary.total_overload_hours > 0
                    ? `+${demandData.summary.total_overload_hours} soat ortgan`
                    : "0 soat (to'liq qoplangan)"}
                </div>
                <div className="text-[11px] text-rose-800 font-medium mt-1">
                  {demandData.summary.total_overload_hours > 0
                    ? "Ushbu soatlarga yangi o'qituvchilar kerak!"
                    : "Barcha dars soatlariga o'qituvchilar yetarli"}
                </div>
              </div>

              {/* Kerakli qo'shimcha shtat */}
              <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm col-span-2 sm:col-span-1">
                <div className="flex items-center justify-between text-gray-500 text-xs mb-1">
                  <span>Kerakli O'qituvchilar</span>
                  <Users className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="text-2xl sm:text-3xl font-black text-[#1E40AF]">
                  {demandData.summary.total_required_teachers} nafar
                </div>
                <div className="text-[11px] text-gray-400 mt-1">
                  Hozir: {demandData.summary.total_current_teachers} nafar ({demandData.summary.total_deficit > 0 ? `+${demandData.summary.total_deficit} ta yetishmayapti` : 'yetarli'})
                </div>
              </div>
            </div>
          )}

          {/* Fanlar Kesimida Ortib Qolgan Soatlar Jadvali */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h4 className="font-extrabold text-gray-900 text-base">Fanlar Kesimida Ortib Qolgan Dars Soatlari</h4>
                <p className="text-xs text-gray-500">
                  Har bir fanning umumiy dars soati, mavjud o'qituvchilar qamrovi va qancha soat ortib qolgani
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    <th className="py-4 px-6">Fan Nomi</th>
                    <th className="py-4 px-4 text-center">Sinflar</th>
                    <th className="py-4 px-4 text-center">Jami Dars Soati</th>
                    <th className="py-4 px-4 text-center">Mavjud O'qituvchi Qamrovi</th>
                    <th className="py-4 px-6 text-center bg-rose-50/50 text-rose-900">
                      Ortib Qolgan Soat
                    </th>
                    <th className="py-4 px-4 text-center">Kerakli O'qituvchi</th>
                    <th className="py-4 px-6 text-right">Amal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-sm">
                  {demandData?.subjects.map((item) => (
                    <tr
                      key={item.subject_id}
                      className={`hover:bg-gray-50/80 transition ${
                        item.overload_hours > 0 ? 'bg-rose-50/20' : ''
                      }`}
                    >
                      {/* Fan */}
                      <td className="py-4 px-6 font-semibold text-gray-900">
                        <div className="flex items-center gap-2.5">
                          <span
                            className="w-3.5 h-3.5 rounded-full shrink-0"
                            style={{ backgroundColor: item.color_hex }}
                          />
                          <div>
                            <div className="font-bold text-gray-900">{item.subject_name}</div>
                            <div className="text-[11px] text-gray-400 font-normal">Kodi: {item.subject_code}</div>
                          </div>
                        </div>
                      </td>

                      {/* Sinflar */}
                      <td className="py-4 px-4 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-gray-100 text-gray-700">
                          {item.classes_count} ta sinf
                        </span>
                      </td>

                      {/* Jami Dars Soati */}
                      <td className="py-4 px-4 text-center">
                        <span className="text-base font-black text-gray-900">{item.total_weekly_hours}</span>
                        <span className="text-xs text-gray-400 font-normal"> soat</span>
                      </td>

                      {/* Mavjud o'qituvchi qamrovi */}
                      <td className="py-4 px-4 text-center">
                        <div className="text-sm font-bold text-gray-900">
                          {item.teachers_capacity_hours} soat
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {item.current_teachers_count} nafar o'qituvchi
                          {item.current_teachers.length > 0 && (
                            <span className="block text-[10px] text-gray-400">
                              ({item.current_teachers.map(t => t.name).join(', ')})
                            </span>
                          )}
                        </div>
                      </td>

                      {/* ASOSIY: Ortib Qolgan Soatlar */}
                      <td className="py-4 px-6 text-center bg-rose-50/40">
                        {item.overload_hours > 0 ? (
                          <div className="inline-flex flex-col items-center">
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-rose-100 text-rose-800 border border-rose-300 shadow-xs">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                              +{item.overload_hours} soat ortib qolgan
                            </span>
                            <span className="text-[10px] text-rose-600 font-medium mt-0.5">
                              Ochiq qolgan dars soati
                            </span>
                          </div>
                        ) : (
                          <div className="inline-flex flex-col items-center">
                            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              0 soat (to'liq qoplangan)
                            </span>
                            {item.spare_hours > 0 && (
                              <span className="text-[10px] text-emerald-600 mt-0.5">
                                {item.spare_hours} soat zaxira bor
                              </span>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Kerakli o'qituvchi soni */}
                      <td className="py-4 px-4 text-center">
                        <span className="text-sm font-black text-[#1E40AF]">
                          {item.required_teachers} nafar
                        </span>
                        <div className="text-[11px] text-gray-400">
                          ({item.current_teachers_count} nafar mavjud)
                        </div>
                      </td>

                      {/* Qo'shish amali */}
                      <td className="py-4 px-6 text-right">
                        {item.overload_hours > 0 ? (
                          <button
                            onClick={() => handleQuickAddForSubject(item.subject_name)}
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-[#10B981] hover:bg-emerald-600 text-white shadow-sm transition active:scale-95"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            <span>O'qituvchi qo'shish</span>
                          </button>
                        ) : (
                          <button
                            onClick={() => handleQuickAddForSubject(item.subject_name)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold text-gray-500 hover:bg-gray-100 transition"
                          >
                            <Plus className="w-3 h-3" />
                            <span>Qo'shish</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 3. TAB: O'QITUVCHILAR RO'YXATI */}
      {activeTab === 'list' && (
        <div className="space-y-6">
          {/* Yuqori Panel: Qidiruv va Ma'lumot */}
          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="O'qituvchi yoki fan bo'yicha qidirish..."
                className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-[#1E40AF]"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-xl">
                <ArrowUpDown className="w-3.5 h-3.5 text-[#1E40AF]" />
                <span>Fani bo'yicha tartiblangan (<strong className="text-gray-900">{teachers.length} nafar</strong>)</span>
              </div>
            </div>
          </div>

          {/* O'qituvchilar Jadvali */}
          <div className="bg-[#FFFFFF] rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <th className="py-4 px-6">O'qituvchi F.I.O</th>
                    <th className="py-4 px-6">
                      <span className="flex items-center gap-1 text-[#1E40AF]">
                        Asosiy Fani
                        <ArrowUpDown className="w-3 h-3" />
                      </span>
                    </th>
                    <th className="py-4 px-6">Aloqa</th>
                    <th className="py-4 px-6 text-center">Haftalik Yuklama</th>
                    <th className="py-4 px-6">Ishlash Kunlari</th>
                    <th className="py-4 px-6 text-right">Amallar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-sm">
                  {sortedAndFilteredTeachers.map((teacher) => (
                    <tr key={teacher.id} className="hover:bg-gray-50/70 transition">
                      <td className="py-4 px-6 font-semibold text-gray-900 flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-blue-100 text-[#1E40AF] font-bold flex items-center justify-center text-xs">
                          {teacher.fullName.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div>{teacher.fullName}</div>
                          <div className="text-xs text-gray-400 font-normal">ID: {teacher.id}</div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex flex-wrap gap-1.5 max-w-xs">
                          {teacher.subject
                            ? teacher.subject.split(/[,/;&]+/).map((s, idx) => {
                                const cleanSubj = s.trim();
                                if (!cleanSubj) return null;
                                return (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-50 text-[#1E40AF] border border-blue-100 shadow-2xs"
                                  >
                                    <BookOpen className="w-3 h-3 text-[#1E40AF]" />
                                    {cleanSubj}
                                  </span>
                                );
                              })
                            : (
                              <span className="text-xs text-gray-400">Fan biriktirilmagan</span>
                            )}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-xs text-gray-600 space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <Mail className="w-3.5 h-3.5 text-gray-400" />
                          <span>{teacher.email}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Phone className="w-3.5 h-3.5 text-gray-400" />
                          <span>{teacher.phone}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-center">
                        <span className="inline-block bg-emerald-50 text-emerald-700 font-bold px-2.5 py-1 rounded-lg text-xs border border-emerald-100">
                          {teacher.weeklyHours} soat / hafta
                        </span>
                        <div className="text-[11px] text-gray-400 mt-0.5">Kuniga maks {teacher.maxDailyHours} soat</div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {teacher.availableDays.map((d) => (
                            <span key={d} className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-medium">
                              {d.slice(0, 3)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleOpenEditModal(teacher)}
                            className="p-2 text-gray-400 hover:text-[#1E40AF] hover:bg-blue-50 rounded-xl transition"
                            title="Tahrirlash"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(teacher.id)}
                            className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition"
                            title="O'chirish"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Yangi O'qituvchi Qo'shish Modali */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl p-6 sm:p-7 max-w-lg w-full shadow-2xl border border-gray-100 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-gray-900 mb-1 flex items-center gap-2">
              <Users className="w-5 h-5 text-[#1E40AF]" />
              Yangi O'qituvchi Qo'shish
            </h3>
            <p className="text-xs text-gray-500 mb-5">
              O'qituvchi ma'lumotlarini to'ldiring va dars beradigan fanlarini tanlang
            </p>

            <form onSubmit={handleAddTeacher} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">To'liq F.I.O:</label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: Azizbek Karimov"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                />
              </div>

              {/* Ko'p bosqichli kaskadli fan tanlash */}
              <MultiSubjectSelector
                selectedSubjects={newSubjects}
                onChange={setNewSubjects}
                allSubjects={subjects}
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Telefon:</label>
                  <input
                    type="text"
                    placeholder="+998 90 123 45 67"
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Haftalik soat:</label>
                  <input
                    type="number"
                    min="1"
                    value={newWeeklyHours}
                    onChange={(e) => setNewWeeklyHours(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Email (ixtiyoriy):</label>
                  <input
                    type="email"
                    placeholder="a.karimov@maktab142.uz"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Kunlik maks soat:</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={newMaxDailyHours}
                    onChange={(e) => setNewMaxDailyHours(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
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

      {/* O'qituvchini Tahrirlash Modali */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl p-6 sm:p-7 max-w-lg w-full shadow-2xl border border-gray-100 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-gray-900 mb-1 flex items-center gap-2">
              <Pencil className="w-5 h-5 text-[#1E40AF]" />
              O'qituvchi Ma'lumotlarini Tahrirlash
            </h3>
            <p className="text-xs text-gray-500 mb-5">
              O'qituvchi F.I.O, dars beradigan fanlari va yuklama ma'lumotlarini o'zgartiring
            </p>

            <form onSubmit={handleSaveEditTeacher} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">To'liq F.I.O:</label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: Azizbek Karimov"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                />
              </div>

              {/* Ko'p bosqichli kaskadli fan tanlash */}
              <MultiSubjectSelector
                selectedSubjects={editSubjects}
                onChange={setEditSubjects}
                allSubjects={subjects}
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Telefon:</label>
                  <input
                    type="text"
                    placeholder="+998 90 123 45 67"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Haftalik soat:</label>
                  <input
                    type="number"
                    min="1"
                    value={editWeeklyHours}
                    onChange={(e) => setEditWeeklyHours(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Email (ixtiyoriy):</label>
                  <input
                    type="email"
                    placeholder="a.karimov@maktab142.uz"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Kunlik maks soat:</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={editMaxDailyHours}
                    onChange={(e) => setEditMaxDailyHours(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingTeacherId(null);
                  }}
                  className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-[#1E40AF] hover:bg-blue-800 text-white font-medium rounded-xl shadow transition"
                >
                  O'zgarishlarni saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
