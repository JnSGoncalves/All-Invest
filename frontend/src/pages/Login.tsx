import { useState } from "react";
import LoginForm from "../components/LoginForm/LoginForm";
import { useAuth } from "../contexts/auth-context";

export default function Login() {
  const [erro, setErro] = useState<string | null>(null);
  const [entrandoGoogle, setEntrandoGoogle] = useState(false);
  const { login, loginWithGoogle } = useAuth();

  async function handleLogin(email: string, senha: string) {
    setErro(null);

    try {
      await login(email, senha);
    } catch (erro: unknown) {
      setErro(
        erro instanceof Error
          ? erro.message
          : "Não foi possível realizar o login.",
      );
    }
  }

  function handleGoogleLogin() {
    setErro(null);
    setEntrandoGoogle(true);
    loginWithGoogle();
  }

  return (
    <LoginForm
      onSubmit={handleLogin}
      onGoogleLogin={handleGoogleLogin}
      googleLoading={entrandoGoogle}
      erro={erro}
    />
  );
}
