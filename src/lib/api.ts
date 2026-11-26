/**
 * API Client for Maktab SMS Frontend
 * Handles HTTP requests, JWT token authorization, automatic token refresh, and typed responses.
 */

import {
  AuthResponse,
  LoginCredentials,
  RefreshTokenResponse,
  Teacher,
  TeacherCreateInput,
  TeacherWorkloadDemandResponse,
  SchoolClass,
  ClassCreateInput,
  Room,
  RoomCreateInput,
  Subject,
  SubjectCreateInput,
  CurriculumAllocation,
  CurriculumAllocationCreateInput,
  TimetableEntry,
  TimetableGenerateRequest,
  TimetableGenerateResponse,
  TimetableJobStatusResponse,
  SchoolProfile,
  PaginatedResponse,
  UserProfile,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Access token faqat xotirada (modul o'zgaruvchisi) saqlanadi; refresh token HttpOnly cookie da
let inMemoryAccessToken: string | null = null;

export const getToken = (): string | null => {
  return inMemoryAccessToken;
};

export const setToken = (token: string): void => {
  inMemoryAccessToken = token;
};

export const removeToken = (): void => {
  inMemoryAccessToken = null;
};

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

async function executeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: "include",
    headers,
  });

  if (res.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (!refreshRes.ok) {
          throw new Error("Sessiya muddati tugadi");
        }

        const refreshData: RefreshTokenResponse = await refreshRes.json();
        setToken(refreshData.access_token);
        isRefreshing = false;
        processQueue(null);

        // Retry current request with new token
        headers["Authorization"] = `Bearer ${refreshData.access_token}`;
        const retryRes = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...options,
          credentials: "include",
          headers,
        });
        if (!retryRes.ok) {
          const errData = await retryRes.json().catch(() => ({}));
          throw new Error(errData?.error?.message || errData.detail || `Server xatosi: ${retryRes.status}`);
        }
        return await retryRes.json();
      } catch (refreshErr) {
        isRefreshing = false;
        processQueue(refreshErr);
        removeToken();
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
        throw refreshErr;
      }
    } else {
      // Wait until refreshing finishes then retry
      return new Promise<T>((resolve, reject) => {
        failedQueue.push({
          resolve: () => {
            executeRequest<T>(endpoint, options).then(resolve).catch(reject);
          },
          reject: (err) => reject(err),
        });
      });
    }
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Noma'lum xatolik" }));
    const msg = errorData?.error?.message || errorData.detail || `Server xatosi: ${res.status}`;
    throw new Error(msg);
  }

  return await res.json();
}

/**
 * Normalizes API response to array if response was wrapped in { data: [...] }
 */
function extractDataArray<T>(response: any): T[] {
  if (Array.isArray(response)) {
    return response;
  }
  if (response && Array.isArray(response.data)) {
    return response.data;
  }
  return [];
}

// 1. AUTH API
export const authApi = {
  login: (credentials: LoginCredentials) =>
    executeRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
  refresh: () =>
    executeRequest<RefreshTokenResponse>("/auth/refresh", {
      method: "POST",
    }),
  logout: () =>
    executeRequest<{ success: boolean; message: string }>("/auth/logout", {
      method: "POST",
    }),
  getMe: () => executeRequest<UserProfile>("/auth/me"),
};

// 2. TEACHERS API
export const teachersApi = {
  getAll: async (params?: { search?: string; subject?: string }): Promise<Teacher[]> => {
    const query = new URLSearchParams();
    query.set("per_page", "100");
    if (params?.search) query.set("search", params.search);
    if (params?.subject) query.set("subject", params.subject);
    const res = await executeRequest<PaginatedResponse<Teacher> | Teacher[]>(`/teachers?${query.toString()}`);
    return extractDataArray<Teacher>(res);
  },
  list: (params?: { page?: number; per_page?: number; search?: string; subject?: string }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.search) query.set("search", params.search);
    if (params?.subject) query.set("subject", params.subject);
    return executeRequest<PaginatedResponse<Teacher>>(`/teachers?${query.toString()}`);
  },
  create: (data: TeacherCreateInput) =>
    executeRequest<Teacher>("/teachers", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<TeacherCreateInput>) =>
    executeRequest<Teacher>(`/teachers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => executeRequest<{ message: string }>(`/teachers/${id}`, { method: "DELETE" }),
  getWorkloadDemand: (params?: { term?: number; rate?: number }) => {
    const query = new URLSearchParams();
    if (params?.term) query.set("term", String(params.term));
    if (params?.rate) query.set("rate", String(params.rate));
    return executeRequest<TeacherWorkloadDemandResponse>(`/teachers/workload-demand?${query.toString()}`);
  },
};

// 3. CLASSES API
export const classesApi = {
  getAll: async (params?: { search?: string; shift?: string; grade?: number }): Promise<SchoolClass[]> => {
    const query = new URLSearchParams();
    query.set("per_page", "100");
    if (params?.search) query.set("search", params.search);
    if (params?.shift) query.set("shift", params.shift);
    if (params?.grade) query.set("grade", String(params.grade));
    const res = await executeRequest<PaginatedResponse<SchoolClass> | SchoolClass[]>(`/classes?${query.toString()}`);
    return extractDataArray<SchoolClass>(res);
  },
  list: (params?: { page?: number; per_page?: number; search?: string; shift?: string; grade?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.search) query.set("search", params.search);
    if (params?.shift) query.set("shift", params.shift);
    if (params?.grade) query.set("grade", String(params.grade));
    return executeRequest<PaginatedResponse<SchoolClass>>(`/classes?${query.toString()}`);
  },
  create: (data: ClassCreateInput) =>
    executeRequest<SchoolClass>("/classes", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<ClassCreateInput>) =>
    executeRequest<SchoolClass>(`/classes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  applyCurriculum: (id: string) =>
    executeRequest<{ success: boolean; message: string }>(`/classes/${id}/apply-curriculum`, { method: "POST" }),
  delete: (id: string) => executeRequest<{ message: string }>(`/classes/${id}`, { method: "DELETE" }),
};

// 4. ROOMS API
export const roomsApi = {
  getAll: async (params?: { search?: string; room_type?: string }): Promise<Room[]> => {
    const query = new URLSearchParams();
    query.set("per_page", "100");
    if (params?.search) query.set("search", params.search);
    if (params?.room_type) query.set("type", params.room_type);
    const res = await executeRequest<PaginatedResponse<Room> | Room[]>(`/rooms?${query.toString()}`);
    return extractDataArray<Room>(res);
  },
  list: (params?: { page?: number; per_page?: number; search?: string; room_type?: string }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.search) query.set("search", params.search);
    if (params?.room_type) query.set("type", params.room_type);
    return executeRequest<PaginatedResponse<Room>>(`/rooms?${query.toString()}`);
  },
  create: (data: RoomCreateInput) =>
    executeRequest<Room>("/rooms", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<RoomCreateInput>) =>
    executeRequest<Room>(`/rooms/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => executeRequest<{ message: string }>(`/rooms/${id}`, { method: "DELETE" }),
};

// 5. SUBJECTS API
export const subjectsApi = {
  getAll: async (params?: { search?: string }): Promise<Subject[]> => {
    const query = new URLSearchParams();
    query.set("per_page", "100");
    if (params?.search) query.set("search", params.search);
    const res = await executeRequest<PaginatedResponse<Subject> | Subject[]>(`/subjects?${query.toString()}`);
    return extractDataArray<Subject>(res);
  },
  list: (params?: { page?: number; per_page?: number; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.search) query.set("search", params.search);
    return executeRequest<PaginatedResponse<Subject>>(`/subjects?${query.toString()}`);
  },
  create: (data: SubjectCreateInput) =>
    executeRequest<Subject>("/subjects", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<SubjectCreateInput>) =>
    executeRequest<Subject>(`/subjects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => executeRequest<{ message: string }>(`/subjects/${id}`, { method: "DELETE" }),
};

// 6. CURRICULUM API
export const curriculumApi = {
  getAll: async (term?: number): Promise<CurriculumAllocation[]> => {
    const query = new URLSearchParams();
    query.set("per_page", "1000");
    if (term) query.set("term", String(term));
    const res = await executeRequest<PaginatedResponse<CurriculumAllocation> | CurriculumAllocation[]>(
      `/curriculum/all?${query.toString()}`
    );
    return extractDataArray<CurriculumAllocation>(res);
  },
  list: (params?: { page?: number; per_page?: number; term?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.term) query.set("term", String(params.term));
    return executeRequest<PaginatedResponse<CurriculumAllocation>>(`/curriculum/all?${query.toString()}`);
  },
  getByClass: (classId: string, term = 1) =>
    executeRequest<CurriculumAllocation[]>(`/curriculum/by-class/${classId}?term=${term}`),
  allocate: (data: CurriculumAllocationCreateInput) =>
    executeRequest<CurriculumAllocation>("/curriculum/allocate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAllocation: (allocationId: string, data: Partial<CurriculumAllocationCreateInput>) =>
    executeRequest<CurriculumAllocation>(`/curriculum/allocate/${allocationId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteAllocation: (allocationId: string) =>
    executeRequest<{ message: string }>(`/curriculum/allocate/${allocationId}`, { method: "DELETE" }),
};

// 7. TIMETABLE API (CSP Generator)
export const timetableApi = {
  generate: (payloadOrTerm: TimetableGenerateRequest | number = 1, slotsPerDay = 6) => {
    const body = typeof payloadOrTerm === 'number'
      ? { term: payloadOrTerm, slots_per_day: slotsPerDay }
      : payloadOrTerm;
    return executeRequest<TimetableGenerateResponse>("/timetable/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  getJob: (jobId: string) =>
    executeRequest<TimetableJobStatusResponse>(`/timetable/jobs/${encodeURIComponent(jobId)}`),
  getMy: async (term = 1): Promise<TimetableEntry[]> => {
    const res = await executeRequest<PaginatedResponse<TimetableEntry> | TimetableEntry[]>(
      `/timetable/my?term=${term}`
    );
    return extractDataArray<TimetableEntry>(res);
  },
  getAll: async (term = 1): Promise<TimetableEntry[]> => {
    const res = await executeRequest<PaginatedResponse<TimetableEntry> | TimetableEntry[]>(
      `/timetable/all?term=${term}&per_page=3000`
    );
    return extractDataArray<TimetableEntry>(res);
  },
  list: (params?: { page?: number; per_page?: number; term?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page || 100));
    if (params?.term) query.set("term", String(params.term || 1));
    return executeRequest<PaginatedResponse<TimetableEntry>>(`/timetable/all?${query.toString()}`);
  },
  getByClass: (classId: string, term = 1) =>
    executeRequest<TimetableEntry[]>(`/timetable/by-class/${classId}?term=${term}`),
  updateEntry: (
    entryId: string,
    data: { day?: string; lesson_order?: number; room_id?: string; is_pinned?: boolean }
  ) =>
    executeRequest<{
      id: string;
      day: string;
      lesson_order: number;
      room_id: string;
      is_pinned: boolean;
    }>(`/timetable/entries/${encodeURIComponent(entryId)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// 8. SCHOOL SETTINGS API
export const schoolApi = {
  getProfile: () => executeRequest<SchoolProfile>("/auth/school"),
  updateProfile: (data: Partial<SchoolProfile>) =>
    executeRequest<SchoolProfile>("/auth/school", { method: "PUT", body: JSON.stringify(data) }),
};

// 9. SUPER ADMIN SCHOOLS API
export const schoolsApi = {
  getAll: () => executeRequest<any[]>("/schools"),
  create: (data: any) =>
    executeRequest<any>("/schools", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: any) =>
    executeRequest<any>(`/schools/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};
