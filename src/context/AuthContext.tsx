'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getToken,
  setToken,
  removeToken,
  authApi,
} from '@/lib/api';
import { UserProfile, UserRole } from '@/types';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  switchRoleDemo?: (role: UserRole) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = useCallback(async (): Promise<boolean> => {
    try {
      const profile = await authApi.getMe();
      setUser({
        id: profile.id,
        email: profile.email,
        role: profile.role,
        school_id: profile.school_id,
        schoolName: profile.schoolName || "142-Umumta'lim Maktabi",
        fullName: profile.fullName || (profile.role === 'TEACHER' ? "O'qituvchi" : 'Maktab Ma\'muri'),
      });
      return true;
    } catch {
      removeToken();
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        let token = getToken();
        if (!token) {
          // Sahifa yangilanganda HttpOnly cookie orqali access tokenni tiklaymiz
          const refreshRes = await authApi.refresh();
          token = refreshRes.access_token;
          setToken(token);
        }
        if (token) {
          await fetchProfile();
        }
      } catch {
        removeToken();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [fetchProfile]);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await authApi.login({ email, password });
      setToken(res.access_token);
      setUser({
        id: res.user_id || 'admin-id',
        email: res.email,
        role: res.role,
        school_id: res.school_id,
        schoolName: "142-Umumta'lim Maktabi",
        fullName: res.role === 'TEACHER' ? "O'qituvchi" : 'Maktab Ma\'muri',
      });
      return { success: true };
    } catch (err: any) {
      return {
        success: false,
        error: err.message || "Email yoki parol noto'g'ri",
      };
    }
  };

  const logout = async () => {
    await authApi.logout().catch(() => {});
    removeToken();
    setUser(null);
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  };

  const refreshUser = async () => {
    await fetchProfile();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth faqat AuthProvider ichida ishlatilishi kerak');
  }
  return context;
};
