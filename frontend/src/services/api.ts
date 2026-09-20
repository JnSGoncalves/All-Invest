import type { ApiErrorBody, AuthResponse, User } from "../types/auth";
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  saveAuthResponse,
  saveTokenSession,
  saveUser,
} from "./auth-storage";

export const API_URL = (
  import.meta.env.VITE_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;
let refreshPromise: Promise<AuthResponse> | null = null;

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildHeaders(initHeaders?: HeadersInit, accessToken?: string): Headers {
  const headers = new Headers(initHeaders);
  headers.set("Content-Type", "application/json");
  if (API_KEY) headers.set("X-API-Key", API_KEY);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return headers;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = `Erro HTTP ${response.status}.`;
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body.detail) message = body.detail;
  } catch {
    // Mantém a mensagem HTTP quando a resposta não é JSON.
  }
  return new ApiError(message, response.status);
}

async function refreshSession(): Promise<AuthResponse> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new ApiError("Sessão expirada.", 401);

  const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearAuthSession();
    throw await errorFromResponse(response);
  }

  const auth = (await response.json()) as AuthResponse;
  saveAuthResponse(auth);
  return auth;
}

async function ensureRefreshed(): Promise<AuthResponse> {
  if (!refreshPromise) {
    refreshPromise = refreshSession().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function authenticatedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  let accessToken = getAccessToken();
  if (!accessToken) accessToken = (await ensureRefreshed()).access_token;

  let response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: buildHeaders(init.headers, accessToken),
  });

  if (response.status === 401) {
    accessToken = (await ensureRefreshed()).access_token;
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: buildHeaders(init.headers, accessToken),
    });
  }

  return response;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) throw await errorFromResponse(response);

  const auth = (await response.json()) as AuthResponse;
  saveAuthResponse(auth);
  return auth;
}

export function startGoogleLogin(): void {
  window.location.assign(`${API_URL}/api/v1/auth/google`);
}

export async function completeGoogleLogin(): Promise<User> {
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  const accessToken = fragment.get("access_token");
  const refreshToken = fragment.get("refresh_token");
  const expiresIn = Number(fragment.get("expires_in"));

  window.history.replaceState(null, "", window.location.pathname);

  if (!accessToken || !refreshToken || !Number.isFinite(expiresIn)) {
    throw new ApiError("Resposta de autenticação do Google inválida.", 401);
  }

  saveTokenSession({
    accessToken,
    refreshToken,
    expiresAt: Date.now() + expiresIn * 1000,
  });

  const user = await getCurrentUser();
  saveUser(user);
  return user;
}

export async function getCurrentUser(): Promise<User> {
  const response = await authenticatedFetch("/api/v1/auth/me");
  if (!response.ok) throw await errorFromResponse(response);
  const user = (await response.json()) as User;
  saveUser(user);
  return user;
}

export async function logout(): Promise<void> {
  try {
    let refreshToken = getRefreshToken();
    let accessToken = getAccessToken();
    if (!refreshToken) return;

    if (!accessToken) {
      const auth = await ensureRefreshed();
      accessToken = auth.access_token;
      refreshToken = auth.refresh_token;
    }

    let response = await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: buildHeaders(undefined, accessToken),
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (response.status === 401) {
      const auth = await ensureRefreshed();
      response = await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: buildHeaders(undefined, auth.access_token),
        body: JSON.stringify({ refresh_token: auth.refresh_token }),
      });
    }

    if (!response.ok) throw await errorFromResponse(response);
  } finally {
    clearAuthSession();
  }
}
