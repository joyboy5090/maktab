import { RoomItem } from '@/components/rooms/RoomsModule';
import { TeacherItem } from '@/components/teachers/TeachersModule';
import { SubjectItem } from '@/components/subjects/SubjectsModule';

/**
 * O'qituvchining mutaxassisligi tanlangan fanga mos kelishini tekshiradi.
 */
export function isTeacherQualifiedForSubject(
  teacherSubject: string | undefined,
  subjectName: string | undefined,
  subjectCode: string = ''
): boolean {
  if (!teacherSubject || !subjectName) return false;

  const t = teacherSubject.toLowerCase().replace(/['`ʻ’]/g, '').trim();
  const s = subjectName.toLowerCase().replace(/['`ʻ’]/g, '').trim();

  // 1. To'g'ridan-to'g'ri aniq moslik
  if (t === s) return true;

  // 2. Bir nechta fan biriktirilgan bo'lsa (vergul bilan yozilgan bo'lsa)
  const list = t.split(/[,/;&]+/).map((x) => x.trim()).filter(Boolean);
  if (list.some((item) => item === s || item.includes(s) || s.includes(item))) return true;

  return false;
}

/**
 * Fanga mos o'qituvchilarni saralash.
 * Faqat shu fanni o'tadigan o'qituvchilar ro'yxatini qaytaradi.
 */
export function filterTeachersForSubject(
  teachers: TeacherItem[],
  subject: SubjectItem | undefined
): TeacherItem[] {
  if (!subject) return [];
  return teachers.filter((t) => isTeacherQualifiedForSubject(t.subject, subject.name, subject.code));
}

/**
 * Sinf uchun ruxsat etilgan xonalar:
 * FAQAT shu sinfning o'z shaxsiy xonasi (masalan: 8-A xona) yoki umumiy laboratoriya/maxsus xonalar (Lab-1, Lab-2, IT-Zal, Sport Zal).
 * Boshqa sinflarning shaxsiy xonalari MUTLAQO kiritilmaydi.
 */
export function getAvailableRoomsForClass(
  className: string,
  allRooms: RoomItem[]
): RoomItem[] {
  const cName = (className || '').toLowerCase().trim();

  // 1. Shu sinfning shaxsiy xonasi
  const personalRooms = cName
    ? allRooms.filter(
        (r) =>
          r.roomType === 'GENERAL' &&
          (r.roomNumber.toLowerCase().includes(cName) ||
            (r.name && r.name.toLowerCase().includes(cName)))
      )
    : [];

  // Agar ro'yxatda hali sinf xonasi bo'lmasa, uning shaxsiy xonasini kafolatlaymiz
  const homeRooms: RoomItem[] =
    personalRooms.length > 0
      ? personalRooms
      : className
      ? [
          {
            id: `home_room_${className}`,
            roomNumber: `${className} xona`,
            name: `${className} sinf xonasi`,
            capacity: 35,
            roomType: 'GENERAL',
          },
        ]
      : [];

  // 2. Faqat laboratoriya va maxsus xonalar (Lab-1, Lab-2, IT-Zal, Sport Zal)
  const specialRooms = allRooms.filter((r) => r.roomType !== 'GENERAL');

  return [...homeRooms, ...specialRooms];
}

/**
 * Tanlangan fan va sinf uchun eng mos xona ID sini aniqlash
 */
export function getRecommendedRoomId(
  subject: SubjectItem | undefined,
  className: string,
  availableRooms: RoomItem[]
): string {
  if (!subject) return '';

  const sName = (subject.name || '').toLowerCase();
  const reqType = (subject.requiredRoom || '').toUpperCase().trim();

  // 1. Kompyuter xonasi (Informatika)
  if (reqType.includes('KOMP') || reqType.includes('IT') || reqType.includes('INF') || sName.includes('informatika')) {
    const itRoom = availableRooms.find((r) => r.roomType === 'COMPUTER_LAB');
    if (itRoom) return itRoom.id;
  }

  // 2. Sport zal (Jismoniy tarbiya)
  if (reqType.includes('SPORT') || reqType.includes('GYM') || sName.includes('jismoniy')) {
    const gymRoom = availableRooms.find((r) => r.roomType === 'GYM');
    if (gymRoom) return gymRoom.id;
  }

  // 3. Laboratoriya xonasi (Kimyo, Fizika, Biologiya)
  if (reqType.includes('LAB') || sName.includes('kimyo') || sName.includes('fizika') || sName.includes('biologiya')) {
    if (sName.includes('kimyo')) {
      const lab2 = availableRooms.find((r) => r.roomType === 'LABORATORY' && (r.roomNumber.includes('2') || r.name.toLowerCase().includes('kimyo')));
      if (lab2) return lab2.id;
    }
    const labRoom = availableRooms.find((r) => r.roomType === 'LABORATORY');
    if (labRoom) return labRoom.id;
  }

  // 4. Boshqa barcha asosiy darslar -> Faqat shu sinfning o'z shaxsiy xonasi
  const cName = (className || '').toLowerCase().trim();
  const personalRoom = availableRooms.find(
    (r) =>
      r.roomType === 'GENERAL' &&
      (r.roomNumber.toLowerCase().includes(cName) ||
        (r.name && r.name.toLowerCase().includes(cName)))
  );
  if (personalRoom) return personalRoom.id;

  // Agar mavjud bo'lsa, mavjud xonalardan birinchisi
  return availableRooms[0]?.id || '';
}
