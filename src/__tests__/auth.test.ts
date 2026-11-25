import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { z } from 'zod';
import { authApi, setToken, getToken, removeToken } from '@/lib/api';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const loginSchema = z.object({
  email: z.string().email("Noto'g'ri email formati kiritildi"),
  password: z
    .string()
    .min(8, "Parol kamida 8 ta belgidan iborat bo'lishi kerak")
    .regex(/[A-Z]/, "Parolda kamida 1 ta katta harf bo'lishi kerak")
    .regex(/[0-9]/, "Parolda kamida 1 ta raqam bo'lishi kerak"),
});

const mockReplace = vi.fn();
const mockUseAuth = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
  }),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('Auth Zod Schema', () => {
  it('accepts valid email and strong password', () => {
    const valid = loginSchema.safeParse({
      email: 'admin@maktab142.uz',
      password: 'AdminPassword123!',
    });
    expect(valid.success).toBe(true);
  });

  it('rejects short, missing-digit, or missing-uppercase passwords', () => {
    expect(loginSchema.safeParse({ email: 'admin@maktab142.uz', password: 'Pass1' }).success).toBe(false);
    expect(loginSchema.safeParse({ email: 'admin@maktab142.uz', password: 'PasswordOnly' }).success).toBe(false);
    expect(loginSchema.safeParse({ email: 'admin@maktab142.uz', password: 'password123' }).success).toBe(false);
  });
});

describe('API Client automatic refresh interceptor', () => {
  beforeEach(() => {
    removeToken();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    removeToken();
  });

  it('refreshes access token via HttpOnly cookie on 401 and retries request', async () => {
    setToken('expired-token');

    const fetchMock = vi
      .fn()
      // 1. Original /auth/me returns 401
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Expired' }), { status: 401 }))
      // 2. /auth/refresh returns new access_token
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'fresh-access-token', role: 'SCHOOL_ADMIN', email: 'a@b.uz' }), {
          status: 200,
        })
      )
      // 3. Retry /auth/me with fresh token succeeds
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 'u1', email: 'a@b.uz', role: 'SCHOOL_ADMIN' }), { status: 200 })
      );

    vi.stubGlobal('fetch', fetchMock);

    const profile = await authApi.getMe();
    expect(profile.email).toBe('a@b.uz');
    expect(getToken()).toBe('fresh-access-token');
    expect(fetchMock).toHaveBeenCalledTimes(3);

    // Verify credentials: 'include' is passed
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh');
    expect(fetchMock.mock.calls[1][1].credentials).toBe('include');
  });
});

describe('ProtectedRoute', () => {
  beforeEach(() => {
    mockReplace.mockReset();
    mockUseAuth.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('shows loading state while auth is initializing', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true });
    render(React.createElement(ProtectedRoute, null, React.createElement('div', null, 'Secret')));
    expect(screen.getByText('Tizim yuklanmoqda...')).toBeTruthy();
    expect(screen.queryByText('Secret')).toBeNull();
  });

  it('redirects to /login when unauthenticated', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    render(React.createElement(ProtectedRoute, null, React.createElement('div', null, 'Secret')));
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login');
    });
    expect(screen.queryByText('Secret')).toBeNull();
  });

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    render(React.createElement(ProtectedRoute, null, React.createElement('div', null, 'Secret')));
    expect(screen.getByText('Secret')).toBeTruthy();
  });
});
