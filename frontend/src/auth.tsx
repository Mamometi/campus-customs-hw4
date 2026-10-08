import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchMe, type AuthResponse, type User } from "./api";

const TOKEN_KEY = "cc_token";

interface AuthState {
  user: User | null;
  token: string | null;
  ready: boolean;
  setSession: (res: AuthResponse) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(!token);

  useEffect(() => {
    if (!token || user) return;
    fetchMe(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => setReady(true));
  }, [token, user]);

  function setSession(res: AuthResponse) {
    localStorage.setItem(TOKEN_KEY, res.token);
    setToken(res.token);
    setUser(res.user);
    setReady(true);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, token, ready, setSession, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
