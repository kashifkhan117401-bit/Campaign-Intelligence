import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { authApi, clearStoredTokens, getStoredTokens, setStoredTokens } from "../services/api";
import { useToast } from "./ToastContext";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, captcha?: { captcha_token: string; captcha_answer: string }) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
    captcha_token?: string;
    captcha_answer?: string;
    accepted_terms?: boolean;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();
  const lastExpiredToastAt = useRef(0);

  const refreshUser = useCallback(async () => {
    try {
      const me = await authApi.me({ skipRedirect: true });
      setUser(me);
    } catch {
      clearStoredTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  // Handle 401 session expiry purely client-side via React Router (never hard-reloading /login)
  useEffect(() => {
    const handleAuthExpired = (evt: Event) => {
      clearStoredTokens();
      setUser(null);
      const now = Date.now();
      if (now - lastExpiredToastAt.current > 3000) {
        lastExpiredToastAt.current = now;
        const msg = (evt as CustomEvent<{ message?: string }>).detail?.message || "Please sign in again.";
        notify("error", "Session expired", msg);
      }
    };
    window.addEventListener("ci:auth-expired", handleAuthExpired);
    return () => window.removeEventListener("ci:auth-expired", handleAuthExpired);
  }, [notify]);

  const login = useCallback(
    async (email: string, password: string, captcha?: { captcha_token: string; captcha_answer: string }) => {
      const res = await authApi.login({
        email,
        password,
        captcha_token: captcha?.captcha_token,
        captcha_answer: captcha?.captcha_answer,
      });
      setStoredTokens(res.access_token, res.refresh_token);
      setUser(res.user);
    },
    []
  );

  const register = useCallback(
    async (payload: {
      email: string;
      password: string;
      full_name: string;
      company_name?: string;
      captcha_token?: string;
      captcha_answer?: string;
      accepted_terms?: boolean;
    }) => {
      const res = await authApi.register(payload);
      setStoredTokens(res.access_token, res.refresh_token);
      setUser(res.user);
    },
    []
  );

  const logout = useCallback(async () => {
    const { refreshToken } = getStoredTokens();
    try {
      await authApi.logout(refreshToken);
    } catch {
      // Ignore network errors during logout
    } finally {
      clearStoredTokens();
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
