'use client';

import React from 'react';
import Link from 'next/link';
import { StatCards } from '@/components/dashboard/StatCards';
import { useSchoolData } from '@/context/SchoolDataContext';
import { useAuth } from '@/context/AuthContext';
import { SuperAdminSchoolsModule } from '@/components/schools/SuperAdminSchoolsModule';
import {
  CalendarDays,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Layers,
  Users,
  GraduationCap,
} from 'lucide-react';

export default function DashboardOverviewPage() {
  const { stats } = useSchoolData();
  const { user } = useAuth();

  // Super Admin kelsa — barcha maktablar boshqaruvi ochiladi
  if (user?.role === 'SUPER_ADMIN') {
    return <SuperAdminSchoolsModule />;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Stat Cards Overview */}
      <StatCards />

      {/* Quick Launch & Generator Banner */}
      <div className="bg-gradient-to-r from-[#1E40AF] to-indigo-800 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-blue-900/10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="max-w-xl space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur text-xs font-semibold text-emerald-300 border border-white/10">
            <Sparkles className="w-3.5 h-3.5 text-emerald-300" />
            <span>CSP Backtracking Generator 2.0</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight">
            Choraklik Dars Jadvalini Avtomatik Yarating
          </h2>
          <p className="text-xs sm:text-sm text-blue-100 leading-relaxed">
            O'qituvchilarning kunlik/haftalik soatlari, sinf smenalari va xonalar
            sig'imini hisobga oluvchi algoritm bilan to'liq ziddiyatsiz jadval shakllantiring.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link
            href="/dashboard/timetable"
            className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-white text-[#1E40AF] font-bold text-xs sm:text-sm shadow-md hover:bg-blue-50 transition"
          >
            <CalendarDays className="w-4 h-4 text-[#1E40AF]" />
            <span>Jadvalni Ko'rish / Yaratish</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/dashboard/curriculum"
            className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-white/15 text-white font-semibold text-xs sm:text-sm hover:bg-white/25 transition border border-white/20"
          >
            <Layers className="w-4 h-4" />
            <span>O'quv Rejasini Sozlash</span>
          </Link>
        </div>
      </div>

      {/* Grid of Sections */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Teachers summary card */}
        <Link
          href="/dashboard/teachers"
          className="bg-white p-6 rounded-2xl border border-gray-200/80 hover:border-blue-300 hover:shadow-md transition group"
        >
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#1E40AF] flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
            <Users className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-gray-900 text-base mb-1">O'qituvchilar Tarkibi</h3>
          <p className="text-xs text-gray-500 mb-4">
            Jami {stats.totalTeachers} nafar o'qituvchi. Haftalik dars soatlari, bo'sh kunlari va cheklovlarini boshqaring.
          </p>
          <span className="text-xs font-bold text-[#1E40AF] inline-flex items-center gap-1 group-hover:gap-2 transition-all">
            Ro'yxatga o'tish <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>

        {/* Classes summary card */}
        <Link
          href="/dashboard/classes"
          className="bg-white p-6 rounded-2xl border border-gray-200/80 hover:border-emerald-300 hover:shadow-md transition group"
        >
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
            <GraduationCap className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-gray-900 text-base mb-1">Sinflar & Smenalar</h3>
          <p className="text-xs text-gray-500 mb-4">
            Jami {stats.totalClasses} ta sinf. 1-smena: {stats.shift1Classes} ta, 2-smena: {stats.shift2Classes} ta. Jami o'quvchilar: {stats.totalStudents}.
          </p>
          <span className="text-xs font-bold text-emerald-700 inline-flex items-center gap-1 group-hover:gap-2 transition-all">
            Sinflarni ko'rish <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>

        {/* System & Neon DB status */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200/80 flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center mb-4">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-gray-900 text-base mb-1">Tizim Xavfsizligi & Baza</h3>
            <div className="space-y-2 mt-3 text-xs text-gray-600">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>PostgreSQL Neon Cloud (Aktiv)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Multi-tenant RLS Izolyatsiya</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>JWT Access & Refresh Tokenlar</span>
              </div>
            </div>
          </div>
          <div className="pt-4 border-t border-gray-100 mt-4 text-[11px] text-gray-400">
            Alembic migratsiyalari sinxronlangan
          </div>
        </div>
      </div>
    </div>
  );
}
