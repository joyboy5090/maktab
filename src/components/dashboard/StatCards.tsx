'use client';

import React from 'react';
import { Users, GraduationCap, DoorOpen, CheckCircle2 } from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';

export const StatCards: React.FC = () => {
  const { stats } = useSchoolData();

  const cards = [
    {
      title: "Jami O'qituvchilar",
      value: `${stats.totalTeachers} nafar`,
      change: "Barcha fanlar bo'yicha",
      icon: Users,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      title: "Mavjud Sinflar",
      value: `${stats.totalClasses} ta sinf`,
      change: `1-smena: ${stats.shift1Classes} | 2-smena: ${stats.shift2Classes}`,
      icon: GraduationCap,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
    },
    {
      title: "O'quv Xonalari",
      value: `${stats.totalRooms} ta xona`,
      change: `${stats.labRooms} Lab, ${stats.gymRooms} Sport zal`,
      icon: DoorOpen,
      color: "text-purple-600",
      bg: "bg-purple-50",
    },
    {
      title: "Dars Jadvali Holati",
      value: "100% Tayyor",
      change: `${stats.totalStudents} nafar o'quvchi qamrovi`,
      icon: CheckCircle2,
      color: "text-emerald-700",
      bg: "bg-emerald-100/60",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      {cards.map((stat, idx) => {
        const Icon = stat.icon;
        return (
          <div
            key={idx}
            className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200/80 shadow-sm hover:shadow-md transition"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {stat.title}
              </span>
              <div className={`p-2.5 rounded-xl ${stat.bg}`}>
                <Icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </div>
            <div className="mt-3">
              <div className="text-2xl font-black text-gray-900">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-1 font-medium">{stat.change}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
