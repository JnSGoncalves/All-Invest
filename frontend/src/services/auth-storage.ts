import type { AuthResponse, TokenSession } from "../types/auth";

export const SESSION_CLEARED_EVENT = "allinvest:session-cleared";
export const SESSION_UPDATED_EVENT = "allinvest:session-updated";

const ACCESS_TOKEN_KEY = "allinvest.access_token";
const ACCESS_EXPIRES_AT_KEY = "allinvest.access_expires_at";
export const REFRESH_TOKEN_KEY = "allinvest.refresh_token";
const USER_KEY = "allinvest.user";

export function saveAuthResponse(response: AuthResponse): void {
  saveTokenSession({
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    expiresAt: Date.now() + response.expires_in * 1000,
  });
  window.dispatchEvent(new CustomEvent(SESSION_UPDATED_EVENT, { detail: response.user }));
}

export function saveTokenSession(session: TokenSession): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
  sessionStorage.setItem(ACCESS_EXPIRES_AT_KEY, String(session.expiresAt));
  localStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
}

export function getAccessToken(): string | null {
  const expiresAt = Number(sessionStorage.getItem(ACCESS_EXPIRES_AT_KEY));
  if (!Number.isFinite(expiresAt) || expiresAt <= Date.now() + 15_000) return null;
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearAuthSession(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event(SESSION_CLEARED_EVENT));
}
