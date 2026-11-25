'use client';

import React, { useState, useEffect } from 'react';
import { ShieldCheck, CheckCircle2, School, Building2, Bell, RefreshCw, AlertCircle } from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';
import { schoolApi } from '@/lib/api';

export const SettingsModule: React.FC = () => {
  const { stats } = useSchoolData();

  const [schoolName, setSchoolName] = useState("142-Umumta'lim Maktabi");
  const [subdomain, setSubdomain] = useState("maktab142");
  const [email, setEmail] = useState("admin@maktab142.uz");
  const [phone, setPhone] = useState("+998 71 200 42 42");
  const [address, setAddress] = useState("Toshkent shahri, Yunusobod tumani, 12-mavze");

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // PostgreSQL Neon bazasidan maktab ma'lumotlarini yuklash
  useEffect(() => {
    const fetchSchoolProfile = async () => {
      setIsLoading(true);
      try {
        const data = await schoolApi.getProfile();
        if (data) {
          if (data.name) setSchoolName(data.name);
          if (data.subdomain || data.slug) setSubdomain(data.subdomain || data.slug);
          if (data.email) setEmail(data.email);
          if (data.phone) setPhone(data.phone);
          if (data.address) setAddress(data.address);
        }
      } catch (err) {
        console.warn("Maktab ma'lumotlarini yuklashda xatolik:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSchoolProfile();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(null);
    setErrorMessage(null);

    try {
      await schoolApi.updateProfile({
        name: schoolName,
        email,
        phone,
        address,
      });
      setSaveSuccess("Maktab ma'lumotlari PostgreSQL Neon bazasida muvaffaqiyatli yangilandi!");
    } catch (err: any) {
      setErrorMessage(err.message || "Ma'lumotlarni saqlashda xatolik yuz berdi");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Obuna Karti */}
      <div className="bg-[#FFFFFF] p-6 rounded-2xl border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between pb-5 border-b border-gray-100">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#10B981] bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              Aktiv Obuna
            </span>
            <h3 className="text-xl font-bold text-gray-950 mt-2">Maktab Standart Pro</h3>
            <p className="text-xs text-gray-500">Amal qilish muddati: 2027-yil 1-avgustgacha</p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-black text-[#1E40AF]">Yillik</span>
            <div className="text-xs text-gray-400">Neon Cloud PostgreSQL ulanishi faol</div>
          </div>
        </div>

        {/* Dinamik Limitlar (Neon DB dan real vaqtda) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <div className="text-xs text-gray-500">O'quvchilar sig'imi</div>
            <div className="text-lg font-bold text-gray-900 mt-1">
              {stats.totalStudents} / 1000
            </div>
            <div className="w-full bg-gray-200 h-1.5 rounded-full mt-2">
              <div
                className="bg-[#1E40AF] h-1.5 rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.round((stats.totalStudents / 1000) * 100))}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <div className="text-xs text-gray-500">O'qituvchilar soni</div>
            <div className="text-lg font-bold text-gray-900 mt-1">
              {stats.totalTeachers} / 60
            </div>
            <div className="w-full bg-gray-200 h-1.5 rounded-full mt-2">
              <div
                className="bg-[#10B981] h-1.5 rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.round((stats.totalTeachers / 60) * 100))}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <div className="text-xs text-gray-500">O'quv xonalari</div>
            <div className="text-lg font-bold text-gray-900 mt-1">
              {stats.totalRooms} / Cheksiz
            </div>
            <div className="w-full bg-gray-200 h-1.5 rounded-full mt-2">
              <div className="bg-purple-600 h-1.5 rounded-full" style={{ width: '100%' }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Maktab Profil Sozlamalari (PostgreSQL Neon) */}
      <div className="bg-[#FFFFFF] p-6 rounded-2xl border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <School className="w-5 h-5 text-[#1E40AF]" />
            Maktab Ma'lumotlari (PostgreSQL Neon Baza)
          </h3>
          {isLoading && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Yuklanmoqda...
            </span>
          )}
        </div>

        {saveSuccess && (
          <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-800 p-3.5 rounded-xl text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
            <span>{saveSuccess}</span>
          </div>
        )}

        {errorMessage && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-800 p-3.5 rounded-xl text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-700 block mb-1">Maktab Rasmiy Nomi:</label>
              <input
                type="text"
                required
                value={schoolName}
                onChange={(e) => setSchoolName(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-700 block mb-1">Subdomain (SaaS slug):</label>
              <input
                type="text"
                disabled
                value={`${subdomain}.sms.uz`}
                className="w-full px-3.5 py-2.5 bg-gray-100 border border-gray-300 rounded-xl text-sm text-gray-500 font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-700 block mb-1">Aloqa Emaili (Admin):</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-700 block mb-1">Telefon Raqam:</label>
              <input
                type="text"
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">Manzil:</label>
            <input
              type="text"
              required
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-3.5 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
            />
          </div>

          <div className="pt-3 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold text-sm px-6 py-2.5 rounded-xl shadow-sm transition active:scale-95"
            >
              {isSaving && <RefreshCw className="w-4 h-4 animate-spin" />}
              <span>{isSaving ? "Saqlanmoqda..." : "O'zgarishlarni Saqlash"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};