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
  Pin,
  PinOff,
} from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';
import { useToast } from '@/context/ToastContext';
import { useAuth } from '@/context/AuthContext';
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
  isPinned?: boolean;
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
  const { user } = useAuth();
  const isTeacher = user?.role === 'TEACHER';
  const [selectedClass, setSelectedClass] = useState<string>('5-A');
  const [hoveredCell, setHoveredCell] = useState<TimetableCell | null>(null);
  const [dbEntries, setDbEntries] = useState<TimetableCell[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [draggedCell, setDraggedCell] = useState<TimetableCell | null>(null);
  const gridContainerRef = useRef<HTMLDivElement>(null);

  // PostgreSQL Neon bazasidan dars jadvalini yuklash
  useEffect(() => {
    const fetchTimetable = async () => {
      setIsLoading(true);
      try {
        const data = isTeacher ? await timetableApi.getMy(1) : await timetableApi.getAll(1);
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
              isPinned: Boolean(item.is_pinned),
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
  }, [refreshKey, isTeacher]);

  // Standart birinchi sinfni tanlash
  useEffect(() => {
    if (!isTeacher && classes.length > 0 && !classes.some((c) => c.name === selectedClass)) {
      setSelectedClass(classes[0].name);
    }
  }, [classes, selectedClass, isTeacher]);

  // Tanlangan sinf yoki o'qituvchining barcha darslari
  const classLessons = useMemo(() => {
    return isTeacher ? dbEntries : dbEntries.filter((item) => item.className === selectedClass);
  }, [dbEntries, selectedClass, isTeacher]);

  const getCellForSlot = (day: DayOfWeek, order: number): TimetableCell | undefined => {
    return classLessons.find((item) => item.day === day && item.lessonOrder === order);
  };

  const detectLocalConflict = (moving: TimetableCell, targetDay: DayOfWeek, targetSlot: number): string | null => {
    const movingClassShift = classes.find((c) => c.name === moving.className)?.shift || '1-smena';
    for (const other of dbEntries) {
      if (other.id === moving.id) continue;
      if (other.day !== targetDay || other.lessonOrder !== targetSlot) continue;
      if (other.className === moving.className) {
        return `${moving.className} sinfi ${targetDay} ${targetSlot}-soatda boshqa darsda band (${other.subjectName}).`;
      }
      const otherShift = classes.find((c) => c.name === other.className)?.shift || '1-smena';
      if (otherShift === movingClassShift) {
        if (moving.teacherName && moving.teacherName !== 'Biriktirilmagan' && other.teacherName === moving.teacherName) {
          return `O'qituvchi (${moving.teacherName}) bu vaqtda ${other.className} sinfida band.`;
        }
        if (moving.roomNumber && other.roomNumber === moving.roomNumber) {
          return `Xona (${moving.roomNumber}) bu vaqtda ${other.className} sinfi uchun band.`;
        }
      }
    }
    return null;
  };

  const handleDropOnSlot = async (targetDay: DayOfWeek, targetSlot: number) => {
    if (!draggedCell) return;
    const moving = draggedCell;
    setDraggedCell(null);

    if (moving.day === targetDay && moving.lessonOrder === targetSlot) return;

    const localConflict = detectLocalConflict(moving, targetDay, targetSlot);
    if (localConflict) {
      const proceed = typeof window !== 'undefined'
        ? window.confirm(`Ogohlantirish: ${localConflict}\nBaribir ko'chirishga urinib ko'rasizmi?`)
        : false;
      if (!proceed) return;
    }

    try {
      await timetableApi.updateEntry(moving.id, {
        day: targetDay,
        lesson_order: targetSlot,
      });
      const slotTime = TIME_SLOTS.find((s) => s.order === targetSlot) || { start: '08:00', end: '08:45' };
      setDbEntries((prev) =>
        prev.map((item) =>
          item.id === moving.id
            ? { ...item, day: targetDay, lessonOrder: targetSlot, startTime: slotTime.start, endTime: slotTime.end }
            : item
        )
      );
      toast.success(`${moving.subjectName} darsi ${targetDay} ${targetSlot}-soatga ko'chirildi`);
    } catch (err: any) {
      toast.error(err.message || "Darsni ko'chirishda to'qnashuv yuz berdi");
    }
  };

  const handleTogglePin = async (item: TimetableCell) => {
    const nextPinned = !item.isPinned;
    try {
      await timetableApi.updateEntry(item.id, { is_pinned: nextPinned });
      setDbEntries((prev) =>
        prev.map((entry) => (entry.id === item.id ? { ...entry, isPinned: nextPinned } : entry))
      );
      toast.success(
        nextPinned
          ? `${item.subjectName} qotirildi (generator qayta ishlaganda o'zgarmaydi)`
          : `${item.subjectName} qotirishdan chiqarildi`
      );
    } catch (err: any) {
      toast.error(err.message || "Qotirish holatini o'zgartirishda xatolik");
    }
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

  // Real Excel (.xlsx) Export with 3 sheets (Sinf, O'qituvchi, Xona)
  const handleExportXlsx = async () => {
    try {
      const ExcelJS = (await import('exceljs')).default;
      const workbook = new ExcelJS.Workbook();

      // 1. Sinf bo'yicha varaq
      const classSheet = workbook.addWorksheet("Sinf bo'yicha");
      classSheet.addRow(['Sinf', 'Kun', 'Soat', 'Vaqt', 'Fan', "O'qituvchi", 'Xona']);
      const sortedByClass = [...dbEntries].sort(
        (a, b) => a.className.localeCompare(b.className) || DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || a.lessonOrder - b.lessonOrder
      );
      sortedByClass.forEach((item) => {
        classSheet.addRow([
          item.className,
          item.day,
          `${item.lessonOrder}-soat`,
          `${item.startTime}-${item.endTime}`,
          item.subjectName,
          item.teacherName,
          item.roomNumber,
        ]);
      });

      // 2. O'qituvchi bo'yicha varaq
      const teacherSheet = workbook.addWorksheet("O'qituvchi bo'yicha");
      teacherSheet.addRow(["O'qituvchi", 'Kun', 'Soat', 'Vaqt', 'Sinf', 'Fan', 'Xona']);
      const sortedByTeacher = [...dbEntries].sort(
        (a, b) => a.teacherName.localeCompare(b.teacherName) || DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || a.lessonOrder - b.lessonOrder
      );
      sortedByTeacher.forEach((item) => {
        teacherSheet.addRow([
          item.teacherName,
          item.day,
          `${item.lessonOrder}-soat`,
          `${item.startTime}-${item.endTime}`,
          item.className,
          item.subjectName,
          item.roomNumber,
        ]);
      });

      // 3. Xona bo'yicha varaq
      const roomSheet = workbook.addWorksheet("Xona bo'yicha");
      roomSheet.addRow(['Xona', 'Kun', 'Soat', 'Vaqt', 'Sinf', 'Fan', "O'qituvchi"]);
      const sortedByRoom = [...dbEntries].sort(
        (a, b) => a.roomNumber.localeCompare(b.roomNumber) || DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || a.lessonOrder - b.lessonOrder
      );
      sortedByRoom.forEach((item) => {
        roomSheet.addRow([
          item.roomNumber,
          item.day,
          `${item.lessonOrder}-soat`,
          `${item.startTime}-${item.endTime}`,
          item.className,
          item.subjectName,
          item.teacherName,
        ]);
      });

      [classSheet, teacherSheet, roomSheet].forEach((sheet) => {
        sheet.getRow(1).font = { bold: true };
        sheet.columns.forEach((col) => {
          col.width = 20;
        });
      });

      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `maktab_dars_jadvali.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success("Dars jadvali Excel (.xlsx) fayli yuklandi");
    } catch (err: any) {
      toast.error("Excel eksportida xatolik: " + (err.message || "Noma'lum"));
    }
  };

  // CSV Export
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
          {!isTeacher ? (
            <>
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
            </>
          ) : (
            <span className="text-sm font-bold text-gray-900">Mening darslarim</span>
          )}

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
            onClick={handleExportXlsx}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 shadow-sm transition"
            title="Haqiqiy Excel (.xlsx) formatida eksport (sinf, o'qituvchi, xona varaqlari)"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>Excel (.xlsx)</span>
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 shadow-sm transition"
            title="CSV formatida eksport"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-gray-500" />
            <span>CSV</span>
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
            <span className="text-sm font-bold text-gray-900">
              {isTeacher ? 'Mening haftalik dars jadvalim' : `${selectedClass} sinf dars jadvali`}
            </span>
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
                      onDragOver={isTeacher ? undefined : (e) => e.preventDefault()}
                      onDrop={isTeacher ? undefined : () => handleDropOnSlot(day, slot.order)}
                      className="p-2 border-r border-gray-200 last:border-r-0 align-top relative"
                    >
                      {item ? (
                        <div
                          draggable={!isTeacher}
                          onDragStart={isTeacher ? undefined : () => setDraggedCell(item)}
                          onDragEnd={isTeacher ? undefined : () => setDraggedCell(null)}
                          onMouseEnter={() => setHoveredCell(item)}
                          onMouseLeave={() => setHoveredCell(null)}
                          style={{ borderLeftColor: item.colorHex }}
                          className={`h-24 p-2.5 rounded-xl bg-white border border-l-4 shadow-sm hover:shadow-md transition-all ${
                            isTeacher ? '' : 'cursor-grab active:cursor-grabbing'
                          } flex flex-col justify-between ${
                            item.isPinned ? 'border-amber-400 ring-1 ring-amber-200' : 'border-gray-200/80'
                          }`}
                        >
                          <div>
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-bold text-gray-900 text-xs truncate max-w-[95px]">
                                {item.subjectName}
                              </span>
                              <div className="flex items-center gap-1 shrink-0">
                                {!isTeacher && (
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleTogglePin(item);
                                    }}
                                    title={item.isPinned ? "Qotirishni yechish" : "Darsni qotirish (Pin)"}
                                    className={`p-0.5 rounded transition ${
                                      item.isPinned
                                        ? 'text-amber-600 bg-amber-50 hover:bg-amber-100'
                                        : 'text-gray-300 hover:text-gray-600'
                                    }`}
                                  >
                                    {item.isPinned ? <Pin className="w-3 h-3" /> : <PinOff className="w-3 h-3" />}
                                  </button>
                                )}
                                <span
                                  style={{ color: item.colorHex }}
                                  className="text-[10px] font-mono font-bold"
                                >
                                  {item.subjectCode}
                                </span>
                              </div>
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
            {isTeacher
              ? "Sizga hozircha dars jadvali biriktirilmagan"
              : `${selectedClass} sinfi uchun hali dars jadvali generatsiya qilinmagan`}
          </p>
          {!isTeacher && (
            <p className="text-xs text-gray-400 mt-0.5">
              Yuqoridagi <strong>"Jadvalni Generatsiya Qilish"</strong> tugmasini bosib ziddiyatsiz jadval yarating
            </p>
          )}
        </div>
      )}
    </div>
  );
};
