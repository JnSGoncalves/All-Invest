import { useState } from "react";
import LoginForm from "../components/LoginForm/LoginForm";
import { login } from "../services/api";

export default function Login() {
  const [token, setToken] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function handleLogin(email: string, senha: string) {
    setErro(null);

    try {
      const resposta = await login(email, senha);
      setToken(resposta.access_token);
    } catch (erro: unknown) {
      setErro(
        erro instanceof Error
          ? erro.message
          : "Não foi possível realizar o login."
      );
    }
  }

  if (token) {
    return <p role="status">Login realizado com sucesso!</p>;
  }

  return <LoginForm onSubmit={handleLogin} erro={erro} />;
}