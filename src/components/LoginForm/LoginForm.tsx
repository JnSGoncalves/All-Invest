import { useState, type FormEvent } from "react";
import "./LoginForm.css";
import logo from "C:/Users/pedro/all_invest/src/assets/all-invest-logo.png";

interface FormErrors {
  email?: string;
  senha?: string;
}

interface LoginFormProps {
  onSubmit?: (email: string, senha: string) => void;
}

export default function LoginForm({ onSubmit }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erros, setErros] = useState<FormErrors>({});
  const [enviando, setEnviando] = useState(false);

  function validarEmail(valor: string): string | undefined {
    if (!valor.trim()) return "Informe seu e-mail";
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!regex.test(valor)) return "E-mail inválido";
    return undefined;
  }

  function validarSenha(valor: string): string | undefined {
    if (!valor) return "Informe sua senha";
    if (valor.length < 6) return "Mínimo de 6 caracteres";
    return undefined;
  }

  function validarCampos(): boolean {
    const novosErros: FormErrors = {
      email: validarEmail(email),
      senha: validarSenha(senha),
    };
    setErros(novosErros);
    return !novosErros.email && !novosErros.senha;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validarCampos()) return;

    setEnviando(true);
    try {
      if (onSubmit) {
        await onSubmit(email, senha);
      } else {
        console.log("Login:", { email, senha });
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="login-logo">
          <img src={logo} alt="All-invest" />
        </h1>

        <p className="login-subtitle">
          Acompanhe sua carteira e acesse suas posições.
        </p>

        <form onSubmit={handleSubmit} noValidate className="login-form">
          <div className={`field ${erros.email ? "field-error" : ""}`}>
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={!!erros.email}
              placeholder="voce@email.com"
              autoComplete="email"
            />
            {erros.email && (
              <span className="field-message" role="alert">
                {erros.email}
              </span>
            )}
          </div>

          <div className={`field ${erros.senha ? "field-error" : ""}`}>
            <label htmlFor="senha">Senha</label>
            <input
              id="senha"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              aria-invalid={!!erros.senha}
              placeholder="••••••••"
              autoComplete="current-password"
            />
            {erros.senha && (
              <span className="field-message" role="alert">
                {erros.senha}
              </span>
            )}
          </div>

          <button type="submit" className="login-button" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <p className="login-footer">Ainda não tem conta? <a href="/cadastro">Crie uma</a>.</p>
      </div>
    </div>
  );
}