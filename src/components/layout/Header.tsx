'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Bell,
  Search,
  Calendar,
  Menu,
  GraduationCap,
  Users,
  BookOpen,
  X,
  ExternalLink,
} from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onOpenMobileNav?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle, onOpenMobileNav }) => {
  const router = useRouter();
  const { teachers, classes, subjects } = useSchoolData();
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  // Close search dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const trimmed = searchTerm.trim().toLowerCase();

  const filteredTeachers = trimmed
    ? teachers.filter(
        (t) =>
          t.fullName.toLowerCase().includes(trimmed) ||
          t.subject.toLowerCase().includes(trimmed)
      ).slice(0, 4)
    : [];

  const filteredClasses = trimmed
    ? classes.filter((c) => c.name.toLowerCase().includes(trimmed)).slice(0, 4)
    : [];

  const filteredSubjects = trimmed
    ? subjects.filter((s) => s.name.toLowerCase().includes(trimmed)).slice(0, 4)
    : [];

  const hasResults =
    filteredTeachers.length > 0 ||
    filteredClasses.length > 0 ||
    filteredSubjects.length > 0;

  const handleSelectResult = (url: string) => {
    setIsSearchOpen(false);
    setSearchTerm('');
    router.push(url);
  };

  return (
    <header className="bg-white border-b border-gray-200 px-4 md:px-8 py-3.5 flex items-center justify-between gap-4 sticky top-0 z-30">
      <div className="flex items-center gap-3">
        {onOpenMobileNav && (
          <button
            onClick={onOpenMobileNav}
            className="md:hidden p-2 rounded-xl text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition"
            aria-label="Menyuni ochish"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <div>
          <h2 className="text-lg md:text-xl font-bold text-gray-900 tracking-tight">{title}</h2>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Global Search input */}
        <div className="relative" ref={searchRef}>
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setIsSearchOpen(true);
              }}
              onFocus={() => setIsSearchOpen(true)}
              placeholder="Qidirish (o'qituvchi, sinf, fan)..."
              className="pl-9 pr-8 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:ring-2 focus:ring-[#1E40AF] focus:border-transparent outline-none w-48 sm:w-64 transition"
            />
            {searchTerm && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setIsSearchOpen(false);
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Search Dropdown Results */}
          {isSearchOpen && trimmed && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="p-3 bg-gray-50/70 border-b border-gray-100 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                Qidiruv natijalari: "{searchTerm}"
              </div>

              {!hasResults ? (
                <div className="p-6 text-center text-xs text-gray-400">
                  Mos keladigan ma'lumot topilmadi
                </div>
              ) : (
                <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
                  {/* Teachers */}
                  {filteredTeachers.length > 0 && (
                    <div className="p-2">
                      <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase">
                        O'qituvchilar ({filteredTeachers.length})
                      </div>
                      {filteredTeachers.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => handleSelectResult('/dashboard/teachers')}
                          className="w-full text-left flex items-center justify-between p-2 rounded-xl hover:bg-blue-50/60 transition group text-xs"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-lg bg-blue-100 text-[#1E40AF] flex items-center justify-center font-bold text-[11px]">
                              <Users className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <div className="font-semibold text-gray-800">{t.fullName}</div>
                              <div className="text-[10px] text-gray-400">{t.subject}</div>
                            </div>
                          </div>
                          <ExternalLink className="w-3 h-3 text-gray-300 group-hover:text-blue-600" />
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Classes */}
                  {filteredClasses.length > 0 && (
                    <div className="p-2">
                      <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase">
                        Sinflar ({filteredClasses.length})
                      </div>
                      {filteredClasses.map((c) => (
                        <button
                          key={c.id}
                          onClick={() => handleSelectResult('/dashboard/classes')}
                          className="w-full text-left flex items-center justify-between p-2 rounded-xl hover:bg-emerald-50/60 transition group text-xs"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-[11px]">
                              <GraduationCap className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <div className="font-semibold text-gray-800">{c.name} sinfi</div>
                              <div className="text-[10px] text-gray-400">{c.shift}</div>
                            </div>
                          </div>
                          <ExternalLink className="w-3 h-3 text-gray-300 group-hover:text-emerald-600" />
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Subjects */}
                  {filteredSubjects.length > 0 && (
                    <div className="p-2">
                      <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase">
                        Fanlar ({filteredSubjects.length})
                      </div>
                      {filteredSubjects.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => handleSelectResult('/dashboard/subjects')}
                          className="w-full text-left flex items-center justify-between p-2 rounded-xl hover:bg-indigo-50/60 transition group text-xs"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[11px]">
                              <BookOpen className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <div className="font-semibold text-gray-800">{s.name}</div>
                              <div className="text-[10px] text-gray-400">{s.code}</div>
                            </div>
                          </div>
                          <ExternalLink className="w-3 h-3 text-gray-300 group-hover:text-indigo-600" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Date display */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-600 font-medium">
          <Calendar className="w-3.5 h-3.5 text-[#1E40AF]" />
          <span>Bugun: 11-Noyabr, 2026</span>
        </div>

        {/* Notifications */}
        <button
          className="relative p-2.5 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
          title="Xabarnomalar"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#10B981]"></span>
        </button>
      </div>
    </header>
  );
};
