import type { LoginResponse } from "../types/auth";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:4670";
const API_KEY = import.meta.env.VITE_API_KEY;

export async function login(
  email: string,
  senha: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({ email, password: senha }),
  });

  if (!response.ok) {
    throw new Error("E-mail ou senha inválidos");
  }

  return response.json();
}