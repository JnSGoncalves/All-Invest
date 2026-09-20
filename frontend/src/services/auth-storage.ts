import type { AuthResponse, TokenSession, User } from "../types/auth";

const ACCESS_TOKEN_KEY = "allinvest.access_token";
const ACCESS_EXPIRES_AT_KEY = "allinvest.access_expires_at";
const REFRESH_TOKEN_KEY = "allinvest.refresh_token";
const USER_KEY = "allinvest.user";

export function saveAuthResponse(response: AuthResponse): void {
  saveTokenSession({
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    expiresAt: Date.now() + response.expires_in * 1000,
  });
  saveUser(response.user);
}

export function saveTokenSession(session: TokenSession): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
  sessionStorage.setItem(ACCESS_EXPIRES_AT_KEY, String(session.expiresAt));
  localStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getCachedUser(): User | null {
  const rawUser = localStorage.getItem(USER_KEY);
  if (!rawUser) return null;

  try {
    return JSON.parse(rawUser) as User;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function saveUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
