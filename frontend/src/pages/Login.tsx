import LoginForm from "../components/LoginForm/LoginForm";
import { login } from "../services/api";

export default function Login() {
  async function handleLogin(email: string, senha: string) {
    try {
      const usuario = await login(email, senha);
      console.log("Login OK:", usuario);
      // aqui depois: redirecionar para o dashboard, salvar token, etc.
    } catch (erro) {
      console.error("Falha no login:", erro);
    }
  }

  return <LoginForm onSubmit={handleLogin} />;
}