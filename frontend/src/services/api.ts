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

export type TradeSide = "BUY" | "SELL";

export interface Position {
  stock_name: string;
  company_name: string;
  stock_quantity: number;
  preco_medio: number;
  portfolio_id: number | null;
  portfolio_name: string | null;
}

export interface TradeInput {
  stock_name: string;
  stock_quantity: number;
  stock_price?: number;
  auto_cotacao?: boolean;
  broker_id: number;
  trade_side: TradeSide;
  trade_date?: string;
  portfolio_id?: number;
}

export interface Trade {
  stock_name: string;
  company_name: string;
  stock_quantity: number;
  stock_price: number;
  broker_name: string;
  trade_side: TradeSide;
  trade_date: string;
}

export interface TickerSuggestion {
  stock_name: string;
  company_name: string;
}

export interface Portfolio {
  portfolio_id: number;
  portfolio_name: string;
  description: string | null;
}

export async function getPositions(): Promise<Position[]> {
  const response = await authenticatedFetch("/api/stocks/carteira");
  if (!response.ok) throw await errorFromResponse(response);
  // A API serializa Decimal como string; a tela trabalha com number.
  const positions = (await response.json()) as Position[];
  return positions.map((position) => ({
    ...position,
    stock_quantity: Number(position.stock_quantity),
    preco_medio: Number(position.preco_medio),
    portfolio_id: position.portfolio_id ?? null,
    portfolio_name: position.portfolio_name ?? null,
  }));
}

export async function createTrade(trade: TradeInput): Promise<Trade> {
  const response = await authenticatedFetch("/api/stocks", {
    method: "POST",
    body: JSON.stringify(trade),
  });
  if (!response.ok) throw await errorFromResponse(response);
  const created = (await response.json()) as Trade;
  return {
    ...created,
    stock_quantity: Number(created.stock_quantity),
    stock_price: Number(created.stock_price),
  };
}

export async function removePosition(stockName: string): Promise<void> {
  const response = await authenticatedFetch(
    `/api/stocks/${encodeURIComponent(stockName)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw await errorFromResponse(response);
}

export async function autocompleteTickers(
  query: string,
  signal?: AbortSignal,
): Promise<TickerSuggestion[]> {
  const params = new URLSearchParams({ q: query, limit: "8" });
  const response = await authenticatedFetch(`/api/stocks/autocomplete?${params}`, { signal });
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as TickerSuggestion[];
}

export async function validateTicker(stockName: string): Promise<TickerSuggestion> {
  const response = await authenticatedFetch(
    `/api/stocks/validar/${encodeURIComponent(stockName)}`,
  );
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as TickerSuggestion;
}

export async function assignPositionPortfolio(
  stockName: string,
  portfolioId: number,
): Promise<void> {
  const response = await authenticatedFetch(
    `/api/stocks/${encodeURIComponent(stockName)}/portfolio`,
    { method: "PUT", body: JSON.stringify({ portfolio_id: portfolioId }) },
  );
  if (!response.ok) throw await errorFromResponse(response);
}

export async function getPortfolios(): Promise<Portfolio[]> {
  const response = await authenticatedFetch("/api/portfolios");
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as Portfolio[];
}

export async function createPortfolio(
  portfolioName: string,
  description?: string,
): Promise<Portfolio> {
  const response = await authenticatedFetch("/api/portfolios", {
    method: "POST",
    body: JSON.stringify({ portfolio_name: portfolioName, description: description || null }),
  });
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as Portfolio;
}

export async function deletePortfolio(portfolioId: number): Promise<void> {
  const response = await authenticatedFetch(`/api/portfolios/${portfolioId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw await errorFromResponse(response);
}

export interface Broker {
  broker_id: number;
  broker_name: string;
}

export async function getBrokers(): Promise<Broker[]> {
  const response = await authenticatedFetch("/api/brokers");
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as Broker[];
}

export async function createBroker(brokerName: string): Promise<Broker> {
  const response = await authenticatedFetch("/api/brokers", {
    method: "POST",
    body: JSON.stringify({ broker_name: brokerName }),
  });
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as Broker;
}

export type ReturnPeriod = "1w" | "1mo" | "3mo" | "max";

export interface AssetReturn {
  stock_name: string;
  company_name: string;
  portfolio_name: string | null;
  start_quantity: number;
  end_quantity: number;
  start_price: number | null;
  end_price: number;
  start_value: number;
  bought: number;
  sold: number;
  end_value: number;
  gain: number;
  gain_rate: number | null;
}

export interface ReturnPoint {
  date: string;
  invested: number;
  value: number;
  gain: number;
}

export interface Returns {
  period: ReturnPeriod;
  start_date: string | null;
  end_date: string | null;
  has_assets: boolean;
  start_value: number;
  bought: number;
  sold: number;
  end_value: number;
  gain: number;
  gain_rate: number | null;
  assets: AssetReturn[];
  series: ReturnPoint[];
  unavailable: string[];
}

const optionalNumber = (value: unknown) => (value === null || value === undefined ? null : Number(value));

export async function getReturns(period: ReturnPeriod, signal?: AbortSignal): Promise<Returns> {
  const params = new URLSearchParams({ periodo: period });
  const response = await authenticatedFetch(`/api/rendimentos?${params}`, { signal });
  if (!response.ok) throw await errorFromResponse(response);
  // Valores monetários chegam como string (Decimal); a tela trabalha com number.
  const body = (await response.json()) as Returns;
  return {
    ...body,
    start_value: Number(body.start_value),
    bought: Number(body.bought),
    sold: Number(body.sold),
    end_value: Number(body.end_value),
    gain: Number(body.gain),
    gain_rate: optionalNumber(body.gain_rate),
    assets: body.assets.map((asset) => ({
      ...asset,
      start_price: optionalNumber(asset.start_price),
      end_price: Number(asset.end_price),
      start_value: Number(asset.start_value),
      bought: Number(asset.bought),
      sold: Number(asset.sold),
      end_value: Number(asset.end_value),
      gain: Number(asset.gain),
      gain_rate: optionalNumber(asset.gain_rate),
    })),
    series: body.series.map((point) => ({
      date: point.date,
      invested: Number(point.invested),
      value: Number(point.value),
      gain: Number(point.gain),
    })),
  };
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
