'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, RefreshCw, AlertCircle, CheckCircle, Lock } from 'lucide-react';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import { timetableApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { UnplacedLessonItem } from '@/types';

export const TimetableModule: React.FC = () => {
  const { user } = useAuth();
  const isTeacher = user?.role === 'TEACHER';

  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const [generationStatus, setGenerationStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [unplacedLessons, setUnplacedLessons] = useState<UnplacedLessonItem[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, []);

  const pollJobStatus = async (jobId: string) => {
    try {
      const job = await timetableApi.getJob(jobId);
      setProgress(job.progress ?? 0);

      if (job.status === 'done') {
        setIsGenerating(false);
        setGenerationStatus(
          job.result?.message || "Dars jadvali muvaffaqiyatli generatsiya qilindi!"
        );
        setUnplacedLessons(job.result?.unplaced || []);
        setRefreshKey((prev) => prev + 1);
        return;
      }

      if (job.status === 'failed') {
        setIsGenerating(false);
        setErrorMessage(
          job.result?.message || "Dars jadvalini to'liq generatsiya qilib bo'lmadi"
        );
        setUnplacedLessons(job.result?.unplaced || []);
        if (job.result?.status === 'partial') {
          setRefreshKey((prev) => prev + 1);
        }
        return;
      }

      // pending / running: 2 soniyada bir so'rab turish
      pollTimerRef.current = setTimeout(() => pollJobStatus(jobId), 2000);
    } catch (err: any) {
      setIsGenerating(false);
      setErrorMessage(err.message || "Vazifa holatini tekshirishda xatolik yuz berdi");
    }
  };

  const handleGenerate = async () => {
    if (isTeacher || isGenerating) return;

    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
    }
    setIsGenerating(true);
    setProgress(5);
    setGenerationStatus(null);
    setErrorMessage(null);
    setUnplacedLessons([]);

    try {
      const res = await timetableApi.generate(1, 6);
      if (res.job_id) {
        pollTimerRef.current = setTimeout(() => pollJobStatus(res.job_id!), 2000);
      } else {
        setIsGenerating(false);
        setGenerationStatus(res.message || "Dars jadvali muvaffaqiyatli generatsiya qilindi!");
        setUnplacedLessons(res.unplaced || []);
        setRefreshKey((prev) => prev + 1);
      }
    } catch (err: any) {
      setIsGenerating(false);
      setErrorMessage(err.message || "Dars jadvalini generatsiya qilishda xatolik yuz berdi");
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
              <span>{isGenerating ? `Tuzilmoqda (${progress}%)...` : 'Jadvalni Generatsiya Qilish'}</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 bg-white/10 px-4 py-2 rounded-xl text-xs font-medium text-emerald-300">
            <Lock className="w-4 h-4" />
            <span>Faqat ko'rish huquqi</span>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {isGenerating && (
        <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-blue-900">
            <span>Dars jadvali fon rejimida tuzilmoqda...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full h-2.5 bg-blue-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#1E40AF] transition-all duration-500 rounded-full"
              style={{ width: `${Math.min(100, Math.max(5, progress))}%` }}
            />
          </div>
        </div>
      )}

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

      {/* Joylashmagan darslar ro'yxati */}
      {unplacedLessons.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
          <div className="text-sm font-bold text-amber-900">
            Joylashmagan darslar ({unplacedLessons.length} ta):
          </div>
          <ul className="space-y-1.5 text-xs text-amber-800 max-h-56 overflow-y-auto">
            {unplacedLessons.map((u, idx) => (
              <li key={`${u.lesson_id}-${idx}`} className="bg-white/70 border border-amber-200/80 rounded-lg px-3 py-2 flex flex-wrap items-center justify-between gap-2">
                <span>
                  <strong>{u.class_name}</strong> — {u.subject_name} ({u.teacher_name || "O'qituvchisiz"})
                </span>
                <span className="text-amber-700 font-medium">{u.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Grid Komponenti */}
      <TimetableGrid refreshKey={refreshKey} />
    </div>
  );
};
