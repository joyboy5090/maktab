'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Calendar,
  Download,
  Printer,
  User,
  DoorOpen,
  Clock,
  Users,
  BookOpen,
  FileSpreadsheet,
  Loader2,
} from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';
import { useToast } from '@/context/ToastContext';
import { timetableApi } from '@/lib/api';

export type DayOfWeek = 'Dushanba' | 'Seshanba' | 'Chorshanba' | 'Payshanba' | 'Juma' | 'Shanba';

export interface TimetableCell {
  id: string;
  day: DayOfWeek;
  lessonOrder: number;
  subjectName: string;
  subjectCode: string;
  colorHex: string;
  teacherName: string;
  roomNumber: string;
  roomType: string;
  className: string;
  startTime: string;
  endTime: string;
}

const DAYS: DayOfWeek[] = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba'];

const TIME_SLOTS = [
  { order: 1, start: '08:00', end: '08:45' },
  { order: 2, start: '08:50', end: '09:35' },
  { order: 3, start: '09:40', end: '10:25' },
  { order: 4, start: '10:40', end: '11:25' },
  { order: 5, start: '11:30', end: '12:15' },
  { order: 6, start: '12:20', end: '13:05' },
];

export const TimetableGrid: React.FC<{ refreshKey?: number }> = ({ refreshKey }) => {
  const { classes } = useSchoolData();
  const { toast } = useToast();
  const [selectedClass, setSelectedClass] = useState<string>('5-A');
  const [hoveredCell, setHoveredCell] = useState<TimetableCell | null>(null);
  const [dbEntries, setDbEntries] = useState<TimetableCell[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const gridContainerRef = useRef<HTMLDivElement>(null);

  // PostgreSQL Neon bazasidan dars jadvalini yuklash
  useEffect(() => {
    const fetchTimetable = async () => {
      setIsLoading(true);
      try {
        const data = await timetableApi.getAll(1);
        if (data && Array.isArray(data)) {
          const mapped: TimetableCell[] = data.map((item: any) => {
            const slot = TIME_SLOTS.find((s) => s.order === item.lesson_order) || {
              start: '08:00',
              end: '08:45',
            };
            return {
              id: item.id,
              day: item.day as DayOfWeek,
              lessonOrder: item.lesson_order,
              subjectName: item.subject_name,
              subjectCode: item.subject_code,
              colorHex: item.color_hex || '#1E40AF',
              teacherName: item.teacher_name,
              roomNumber: item.room_number || (item.class_name ? `${item.class_name} xona` : 'Sinf xonasi'),
              roomType: 'Oddiy xona',
              className: item.class_name,
              startTime: slot.start,
              endTime: slot.end,
            };
          });
          setDbEntries(mapped);
        }
      } catch (err: any) {
        console.warn("Dars jadvalini bazadan yuklashda xatolik:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTimetable();
  }, [refreshKey]);

  // Standart birinchi sinfni tanlash
  useEffect(() => {
    if (classes.length > 0 && !classes.some((c) => c.name === selectedClass)) {
      setSelectedClass(classes[0].name);
    }
  }, [classes, selectedClass]);

  // Tanlangan sinf darslari
  const classLessons = useMemo(() => {
    return dbEntries.filter((item) => item.className === selectedClass);
  }, [dbEntries, selectedClass]);

  const getCellForSlot = (day: DayOfWeek, order: number): TimetableCell | undefined => {
    return classLessons.find((item) => item.day === day && item.lessonOrder === order);
  };

  // Real PDF Export using html2canvas & jsPDF
  const handleExportPdf = async () => {
    if (!gridContainerRef.current) return;
    setIsExportingPdf(true);
    try {
      const html2canvas = (await import('html2canvas')).default;
      const { jsPDF } = await import('jspdf');

      const canvas = await html2canvas(gridContainerRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#FFFFFF',
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'pt',
        format: 'a4',
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`${selectedClass}_sinf_dars_jadvali.pdf`);
      toast.success(`${selectedClass} sinf jadvali PDF formatida yuklandi`);
    } catch (err: any) {
      toast.error('PDF eksportida xatolik: ' + (err.message || 'Noma\'lum'));
    } finally {
      setIsExportingPdf(false);
    }
  };

  // Excel / CSV Export
  const handleExportCsv = () => {
    const headers = ['Soat', 'Vaqt', ...DAYS];
    const rows = TIME_SLOTS.map((slot) => {
      const row = [`${slot.order}-soat`, `${slot.start}-${slot.end}`];
      DAYS.forEach((day) => {
        const item = getCellForSlot(day, slot.order);
        row.push(
          item
            ? `"${item.subjectName} (${item.teacherName}, ${item.roomNumber})"`
            : '""'
        );
      });
      return row.join(',');
    });

    const csvContent = '\uFEFF' + [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${selectedClass}_sinf_dars_jadvali.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`${selectedClass} dars jadvali CSV fayli yuklandi`);
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Control Bar */}
      <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gray-50/50">
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">
            Sinfni tanlang:
          </label>
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="bg-white border border-gray-300 text-gray-900 text-sm font-semibold rounded-xl focus:ring-2 focus:ring-[#1E40AF] px-3.5 py-2 outline-none shadow-sm"
          >
            {classes.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name} sinf
              </option>
            ))}
          </select>

          <span className="text-xs text-gray-500 font-medium ml-2">
            Haftalik darslar: <strong className="text-gray-900">{classLessons.length} ta</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 shadow-sm transition"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Chop etish</span>
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 shadow-sm transition"
            title="Excel / CSV formatida eksport"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>Excel (CSV)</span>
          </button>
          <button
            onClick={handleExportPdf}
            disabled={isExportingPdf}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-[#1E40AF] rounded-xl hover:bg-blue-800 shadow-sm transition disabled:opacity-50"
          >
            {isExportingPdf ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Tayyorlanmoqda...</span>
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                <span>Eksport (PDF)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Grid Table for view & PDF capture */}
      <div className="overflow-x-auto" ref={gridContainerRef}>
        <div className="p-4 bg-white border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#1E40AF]"></span>
            <span className="text-sm font-bold text-gray-900">{selectedClass} sinf dars jadvali</span>
          </div>
          <span className="text-xs text-gray-400 font-medium">1-Chorak / 2026-2027 O'quv yili</span>
        </div>

        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100/70 border-b border-gray-200 text-xs font-semibold uppercase tracking-wider text-gray-600">
              <th className="p-4 text-center w-28 border-r border-gray-200">Vaqt / Soat</th>
              {DAYS.map((day) => (
                <th key={day} className="p-4 text-center border-r border-gray-200 last:border-r-0 min-w-[170px]">
                  <span className="text-gray-900 font-bold">{day}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 text-sm">
            {TIME_SLOTS.map((slot) => (
              <tr key={slot.order} className="hover:bg-gray-50/50 transition">
                <td className="p-3 text-center bg-gray-50/80 font-medium text-gray-700 border-r border-gray-200">
                  <div className="text-sm font-bold text-[#1E40AF]">{slot.order}-soat</div>
                  <div className="text-[11px] text-gray-400 mt-0.5 font-medium">
                    {slot.start} - {slot.end}
                  </div>
                </td>

                {DAYS.map((day) => {
                  const item = getCellForSlot(day, slot.order);
                  return (
                    <td
                      key={day}
                      className="p-2 border-r border-gray-200 last:border-r-0 align-top relative"
                    >
                      {item ? (
                        <div
                          onMouseEnter={() => setHoveredCell(item)}
                          onMouseLeave={() => setHoveredCell(null)}
                          style={{ borderLeftColor: item.colorHex }}
                          className="h-24 p-2.5 rounded-xl bg-white border border-gray-200/80 border-l-4 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
                        >
                          <div>
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-gray-900 text-xs truncate max-w-[100px]">
                                {item.subjectName}
                              </span>
                              <span
                                style={{ color: item.colorHex }}
                                className="text-[10px] font-mono font-bold"
                              >
                                {item.subjectCode}
                              </span>
                            </div>

                            <div className="flex items-center gap-1 text-[11px] text-gray-500 mt-1 truncate">
                              <User className="w-3 h-3 text-gray-400 shrink-0" />
                              <span className="truncate">{item.teacherName}</span>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-gray-400 border-t border-gray-100 pt-1 mt-1">
                            <span className="flex items-center gap-1">
                              <DoorOpen className="w-3 h-3" />
                              {item.roomNumber}
                            </span>
                            <span className="text-[10px] font-semibold text-gray-500">
                              {item.className}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="h-24 rounded-xl border border-dashed border-gray-200/80 bg-gray-50/30 flex items-center justify-center text-gray-300 text-xs font-medium">
                          Bo'sh
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {classLessons.length === 0 && !isLoading && (
        <div className="p-8 text-center bg-gray-50/50 border-t border-gray-100">
          <BookOpen className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-gray-700">
            {selectedClass} sinfi uchun hali dars jadvali generatsiya qilinmagan
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            Yuqoridagi <strong>"Jadvalni Generatsiya Qilish"</strong> tugmasini bosib ziddiyatsiz jadval yarating
          </p>
        </div>
      )}
    </div>
  );
};
