'use client';

import React, { useState } from 'react';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useSchoolData } from '@/context/SchoolDataContext';
import { useAuth } from '@/context/AuthContext';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { stats } = useSchoolData();
  const { user } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const getPageMeta = () => {
    if (pathname === '/dashboard' && user?.role === 'SUPER_ADMIN') {
      return {
        title: "Super Admin Platformasi — Barcha Maktablar",
        subtitle: "Tizimdagi barcha umumta'lim maktablarini markazlashgan holda boshqarish",
      };
    }
    if (pathname.includes('/dashboard/curriculum')) {
      return {
        title: "Sinflar O'quv Rejasi (Choraklik Taqsimot)",
        subtitle: "Sinflarga fanlar, o'qituvchilar va choraklik umumiy dars soatlarini biriktirish",
      };
    }
    if (pathname.includes('/dashboard/timetable')) {
      return {
        title: "Avtomatlashtirilgan Dars Jadvali",
        subtitle: "CSP Backtracking algoritmi asosida tuzilgan ziddiyatsiz jadval",
      };
    }
    if (pathname.includes('/dashboard/teachers')) {
      return {
        title: "O'qituvchilar Ro'yxati",
        subtitle: `Jami ${stats.totalTeachers} nafar o'qituvchi va ularning fanlari`,
      };
    }
    if (pathname.includes('/dashboard/classes')) {
      return {
        title: "Maktab Sinflari",
        subtitle: `Jami ${stats.totalClasses} ta sinf tarkibi, smenalari va o'quvchilar soni`,
      };
    }
    if (pathname.includes('/dashboard/rooms')) {
      return {
        title: "O'quv Xonalari",
        subtitle: `Jami ${stats.totalRooms} ta o'quv xonasi, laboratoriya va sport zallar`,
      };
    }
    if (pathname.includes('/dashboard/subjects')) {
      return {
        title: "Fanlar & Rang Kodlari",
        subtitle: "Maktab o'quv dasturi fanlar katalogi",
      };
    }
    if (pathname.includes('/dashboard/settings')) {
      return {
        title: "Sozlamalar & SaaS Obunasi",
        subtitle: "Maktab profili va obuna limitlarini nazorat qilish",
      };
    }
    return {
      title: "Maktab Boshqaruv Markazi (Dashboard)",
      subtitle: "Xush kelibsiz! Maktab ma'lumotlari va dars jadvali holati",
    };
  };

  const meta = getPageMeta();

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen bg-[#F3F4F6]">
        {/* Responsive Sidebar */}
        <Sidebar
          mobileOpen={mobileNavOpen}
          onClose={() => setMobileNavOpen(false)}
        />

        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {/* Header */}
          <Header
            title={meta.title}
            subtitle={meta.subtitle}
            onOpenMobileNav={() => setMobileNavOpen(true)}
          />

          {/* Main content wrapped in ErrorBoundary */}
          <main className="p-4 md:p-8 flex-1">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
