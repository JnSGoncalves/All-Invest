export interface Usuario {
  id: string;
  nome: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}