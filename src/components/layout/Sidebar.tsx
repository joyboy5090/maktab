'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  GraduationCap,
  DoorOpen,
  BookOpen,
  Settings,
  Sparkles,
  LogOut,
  Layers,
  X,
  Building2,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onClose }) => {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const currentRole = user?.role || 'SCHOOL_ADMIN';
  const isSuperAdmin = currentRole === 'SUPER_ADMIN';
  const isTeacher = currentRole === 'TEACHER';

  let menuItems = [
    { href: '/dashboard', label: 'Bosh Sahifa', icon: LayoutDashboard },
    { href: '/dashboard/curriculum', label: "O'quv Rejasi", icon: Layers, badge: 'Choraklik' },
    { href: '/dashboard/timetable', label: 'Dars Jadvali', icon: CalendarDays, badge: 'Generator' },
    { href: '/dashboard/teachers', label: "O'qituvchilar", icon: Users },
    { href: '/dashboard/classes', label: 'Sinflar', icon: GraduationCap },
    { href: '/dashboard/rooms', label: 'Xonalar', icon: DoorOpen },
    { href: '/dashboard/subjects', label: 'Fanlar Ro\'yxati', icon: BookOpen },
    { href: '/dashboard/settings', label: 'Sozlamalar & Obuna', icon: Settings },
  ];

  if (isSuperAdmin) {
    // Super Admin faqat butun platformadagi maktablarni va obunalarni boshqaradi
    // Unda bitta maktabning xonalari, o'qituvchilari yoki dars jadvali BO'LMAYDI
    menuItems = [
      { href: '/dashboard', label: 'Barcha Maktablar', icon: Building2, badge: 'Platforma' },
      { href: '/dashboard/settings', label: 'SaaS Obunalar & Tariflar', icon: ShieldCheck },
    ];
  } else if (isTeacher) {
    menuItems = [
      { href: '/dashboard/timetable', label: 'Mening Dars Jadvalim', icon: CalendarDays },
    ];
  }

  const content = (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen flex flex-col justify-between select-none shadow-sm md:shadow-none">
      <div>
        {/* Header / Logo */}
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1E40AF] flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-gray-900 text-base leading-tight">Maktab SMS</h1>
              <p className="text-xs text-gray-500 font-medium">Boshqaruv Tizimi</p>
            </div>
          </Link>
          {onClose && (
            <button
              onClick={onClose}
              className="md:hidden p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Current Tenant / Super Admin Info */}
        <div
          className={`px-4 py-3 mx-3 my-4 rounded-xl border ${
            isSuperAdmin
              ? 'bg-purple-50/80 border-purple-200'
              : 'bg-blue-50/60 border-blue-100'
          }`}
        >
          <div
            className={`text-[10px] font-bold uppercase tracking-wider ${
              isSuperAdmin ? 'text-purple-800' : 'text-blue-800'
            }`}
          >
            {isSuperAdmin ? 'Platforma Nazorati:' : 'Maktab:'}
          </div>
          <div className="text-sm font-bold text-gray-900 truncate mt-0.5">
            {isSuperAdmin ? 'Barcha Maktablar' : (user?.schoolName || "142-Umumta'lim Maktabi")}
          </div>
          <div
            className={`flex items-center gap-1.5 mt-1 text-[11px] font-semibold ${
              isSuperAdmin ? 'text-purple-700' : 'text-[#10B981]'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full inline-block animate-pulse ${
                isSuperAdmin ? 'bg-purple-600' : 'bg-[#10B981]'
              }`}
            ></span>
            {isSuperAdmin ? 'Super Admin Mode' : 'Pro Obuna Aktiv'}
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="px-3 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === '/dashboard'
                ? pathname === '/dashboard'
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#1E40AF] text-white shadow-sm shadow-blue-700/20 font-semibold'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-gray-500'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full flex items-center gap-1 ${
                      isActive
                        ? 'bg-[#10B981] text-white'
                        : 'bg-emerald-50 text-[#10B981] border border-emerald-200'
                    }`}
                  >
                    <Sparkles className="w-2.5 h-2.5" />
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Profile */}
      <div className="p-4 border-t border-gray-100 bg-gray-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 truncate">
            <div
              className={`w-8 h-8 rounded-full font-bold flex items-center justify-center text-xs ${
                isSuperAdmin
                  ? 'bg-purple-100 text-purple-800'
                  : isTeacher
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-blue-100 text-[#1E40AF]'
              }`}
            >
              {isSuperAdmin ? 'SA' : isTeacher ? 'O\'Q' : 'MA'}
            </div>
            <div className="truncate">
              <div className="text-xs font-bold text-gray-800 truncate">
                {isSuperAdmin
                  ? 'Super Administrator'
                  : user?.fullName || (isTeacher ? "O'qituvchi" : "Maktab Ma'muri")}
              </div>
              <div className="text-[10px] text-gray-400 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg transition"
            title="Tizimdan chiqish"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop permanent sidebar */}
      <div className="hidden md:block">{content}</div>

      {/* Mobile drawer backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Mobile drawer container */}
      <div
        className={`fixed inset-y-0 left-0 z-50 transform md:hidden transition-transform duration-300 ease-in-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {content}
      </div>
    </>
  );
};
