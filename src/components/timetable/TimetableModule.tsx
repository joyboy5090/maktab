'use client';

import React, { useState } from 'react';
import { Sparkles, Printer, Download, Filter, RefreshCw, AlertCircle, CheckCircle, Lock } from 'lucide-react';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import { timetableApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

export const TimetableModule: React.FC = () => {
  const { user } = useAuth();
  const isTeacher = user?.role === 'TEACHER';

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleGenerate = async () => {
    if (isTeacher) return;

    setIsGenerating(true);
    setGenerationStatus(null);
    setErrorMessage(null);

    try {
      // 1. Backend API orqali generatsiya qilish (1-chorak, har kunga 6 soat)
      const res = await timetableApi.generate(1, 6);
      setGenerationStatus(res.message || "Dars jadvali muvaffaqiyatli generatsiya qilindi!");
      setRefreshKey((prev) => prev + 1);
    } catch (err: any) {
      // 2. Agar backend server offline bo'lsa, xatolikni ko'rsatish
      setErrorMessage(err.message || "Dars jadvalini generatsiya qilishda xatolik yuz berdi");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Banner */}
      <div className="bg-gradient-to-r from-[#1E40AF] to-blue-900 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 bg-blue-500/30 px-3 py-1 rounded-full text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5 text-yellow-300" />
            AI & CSP Backtracking Algoritmi
          </div>
          <h3 className="text-xl font-bold">
            {isTeacher ? "Sizning Haftalik Dars Jadvalingiz" : "Avtomatlashtirilgan Dars Jadvali Markazi"}
          </h3>
          <p className="text-blue-100 text-xs mt-1 max-w-xl">
            {isTeacher
              ? "Tizimda siz biriktirilgan darslar, xonalar va vaqtlar quyidagi interaktiv jadvalda aks etgan (Read-only rejim)."
              : "Barcha o'qituvchilar, xonalar sig'imi va sinflar cheklovlarini hisobga olgan holda ziddiyatsiz dars jadvalini yarating."}
          </p>
        </div>

        {!isTeacher ? (
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold text-sm px-6 py-3 rounded-xl shadow-md transition active:scale-95"
            >
              <RefreshCw className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
              <span>{isGenerating ? 'Tuzilmoqda...' : 'Jadvalni Generatsiya Qilish'}</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 bg-white/10 px-4 py-2 rounded-xl text-xs font-medium text-emerald-300">
            <Lock className="w-4 h-4" />
            <span>Faqat ko'rish huquqi</span>
          </div>
        )}
      </div>

      {/* Xabarnomalar */}
      {generationStatus && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-xl flex items-center justify-between text-sm animate-in fade-in">
          <div className="flex items-center gap-2 font-medium">
            <CheckCircle className="w-5 h-5 text-[#10B981]" />
            <span>{generationStatus}</span>
          </div>
          <button
            onClick={() => setGenerationStatus(null)}
            className="text-xs text-emerald-600 hover:underline font-semibold"
          >
            Yopish
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-medium">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs text-red-600 hover:underline font-semibold"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Grid Komponenti */}
      <TimetableGrid refreshKey={refreshKey} />
    </div>
  );
};
