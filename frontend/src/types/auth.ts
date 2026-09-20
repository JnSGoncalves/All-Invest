export interface User {
  user_id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface TokenSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export interface ApiErrorBody {
  detail?: string;
}
