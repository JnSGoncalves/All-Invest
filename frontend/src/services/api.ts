import type { LoginResponse } from "../types/auth";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3000";

export async function login(
  email: string,
  senha: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });

  if (!response.ok) {
    throw new Error("E-mail ou senha inválidos");
  }

  return response.json();
}