import type { ApiErrorBody, AuthResponse, User } from "../types/auth";
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  saveAuthResponse,
  saveTokenSession,
} from "./auth-storage";

// Requests stay same-origin; the Vite/Nginx proxy adds the private API key.
export const API_URL = "";

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
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return headers;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = `Erro HTTP ${response.status}.`;
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) {
      message = body.detail.map((item) => item.msg).filter(Boolean).join(" ");
    }
  } catch {
    // Mantém a mensagem HTTP quando a resposta não é JSON.
  }
  return new ApiError(message, response.status);
}

async function refreshSession(): Promise<AuthResponse> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearAuthSession();
    throw new ApiError("Sua sessão terminou. Entre novamente.", 401);
  }

  const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    const error = await errorFromResponse(response);
    // Falhas de rede/configuração não revogam a sessão que existe no Postgres.
    if (error.status === 401 && !error.message.toLowerCase().includes("api key")) {
      clearAuthSession();
    }
    throw error;
  }

  const auth = (await response.json()) as AuthResponse;
  saveAuthResponse(auth);
  return auth;
}

async function ensureRefreshed(): Promise<AuthResponse> {
  if (!refreshPromise) {
    refreshPromise = withSessionLock(refreshSession).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function withSessionLock<T>(action: () => Promise<T>): Promise<T> {
  // Abas compartilham o refresh token; a rotação precisa ser serializada.
  if (navigator.locks) return navigator.locks.request("allinvest-session", action);
  return action();
}

export async function restoreSession(): Promise<User | null> {
  if (!getRefreshToken()) {
    clearAuthSession();
    return null;
  }
  // O usuário só entra na área protegida após validar a sessão persistida.
  return (await ensureRefreshed()).user;
}

function needsAuthentication(response: Response): boolean {
  return response.status === 401
    && response.headers.get("WWW-Authenticate")?.toLowerCase().startsWith("bearer") === true;
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

  if (needsAuthentication(response)) {
    accessToken = (await ensureRefreshed()).access_token;
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: buildHeaders(init.headers, accessToken),
    });
  }

  if (needsAuthentication(response)) clearAuthSession();

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

export async function register(
  name: string,
  email: string,
  password: string,
): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/api/users`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) throw await errorFromResponse(response);
  return login(email, password);
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

  if (!accessToken || !refreshToken || !Number.isFinite(expiresIn) || expiresIn <= 0) {
    throw new ApiError("Resposta de autenticação do Google inválida.", 401);
  }

  saveTokenSession({
    accessToken,
    refreshToken,
    expiresAt: Date.now() + expiresIn * 1000,
  });

  return getCurrentUser();
}

export async function getCurrentUser(): Promise<User> {
  const response = await authenticatedFetch("/api/v1/auth/me");
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as User;
}

export interface Position {
  stock_name: string;
  company_name: string;
  stock_quantity: number;
  preco_medio: number;
}

export interface TradeInput {
  stock_name: string;
  stock_quantity: number;
  stock_price: number;
  broker_id: number;
  trade_side: "BUY" | "SELL";
}

export async function getPositions(): Promise<Position[]> {
  const response = await authenticatedFetch("/api/stocks/carteira");
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as Position[];
}

export async function createTrade(trade: TradeInput): Promise<void> {
  const response = await authenticatedFetch("/api/stocks", {
    method: "POST",
    body: JSON.stringify(trade),
  });
  if (!response.ok) throw await errorFromResponse(response);
}

export async function removePosition(stockName: string): Promise<void> {
  const response = await authenticatedFetch(
    `/api/stocks/${encodeURIComponent(stockName)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw await errorFromResponse(response);
}

export async function logout(): Promise<void> {
  if (refreshPromise) await refreshPromise;
  await withSessionLock(async () => {
    if (!getRefreshToken()) {
      clearAuthSession();
      return;
    }
    // Usa o token atual sob o mesmo lock para evitar revogar um token já rotacionado.
    let auth: AuthResponse;
    try {
      auth = await refreshSession();
    } catch (error) {
      if (!getRefreshToken()) return; // O servidor já encerrou esta sessão.
      throw error;
    }
    const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: buildHeaders(undefined, auth.access_token),
      body: JSON.stringify({ refresh_token: auth.refresh_token }),
    });
    if (!response.ok) throw await errorFromResponse(response);
    clearAuthSession();
  });
}
