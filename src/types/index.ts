/**
 * Types definition for Maktab SMS Frontend
 * Standartlashtirilgan TypeScript tiplari
 */

export type UserRole = 'SUPER_ADMIN' | 'SCHOOL_ADMIN' | 'TEACHER';

export interface UserProfile {
  id: string;
  email: string;
  role: UserRole;
  school_id?: string;
  schoolName?: string;
  fullName?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  role: UserRole;
  school_id?: string;
  email: string;
  user_id?: string;
}

export type AuthResponse = AuthTokens;

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  role?: UserRole;
  school_id?: string;
  email?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiSuccessResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ApiErrorResponse {
  success: boolean;
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface Teacher {
  id: string;
  school_id?: string;
  fullName: string;
  subject: string;
  email?: string;
  phone?: string;
  weeklyHours: number;
  maxDailyHours: number;
  availableDays?: string[];
}

export interface TeacherCreateInput {
  full_name: string;
  primary_subject?: string;
  max_weekly_hours?: number;
  max_daily_hours?: number;
  email?: string;
  phone?: string;
}

export interface ClassItem {
  id: string;
  school_id?: string;
  name: string;
  gradeLevel: number;
  studentCount: number;
  shift: '1-smena' | '2-smena';
  language?: 'UZBEK' | 'RUSSIAN' | 'QARDOSH';
  classMaster?: string;
}

export type SchoolClass = ClassItem;

export interface ClassCreateInput {
  name: string;
  grade_level: number;
  student_count?: number;
  shift?: string;
  language?: string;
}

export type RoomType = 'GENERAL' | 'LABORATORY' | 'GYM' | 'COMPUTER_LAB';

export interface RoomItem {
  id: string;
  school_id?: string;
  roomNumber: string;
  name: string;
  capacity: number;
  roomType: RoomType;
}

export type Room = RoomItem;

export interface RoomCreateInput {
  room_number: string;
  name?: string;
  capacity?: number;
  room_type?: string;
}

export interface SubjectItem {
  id: string;
  school_id?: string;
  name: string;
  code: string;
  colorHex: string;
  requiredRoom: string;
}

export type Subject = SubjectItem;

export interface SubjectCreateInput {
  name: string;
  short_code: string;
  required_room_type?: string;
  color_hex?: string;
}

export interface AllocationItem {
  id: string;
  className: string;
  classId: string;
  subjectName: string;
  subjectCode: string;
  colorHex: string;
  teacherName: string;
  teacherId: string;
  roomNumber?: string;
  term: number;
  quarterTotalHours: number;
  weeksInQuarter: number;
  weeklyHours: number;
  maxPerDay: number;
}

export type CurriculumAllocation = AllocationItem;

export interface CurriculumAllocationCreateInput {
  class_id: string;
  subject_id: string;
  teacher_id: string;
  preferred_room_id?: string;
  term: number;
  quarter_total_hours: number;
  weeks_in_quarter: number;
  weekly_hours: number;
  max_hours_per_day?: number;
}

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
  roomType?: string;
  className: string;
  startTime: string;
  endTime: string;
  isPinned?: boolean;
}

export type TimetableEntry = TimetableCell;

export interface TimetableGenerateRequest {
  term?: number;
  slots_per_day?: number;
  save_partial?: boolean;
}

export interface UnplacedLessonItem {
  lesson_id: string;
  class_id: string;
  class_name: string;
  subject_id: string;
  subject_name: string;
  teacher_id?: string | null;
  teacher_name?: string | null;
  reason: string;
}

export interface TimetableGenerateResponse {
  job_id?: string;
  status?: string;
  progress?: number;
  success?: boolean;
  message: string;
  total_lessons_scheduled?: number;
  total_required?: number;
  unplaced?: UnplacedLessonItem[];
  term: number;
}

export interface TimetableJobStatusResponse {
  id: string;
  school_id: string;
  term: number;
  status: 'pending' | 'running' | 'done' | 'failed';
  progress: number;
  result?: {
    success: boolean;
    status: string;
    message: string;
    total_lessons_scheduled: number;
    total_required: number;
    unplaced: UnplacedLessonItem[];
    term: number;
  } | null;
  created_at: string;
  finished_at?: string | null;
}

export interface SchoolProfile {
  id: string;
  name: string;
  slug: string;
  subdomain?: string;
  email?: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
}

export interface TeacherWorkloadDemandItem {
  subject_id: string;
  subject_name: string;
  subject_code: string;
  color_hex: string;
  total_weekly_hours: number;
  classes_count: number;
  class_names: string[];
  stavka_units: number;
  teachers_capacity_hours: number;
  overload_hours: number;
  spare_hours: number;
  required_teachers: number;
  current_teachers_count: number;
  current_teachers: Array<{
    id: string;
    name: string;
    primary_subject?: string;
    max_weekly_hours: number;
    assigned_hours: number;
  }>;
  deficit: number;
  status: 'OVERLOAD' | 'DEFICIT' | 'BALANCED' | 'SURPLUS';
  status_label: string;
}

export interface TeacherWorkloadDemandResponse {
  term: number;
  standard_rate_hours: number;
  summary: {
    total_classes: number;
    total_weekly_hours: number;
    total_covered_hours: number;
    total_overload_hours: number;
    total_spare_hours: number;
    total_stavka: number;
    total_required_teachers: number;
    total_current_teachers: number;
    total_deficit: number;
  };
  subjects: TeacherWorkloadDemandItem[];
}
