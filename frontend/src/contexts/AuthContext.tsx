import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { User } from "../types/auth";
import { AuthContext, type AuthContextValue } from "./auth-context";
import { clearAuthSession, getCachedUser } from "../services/auth-storage";
import {
  getCurrentUser,
  login as requestLogin,
  logout as requestLogout,
  startGoogleLogin,
} from "../services/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getCachedUser);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        clearAuthSession();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(email, password) {
        const auth = await requestLogin(email, password);
        setUser(auth.user);
      },
      loginWithGoogle: startGoogleLogin,
      async logout() {
        try {
          await requestLogout();
        } finally {
          setUser(null);
        }
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
