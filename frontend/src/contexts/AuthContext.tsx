import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { User } from "../types/auth";
import { AuthContext, type AuthContextValue } from "./auth-context";
import {
  clearAuthSession,
  getRefreshToken,
  REFRESH_TOKEN_KEY,
  SESSION_CLEARED_EVENT,
  SESSION_UPDATED_EVENT,
} from "../services/auth-storage";
import {
  ApiError,
  restoreSession,
  login as requestLogin,
  logout as requestLogout,
  register as requestRegister,
  startGoogleLogin,
} from "../services/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const clearUser = () => { setUser(null); setSessionError(null); };
    const updateUser = (event: Event) => {
      setUser((event as CustomEvent<User>).detail);
      setSessionError(null);
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key === REFRESH_TOKEN_KEY && !event.newValue) clearAuthSession();
    };
    window.addEventListener(SESSION_CLEARED_EVENT, clearUser);
    window.addEventListener(SESSION_UPDATED_EVENT, updateUser);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(SESSION_CLEARED_EVENT, clearUser);
      window.removeEventListener(SESSION_UPDATED_EVENT, updateUser);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  useEffect(() => {
    let active = true;
    restoreSession()
      .then((authenticatedUser) => { if (active) setUser(authenticatedUser); })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401 && !getRefreshToken()) {
          setUser(null);
          return;
        }
        setSessionError("Não foi possível verificar sua sessão. Confira a conexão e tente novamente.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      sessionError,
      retrySession() {
        setLoading(true);
        setSessionError(null);
        setAttempt((previous) => previous + 1);
      },
      async login(email, password) {
        const auth = await requestLogin(email, password);
        setUser(auth.user);
      },
      async register(name, email, password) {
        const auth = await requestRegister(name, email, password);
        setUser(auth.user);
      },
      loginWithGoogle: startGoogleLogin,
      async logout() {
        await requestLogout();
        setUser(null);
      },
    }),
    [loading, user, sessionError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
