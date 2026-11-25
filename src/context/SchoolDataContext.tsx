'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { TeacherItem } from '@/components/teachers/TeachersModule';
import { ClassItem } from '@/components/classes/ClassesModule';
import { RoomItem } from '@/components/rooms/RoomsModule';
import { SubjectItem } from '@/components/subjects/SubjectsModule';
import { classesApi, teachersApi, roomsApi, subjectsApi } from '@/lib/api';

// Boshlang'ich fanlar ro'yxati (Alifbo bo'yicha tartiblangan)
const INITIAL_SUBJECTS: SubjectItem[] = [
  { id: 's6', name: 'Biologiya', code: 'BIO', colorHex: '#14B8A6', requiredRoom: 'Laboratoriya' },
  { id: 's3', name: 'Fizika', code: 'FIZ', colorHex: '#8B5CF6', requiredRoom: 'Laboratoriya' },
  { id: 's10', name: 'Geografiya', code: 'GEO', colorHex: '#059669', requiredRoom: 'Oddiy xona' },
  { id: 's7', name: 'Informatika', code: 'INF', colorHex: '#0284C7', requiredRoom: 'Kompyuter xonasi' },
  { id: 's2', name: 'Ingliz tili', code: 'ENG', colorHex: '#10B981', requiredRoom: 'Oddiy xona' },
  { id: 's4', name: 'Jismoniy tarbiya', code: 'SPORT', colorHex: '#F59E0B', requiredRoom: 'Sport zal' },
  { id: 's5', name: 'Kimyo', code: 'KIM', colorHex: '#EC4899', requiredRoom: 'Laboratoriya' },
  { id: 's1', name: 'Matematika', code: 'MAT', colorHex: '#1E40AF', requiredRoom: 'Oddiy xona' },
  { id: 's8', name: 'Ona tili va adabiyot', code: 'ONA', colorHex: '#6366F1', requiredRoom: 'Oddiy xona' },
  { id: 's9', name: 'Tarix', code: 'TAR', colorHex: '#D97706', requiredRoom: 'Oddiy xona' },
];

// Boshlang'ich o'qituvchilar ro'yxati (Fani bo'yicha tartiblangan)
const INITIAL_TEACHERS: TeacherItem[] = [
  {
    id: 't1',
    fullName: 'Alisher Qodirov',
    subject: 'Matematika',
    email: 'a.qodirov@maktab142.uz',
    phone: '+998 90 123 45 67',
    weeklyHours: 44,
    maxDailyHours: 8,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't2',
    fullName: 'Malika Karimova',
    subject: 'Ingliz tili',
    email: 'm.karimova@maktab142.uz',
    phone: '+998 93 234 56 78',
    weeklyHours: 36,
    maxDailyHours: 8,
    availableDays: ['Dushanba', 'Seshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't3',
    fullName: 'Bobur Eshmatov',
    subject: 'Fizika',
    email: 'b.eshmatov@maktab142.uz',
    phone: '+998 94 345 67 89',
    weeklyHours: 16,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba'],
  },
  {
    id: 't4',
    fullName: 'Jasur Rahimov',
    subject: 'Jismoniy tarbiya',
    email: 'j.rahimov@maktab142.uz',
    phone: '+998 97 456 78 90',
    weeklyHours: 22,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba'],
  },
  {
    id: 't5',
    fullName: 'Dilnoza Oripova',
    subject: 'Biologiya',
    email: 'd.oripova@maktab142.uz',
    phone: '+998 91 567 89 01',
    weeklyHours: 18,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't6',
    fullName: 'Otabek Yusupov',
    subject: 'Kimyo',
    email: 'o.yusupov@maktab142.uz',
    phone: '+998 90 987 65 43',
    weeklyHours: 16,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't7',
    fullName: 'Nodira Karimova',
    subject: 'Ona tili va adabiyot',
    email: 'n.karimova@maktab142.uz',
    phone: '+998 90 555 44 33',
    weeklyHours: 32,
    maxDailyHours: 8,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't8',
    fullName: 'Sanjar Bekmirzayev',
    subject: 'Informatika',
    email: 's.bekmirzayev@maktab142.uz',
    phone: '+998 91 333 22 11',
    weeklyHours: 20,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't9',
    fullName: 'Rustam Vohidov',
    subject: 'Tarix',
    email: 'r.vohidov@maktab142.uz',
    phone: '+998 93 444 55 66',
    weeklyHours: 20,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
  },
  {
    id: 't10',
    fullName: 'Gulnora Saidova',
    subject: 'Geografiya',
    email: 'g.saidova@maktab142.uz',
    phone: '+998 94 777 88 99',
    weeklyHours: 20,
    maxDailyHours: 5,
    availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
  },
];

// Boshlang'ich sinflar ro'yxati (Barcha sinflar)
const INITIAL_CLASSES: ClassItem[] = [
  { id: 'c1', name: '5-A', gradeLevel: 5, studentCount: 28, shift: '1-smena', classMaster: 'Alisher Qodirov' },
  { id: 'c2', name: '5-B', gradeLevel: 5, studentCount: 26, shift: '1-smena', classMaster: 'Malika Karimova' },
  { id: 'c3', name: '6-A', gradeLevel: 6, studentCount: 30, shift: '1-smena', classMaster: 'Bobur Eshmatov' },
  { id: 'c4', name: '6-B', gradeLevel: 6, studentCount: 28, shift: '1-smena', classMaster: 'Dilnoza Oripova' },
  { id: 'c5', name: '7-A', gradeLevel: 7, studentCount: 30, shift: '1-smena', classMaster: 'Gulnora Saidova' },
  { id: 'c6', name: '7-B', gradeLevel: 7, studentCount: 25, shift: '2-smena', classMaster: 'Jasur Rahimov' },
  { id: 'c7', name: '8-A', gradeLevel: 8, studentCount: 28, shift: '1-smena', classMaster: 'Nodira Karimova' },
  { id: 'c8', name: '8-B', gradeLevel: 8, studentCount: 28, shift: '1-smena', classMaster: 'Rustam Vohidov' },
  { id: 'c9', name: '9-A', gradeLevel: 9, studentCount: 32, shift: '1-smena', classMaster: 'Sanjar Bekmirzayev' },
  { id: 'c10', name: '9-B', gradeLevel: 9, studentCount: 28, shift: '1-smena', classMaster: 'Otabek Yusupov' },
  { id: 'c11', name: '10-A', gradeLevel: 10, studentCount: 24, shift: '2-smena', classMaster: 'Alisher Qodirov' },
  { id: 'c12', name: '10-B', gradeLevel: 10, studentCount: 26, shift: '1-smena', classMaster: 'Malika Karimova' },
  { id: 'c13', name: '11-A', gradeLevel: 11, studentCount: 25, shift: '1-smena', classMaster: 'Bobur Eshmatov' },
  { id: 'c14', name: '11-B', gradeLevel: 11, studentCount: 25, shift: '1-smena', classMaster: 'Dilnoza Oripova' },
];

// Boshlang'ich xonalar ro'yxati (Har bir sinfning o'z xonasi va maxsus laboratoriyalar)
const INITIAL_ROOMS: RoomItem[] = [
  { id: 'r1', roomNumber: '5-A xona', name: '5-A sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r2', roomNumber: '5-B xona', name: '5-B sinf xonasi', capacity: 30, roomType: 'GENERAL' },
  { id: 'r3', roomNumber: '6-A xona', name: '6-A sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r4', roomNumber: '6-B xona', name: '6-B sinf xonasi', capacity: 30, roomType: 'GENERAL' },
  { id: 'r5', roomNumber: '7-A xona', name: '7-A sinf xonasi', capacity: 30, roomType: 'GENERAL' },
  { id: 'r6', roomNumber: '7-B xona', name: '7-B sinf xonasi', capacity: 30, roomType: 'GENERAL' },
  { id: 'r7', roomNumber: '8-A xona', name: '8-A sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r8', roomNumber: '8-B xona', name: '8-B sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r9', roomNumber: '9-A xona', name: '9-A sinf xonasi', capacity: 35, roomType: 'GENERAL' },
  { id: 'r10', roomNumber: '9-B xona', name: '9-B sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r11', roomNumber: '10-A xona', name: '10-A sinf xonasi', capacity: 30, roomType: 'GENERAL' },
  { id: 'r12', roomNumber: '10-B xona', name: '10-B sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r13', roomNumber: '11-A xona', name: '11-A sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r14', roomNumber: '11-B xona', name: '11-B sinf xonasi', capacity: 32, roomType: 'GENERAL' },
  { id: 'r15', roomNumber: 'Lab-1', name: 'Fizika Laboratoriyasi', capacity: 35, roomType: 'LABORATORY' },
  { id: 'r16', roomNumber: 'Lab-2', name: 'Kimyo Laboratoriyasi', capacity: 35, roomType: 'LABORATORY' },
  { id: 'r17', roomNumber: 'IT-Zal', name: 'Informatika xonasi', capacity: 35, roomType: 'COMPUTER_LAB' },
  { id: 'r18', roomNumber: 'Sport Zal', name: 'Katta sport majmuasi', capacity: 60, roomType: 'GYM' },
];

export interface SchoolStats {
  totalTeachers: number;
  totalClasses: number;
  shift1Classes: number;
  shift2Classes: number;
  totalRooms: number;
  labRooms: number;
  gymRooms: number;
  totalStudents: number;
}

interface SchoolDataContextType {
  teachers: TeacherItem[];
  addTeacher: (teacher: TeacherItem) => void;
  updateTeacher: (id: string, updated: Partial<TeacherItem>) => Promise<void>;
  deleteTeacher: (id: string) => void;

  classes: ClassItem[];
  addClass: (cls: ClassItem) => void;
  updateClass: (id: string, updated: Partial<ClassItem>) => void;
  deleteClass: (id: string) => void;

  rooms: RoomItem[];
  addRoom: (room: RoomItem) => void;
  deleteRoom: (id: string) => void;

  subjects: SubjectItem[];
  addSubject: (subj: SubjectItem) => void;
  deleteSubject: (id: string) => void;

  stats: SchoolStats;
}

const defaultStats: SchoolStats = {
  totalTeachers: INITIAL_TEACHERS.length,
  totalClasses: INITIAL_CLASSES.length,
  shift1Classes: INITIAL_CLASSES.filter((c) => c.shift === '1-smena').length,
  shift2Classes: INITIAL_CLASSES.filter((c) => c.shift === '2-smena').length,
  totalRooms: INITIAL_ROOMS.length,
  labRooms: INITIAL_ROOMS.filter((r) => r.roomType === 'LABORATORY').length,
  gymRooms: INITIAL_ROOMS.filter((r) => r.roomType === 'GYM').length,
  totalStudents: INITIAL_CLASSES.reduce((sum, c) => sum + (c.studentCount || 0), 0),
};

const SchoolDataContext = createContext<SchoolDataContextType | undefined>(undefined);

export const SchoolDataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [teachers, setTeachers] = useState<TeacherItem[]>(INITIAL_TEACHERS);
  const [classes, setClasses] = useState<ClassItem[]>(INITIAL_CLASSES);
  const [rooms, setRooms] = useState<RoomItem[]>(INITIAL_ROOMS);
  const [subjects, setSubjects] = useState<SubjectItem[]>(INITIAL_SUBJECTS);

  // PostgreSQL Neon bazasidan real ma'lumotlarni yuklash
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [clsList, tchList, rmList, sbjList] = await Promise.all([
          classesApi.getAll().catch(() => null),
          teachersApi.getAll().catch(() => null),
          roomsApi.getAll().catch(() => null),
          subjectsApi.getAll().catch(() => null),
        ]);

        if (Array.isArray(clsList)) {
          setClasses(
            clsList.map((c: any) => ({
              id: c.id,
              name: c.name,
              gradeLevel: c.grade_level,
              studentCount: c.student_count,
              shift: c.shift === '2-smena' ? '2-smena' : '1-smena',
              language: c.language || 'UZBEK',
              classMaster: c.class_master || 'Biriktirilmagan',
            }))
          );
        }

        if (Array.isArray(tchList)) {
          setTeachers(
            tchList.map((t: any) => ({
              id: t.id,
              fullName: t.full_name,
              subject: t.primary_subject || 'Umumiy',
              email: t.email || `${t.full_name?.toLowerCase().replace(/\s+/g, '.') || 'oqituvchi'}@maktab142.uz`,
              phone: t.phone || '+998 90 000 00 00',
              weeklyHours: t.max_weekly_hours || 18,
              maxDailyHours: t.max_daily_hours || 4,
              availableDays: ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma'],
            }))
          );
        }

        if (Array.isArray(rmList)) {
          setRooms(
            rmList.map((r: any) => ({
              id: r.id,
              roomNumber: r.room_number,
              name: r.name || r.room_number,
              capacity: r.capacity,
              roomType: r.room_type || 'GENERAL',
            }))
          );
        }

        if (Array.isArray(sbjList)) {
          setSubjects(
            sbjList.map((s: any) => ({
              id: s.id,
              name: s.name,
              code: s.short_code,
              colorHex: s.color_hex || '#1E40AF',
              requiredRoom: s.required_room_type || 'Oddiy xona',
            }))
          );
        }
      } catch (err) {
        console.warn('Neon DB dan yuklashda xatolik:', err);
      }
    };

    fetchData();
  }, []);

  const addTeacher = async (teacher: TeacherItem) => {
    setTeachers((prev) => [teacher, ...prev]);
    try {
      const res = await teachersApi.create({
        full_name: teacher.fullName,
        primary_subject: teacher.subject,
        max_weekly_hours: teacher.weeklyHours,
      });
      if (res?.id) {
        setTeachers((prev) =>
          prev.map((t) => (t.fullName === teacher.fullName ? { ...t, id: res.id } : t))
        );
      }
    } catch (err) {
      console.warn("O'qituvchini bazaga saqlashda xatolik:", err);
    }
  };

  const updateTeacher = async (id: string, updated: Partial<TeacherItem>) => {
    setTeachers((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...updated } : t))
    );
    try {
      await teachersApi.update(id, {
        full_name: updated.fullName,
        primary_subject: updated.subject,
        max_weekly_hours: updated.weeklyHours,
        max_daily_hours: updated.maxDailyHours,
      });
    } catch (err) {
      console.warn("O'qituvchini yangilashda xatolik:", err);
    }
  };

  const deleteTeacher = async (id: string) => {
    setTeachers((prev) => prev.filter((t) => t.id !== id));
    try {
      await teachersApi.delete(id);
    } catch (err) {
      console.warn("O'qituvchini bazadan o'chirishda xatolik:", err);
    }
  };

  const addClass = async (cls: ClassItem) => {
    setClasses((prev) => [...prev, cls]);

    // Har bir yangi sinf qo'shilganda avtomatik uning shaxsiy xonasi yaratiladi
    const cName = cls.name.toLowerCase().trim();
    const hasRoom = rooms.some(
      (r) =>
        r.roomType === 'GENERAL' &&
        (r.roomNumber.toLowerCase().includes(cName) || (r.name && r.name.toLowerCase().includes(cName)))
    );
    if (!hasRoom) {
      const newRoom: RoomItem = {
        id: `r_${Date.now()}`,
        roomNumber: `${cls.name} xona`,
        name: `${cls.name} sinf xonasi`,
        capacity: cls.studentCount || 32,
        roomType: 'GENERAL',
      };
      setRooms((prev) => [...prev, newRoom]);
      roomsApi.create({
        room_number: newRoom.roomNumber,
        name: newRoom.name,
        capacity: newRoom.capacity,
        room_type: 'GENERAL',
      }).catch((e) => console.warn('Xonani saqlashda ogohlantirish:', e));
    }

    try {
      const res = await classesApi.create({
        name: cls.name,
        grade_level: cls.gradeLevel,
        student_count: cls.studentCount,
        shift: cls.shift,
        language: cls.language || 'UZBEK',
      });
      if (res?.id) {
        setClasses((prev) =>
          prev.map((c) => (c.name === cls.name ? { ...c, id: res.id, language: res.language || cls.language || 'UZBEK' } : c))
        );
      }
    } catch (err) {
      console.warn('Sinfni bazaga saqlashda xatolik:', err);
    }
  };

  const updateClass = async (id: string, updated: Partial<ClassItem>) => {
    setClasses((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...updated } : c))
    );
    try {
      await classesApi.update(id, {
        name: updated.name,
        grade_level: updated.gradeLevel,
        student_count: updated.studentCount,
        shift: updated.shift,
        language: updated.language,
      });
    } catch (err) {
      console.warn('Sinfni bazada yangilashda xatolik:', err);
    }
  };

  const deleteClass = async (id: string) => {
    setClasses((prev) => prev.filter((c) => c.id !== id));
    try {
      await classesApi.delete(id);
    } catch (err) {
      console.warn("Sinfni bazadan o'chirishda xatolik:", err);
    }
  };

  const addRoom = async (room: RoomItem) => {
    setRooms((prev) => [...prev, room]);
    try {
      const res = await roomsApi.create({
        room_number: room.roomNumber,
        name: room.name,
        capacity: room.capacity,
        room_type: room.roomType,
      });
      if (res?.id) {
        setRooms((prev) =>
          prev.map((r) => (r.roomNumber === room.roomNumber ? { ...r, id: res.id } : r))
        );
      }
    } catch (err) {
      console.warn('Xonani bazaga saqlashda xatolik:', err);
    }
  };

  const deleteRoom = async (id: string) => {
    setRooms((prev) => prev.filter((r) => r.id !== id));
    try {
      await roomsApi.delete(id);
    } catch (err) {
      console.warn("Xonani bazadan o'chirishda xatolik:", err);
    }
  };

  const addSubject = async (subj: SubjectItem) => {
    setSubjects((prev) => [...prev, subj]);
    try {
      const res = await subjectsApi.create({
        name: subj.name,
        short_code: subj.code,
        required_room_type: subj.requiredRoom,
        color_hex: subj.colorHex,
      });
      if (res?.id) {
        setSubjects((prev) =>
          prev.map((s) => (s.code === subj.code ? { ...s, id: res.id } : s))
        );
      }
    } catch (err) {
      console.warn('Fanni bazaga saqlashda xatolik:', err);
    }
  };

  const deleteSubject = async (id: string) => {
    setSubjects((prev) => prev.filter((s) => s.id !== id));
    try {
      await subjectsApi.delete(id);
    } catch (err) {
      console.warn("Fanni bazadan o'chirishda xatolik:", err);
    }
  };

  const stats: SchoolStats = {
    totalTeachers: teachers.length,
    totalClasses: classes.length,
    shift1Classes: classes.filter((c) => c.shift === '1-smena').length,
    shift2Classes: classes.filter((c) => c.shift === '2-smena').length,
    totalRooms: rooms.length,
    labRooms: rooms.filter((r) => r.roomType === 'LABORATORY').length,
    gymRooms: rooms.filter((r) => r.roomType === 'GYM').length,
    totalStudents: classes.reduce((sum, c) => sum + (c.studentCount || 0), 0),
  };

  return (
    <SchoolDataContext.Provider
      value={{
        teachers,
        addTeacher,
        updateTeacher,
        deleteTeacher,
        classes,
        addClass,
        updateClass,
        deleteClass,
        rooms,
        addRoom,
        deleteRoom,
        subjects,
        addSubject,
        deleteSubject,
        stats,
      }}
    >
      {children}
    </SchoolDataContext.Provider>
  );
};

export const useSchoolData = () => {
  const context = useContext(SchoolDataContext);
  if (!context) {
    return {
      teachers: INITIAL_TEACHERS,
      addTeacher: () => {},
      updateTeacher: async () => {},
      deleteTeacher: () => {},
      classes: INITIAL_CLASSES,
      addClass: () => {},
      updateClass: () => {},
      deleteClass: () => {},
      rooms: INITIAL_ROOMS,
      addRoom: () => {},
      deleteRoom: () => {},
      subjects: INITIAL_SUBJECTS,
      addSubject: () => {},
      deleteSubject: () => {},
      stats: defaultStats,
    };
  }
  return context;
};
