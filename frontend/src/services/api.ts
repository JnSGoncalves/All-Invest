import type { LoginResponse } from "../types/auth";
import type { AcaoResponse } from "../types/acao";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3000";

export async function cadastrarAcao(
  nomeAtivo: string,
  quantidade: number,
  corretora: string
): Promise<AcaoResponse> {
  const response = await fetch(`${API_URL}/acoes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nomeAtivo, quantidade, corretora }),
  });

  if (!response.ok) {
    // Tenta usar a mensagem que a API mandar (ex: CA02 - ativo inexistente na B3);
    // se não vier nada aproveitável, cai no texto padrão do critério de aceite.
    const corpoErro = await response.json().catch(() => null);
    throw new Error(corpoErro?.message ?? "Tente novamente! Esse ativo não existe na B3.");
  }

  return response.json();
}

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

export async function cadastrar(
  nome: string,
  email: string,
  senha: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/cadastro`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, email, senha }),
  });

  if (!response.ok) {
    throw new Error("Não foi possível concluir o cadastro");
  }

  return response.json();

}