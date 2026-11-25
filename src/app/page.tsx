'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { GraduationCap, Loader2 } from 'lucide-react';

export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.replace('/dashboard');
      } else {
        router.replace('/login');
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#F3F4F6]">
      <div className="w-14 h-14 rounded-2xl bg-[#1E40AF] flex items-center justify-center text-white shadow-lg shadow-blue-500/20 mb-4 animate-pulse">
        <GraduationCap className="w-8 h-8" />
      </div>
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <Loader2 className="w-4 h-4 animate-spin text-[#1E40AF]" />
        <span>Maktab SMS yuklanmoqda...</span>
      </div>
    </div>
  );
}
