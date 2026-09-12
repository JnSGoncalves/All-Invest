export interface Usuario {
  id: string;
  nome: string;
  email: string;
}

export interface LoginResponse {
  usuario: Usuario;
  token: string;
}