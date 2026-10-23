import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { auth, refreshSession, setSessionLostHandler, type User } from "./api";

type AuthState = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    // Restore the session from the refresh cookie on page load.
    refreshSession().then((u) => {
      setUser(u);
      setReady(true);
    });
    setSessionLostHandler(() => {
      setUser(null);
      queryClient.clear();
    });
  }, [queryClient]);

  const login = useCallback(async (email: string, password: string) => setUser(await auth.login(email, password)), []);
  const register = useCallback(
    async (email: string, password: string) => setUser(await auth.register(email, password)),
    [],
  );
  const logout = useCallback(async () => {
    await auth.logout().catch(() => undefined);
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo(() => ({ user, ready, login, register, logout }), [user, ready, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
