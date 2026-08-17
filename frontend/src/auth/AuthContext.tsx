import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import * as authApi from "../api/auth";
import {
  clearSession,
  getStoredToken,
  getStoredUser,
  setSession,
} from "../api/client";
import type { UserInfo } from "../lib/types";

interface AuthContextValue {
  token: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<UserInfo | null>(() => getStoredUser());

  const login = useCallback(async (username: string, password: string) => {
    const response = await authApi.login(username, password);
    const info: UserInfo = { username: response.username, role: response.role };
    setSession(response.access_token, info);
    setToken(response.access_token);
    setUser(info);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const info = await authApi.fetchMe();
    const token = getStoredToken();
    if (token) setSession(token, info);
    setUser(info);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      login,
      logout,
      refreshUser,
    }),
    [token, user, login, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}