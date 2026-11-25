'use client';

import React, { useState, useEffect } from 'react';
import {
  School as SchoolIcon,
  Building2,
  Users,
  GraduationCap,
  Plus,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Search,
  Sparkles,
  Phone,
  Mail,
  MapPin,
  Clock,
  Layers,
  ChevronRight
} from 'lucide-react';
import { schoolsApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';

interface SchoolItem {
  id: string;
  name: string;
  slug: string;
  subdomain?: string;
  email: string;
  phone?: string;
  address?: string;
  is_active: boolean;
  total_classes: number;
  total_teachers: number;
  total_students: number;
  subscription?: {
    plan_name: string;
    status: string;
    max_students: number;
    max_teachers: number;
  };
}

const DEFAULT_SCHOOLS: SchoolItem[] = [
  {
    id: '94561d8a-2ca8-4bb2-9b94-e67a53fc472c',
    name: "142-Umumta'lim Maktabi",
    slug: 'maktab142',
    email: 'admin@maktab142.uz',
    phone: '+998 71 200 42 42',
    address: 'Toshkent shahri, Yunusobod tumani',
    is_active: true,
    total_classes: 14,
    total_teachers: 10,
    total_students: 395,
    subscription: {
      plan_name: 'Standard Pro',
      status: 'ACTIVE',
      max_students: 1000,
      max_teachers: 60,
    },
  },
  {
    id: '55555555-5555-5555-5555-555555555555',
    name: "50-Umumta'lim Maktabi",
    slug: 'maktab50',
    email: 'admin@maktab50.uz',
    phone: '+998 71 277 50 50',
    address: 'Toshkent shahri, Chilonzor tumani',
    is_active: true,
    total_classes: 8,
    total_teachers: 7,
    total_students: 240,
    subscription: {
      plan_name: 'Standard Pro',
      status: 'ACTIVE',
      max_students: 800,
      max_teachers: 50,
    },
  },
];

export const SuperAdminSchoolsModule: React.FC = () => {
  const { user } = useAuth();
  const [schools, setSchools] = useState<SchoolItem[]>(DEFAULT_SCHOOLS);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  // Yangi maktab formasi
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [adminName, setAdminName] = useState('Direktor');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchSchools = async () => {
    try {
      setLoading(true);
      const data = await schoolsApi.getAll();
      if (data && data.length > 0) {
        setSchools(data);
      }
    } catch (e) {
      console.warn("Maktablarni serverdan olishda ogohlantirish:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchools();
  }, []);

  const handleCreateSchool = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !slug || !email) return;

    setIsSubmitting(true);
    try {
      await schoolsApi.create({
        name,
        slug,
        email,
        phone,
        address,
        admin_first_name: adminName,
        admin_email: email,
        admin_password: 'Admin123!',
      });
      await fetchSchools();
      setShowAddModal(false);
      setName('');
      setSlug('');
      setEmail('');
      setPhone('');
      setAddress('');
    } catch (err: any) {
      alert(err.message || 'Xatolik yuz berdi');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredSchools = schools.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.address && s.address.toLowerCase().includes(search.toLowerCase())) ||
      s.email.toLowerCase().includes(search.toLowerCase())
  );

  const totalStudents = schools.reduce((sum, s) => sum + (s.total_students || 0), 0);
  const totalTeachers = schools.reduce((sum, s) => sum + (s.total_teachers || 0), 0);
  const totalClasses = schools.reduce((sum, s) => sum + (s.total_classes || 0), 0);

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Super Admin Boshqaruv Markazi Banner */}
      <div className="bg-gradient-to-r from-purple-900 via-indigo-900 to-blue-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-purple-950/20 relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-white/5 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/30 text-purple-200 border border-purple-400/30 text-xs font-bold uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-300" />
              <span>Super Administrator Boshqaruv Markazi</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
              Platformadagi Barcha Maktablar Nazorati
            </h1>
            <p className="text-xs sm:text-sm text-purple-200/90 max-w-2xl leading-relaxed">
              Siz Super Admin rolida tizimdasiz. Siz istalgan maktabning dars jadvali, sinflari va o'qituvchilarini nazorat qilishingiz, yangi maktablarni platformaga ulashingiz mumkin.
            </p>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs sm:text-sm shadow-lg shadow-emerald-900/30 transition active:scale-95 shrink-0 self-start md:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Yangi Maktab Qo'shish</span>
          </button>
        </div>
      </div>

      {/* Global Platforma Statistikasi */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs text-gray-500 font-semibold block">Jami Maktablar</span>
              <span className="text-xl font-black text-gray-900">{schools.length} ta maktab</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-blue-50 text-[#1E40AF] flex items-center justify-center font-bold">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs text-gray-500 font-semibold block">Jami O'quvchilar</span>
              <span className="text-xl font-black text-gray-900">{totalStudents} nafar</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-emerald-50 text-[#10B981] flex items-center justify-center font-bold">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs text-gray-500 font-semibold block">Jami O'qituvchilar</span>
              <span className="text-xl font-black text-gray-900">{totalTeachers} nafar</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs text-gray-500 font-semibold block">Jami Sinflar</span>
              <span className="text-xl font-black text-gray-900">{totalClasses} ta sinf</span>
            </div>
          </div>
        </div>
      </div>

      {/* Maktablar Ro'yxati Header & Search */}
      <div className="bg-white p-5 rounded-2xl border border-gray-200/90 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-purple-700" />
              <span>Platformadagi Maktablar Ro'yxati ({filteredSchools.length})</span>
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Har bir maktabning statistikasi, obunasi va boshqaruv paneliga kirish
            </p>
          </div>

          <div className="relative min-w-[240px]">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Maktab nomi yoki manzili..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-purple-600"
            />
          </div>
        </div>

        {/* Maktablar Kartalari Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
          {filteredSchools.map((school) => (
            <div
              key={school.id}
              className="border border-gray-200 hover:border-purple-300 rounded-2xl p-5 bg-gradient-to-br from-white to-gray-50/40 shadow-xs hover:shadow-md transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-purple-100/70 text-purple-800 font-black text-base flex items-center justify-center border border-purple-200">
                      {school.slug.slice(0, 3).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
                        {school.name}
                        {school.is_active && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Faol
                          </span>
                        )}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-gray-400" />
                          {school.address || "Manzil ko'rsatilmagan"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-gray-100 text-center">
                  <div className="bg-white p-2 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-500 block font-medium">Sinflar</span>
                    <span className="text-sm font-black text-gray-900">{school.total_classes} ta</span>
                  </div>
                  <div className="bg-white p-2 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-500 block font-medium">O'qituvchilar</span>
                    <span className="text-sm font-black text-[#1E40AF]">{school.total_teachers} nafar</span>
                  </div>
                  <div className="bg-white p-2 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-500 block font-medium">O'quvchilar</span>
                    <span className="text-sm font-black text-emerald-700">{school.total_students} nafar</span>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                  <span className="flex items-center gap-1 truncate">
                    <Mail className="w-3 h-3 text-gray-400" />
                    {school.email}
                  </span>
                  <span className="font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md">
                    {school.subscription?.plan_name || 'Standard Pro'}
                  </span>
                </div>
              </div>

              {/* Maktab holati va admini */}
              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
                <span className="text-[11px] text-gray-500 font-medium">
                  Admin: <strong className="text-gray-800">{school.email}</strong>
                </span>

                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-purple-50 text-purple-700 border border-purple-200 text-xs font-bold">
                  <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                  <span>{school.subscription?.status === 'ACTIVE' ? 'Faol Obuna' : 'Faol'}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Yangi Maktab Qo'shish Modali */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl animate-in fade-in space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
                <Plus className="w-4 h-4 text-purple-700" />
                <span>Yangi Maktabni Platformaga Qo'shish</span>
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSchool} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Maktab nomi:</label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: 142-Umumta'lim Maktabi"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    if (!slug) {
                      setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ''));
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-purple-600 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Slug (Identifikator):</label>
                  <input
                    type="text"
                    required
                    placeholder="maktab142"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-purple-600 outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Email (Admin Login):</label>
                  <input
                    type="email"
                    required
                    placeholder="admin@maktab.uz"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-purple-600 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Telefon:</label>
                  <input
                    type="text"
                    placeholder="+998 71 000 00 00"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-purple-600 outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Direktor Ismi:</label>
                  <input
                    type="text"
                    placeholder="Rustam Karimov"
                    value={adminName}
                    onChange={(e) => setAdminName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-purple-600 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Manzil:</label>
                <input
                  type="text"
                  placeholder="Toshkent shahri, Yunusobod tumani"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-purple-600 outline-none"
                />
              </div>

              <div className="bg-purple-50 p-3 rounded-xl border border-purple-100 text-xs text-purple-900">
                ✨ Yangi maktab uchun standart administrator paroli: <strong>Admin123!</strong> etib belgilanadi.
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-xl"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 text-xs font-bold bg-purple-700 hover:bg-purple-800 text-white rounded-xl shadow-xs transition"
                >
                  {isSubmitting ? "Saqlanmoqda..." : "Maktabni Yaratish"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
