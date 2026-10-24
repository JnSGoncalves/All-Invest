import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../contexts/auth-context";
import "../components/LoginForm/LoginForm.css";
import logo from "../assets/all-invest-logo.png";

export default function Login() {
  const isRegister = window.location.pathname === "/cadastro";
  const { login, register, loginWithGoogle } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    const resetGoogleLoading = () => setGoogleLoading(false);
    window.addEventListener("pageshow", resetGoogleLoading);
    return () => window.removeEventListener("pageshow", resetGoogleLoading);
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isRegister) await register(name.trim(), email.trim(), password);
      else await login(email.trim(), password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível concluir sua solicitação.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-story">
        <img className="auth-logo" src={logo} alt="All Invest" />
        <div className="story-copy">
          <span className="eyebrow"><span className="status-dot" /> SUA CARTEIRA, EM UM SÓ LUGAR</span>
          <h1>Invista com uma visão mais clara.</h1>
          <p>Organize suas ações, acompanhe suas posições e mantenha o controle da sua jornada financeira.</p>
          <div className="story-metrics">
            <div><strong>01</strong><span>carteira centralizada</span></div>
            <div><strong>24/7</strong><span>acesso aos seus dados</span></div>
          </div>
        </div>
        <span className="story-watermark" aria-hidden="true">AI</span>
        <p className="story-footnote">INVESTIMENTOS COM MAIS INTENÇÃO</p>
      </section>

      <section className="auth-panel">
        <div className="auth-form-wrap">
          <div className="auth-heading">
            <span className="eyebrow">BEM-VINDO À ALL INVEST</span>
            <h2>{isRegister ? "Crie sua conta" : "Acesse sua conta"}</h2>
            <p>{isRegister ? "Comece a organizar seus investimentos em um só lugar." : "Entre para acompanhar sua carteira de investimentos."}</p>
          </div>

          <button className="google-button" type="button" onClick={() => { setError(null); setGoogleLoading(true); loginWithGoogle(); }} disabled={googleLoading || submitting}>
              <span className="google-mark" aria-hidden="true">G</span>
              {googleLoading ? "Abrindo o Google…" : "Continuar com Google"}
          </button>

          <div className="auth-divider"><span>ou use seu e-mail</span></div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {isRegister && <label>Nome completo<input value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" placeholder="Como podemos chamar você?" required minLength={1} maxLength={120} /></label>}
            <label>E-mail<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" placeholder="voce@email.com" required /></label>
            <label>Senha<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={isRegister ? "new-password" : "current-password"} placeholder={isRegister ? "Pelo menos 8 caracteres" : "Sua senha"} required minLength={isRegister ? 8 : 1} maxLength={72} /></label>
            {error && <p className="auth-error" role="alert">{error}</p>}
            <button className="primary-button" type="submit" disabled={submitting || googleLoading}>
              {submitting ? "Aguarde…" : isRegister ? "Criar minha conta" : "Entrar na plataforma"}<span aria-hidden="true">↗</span>
            </button>
          </form>

          <p className="auth-switch">
            {isRegister ? "Já tem uma conta? " : "Ainda não tem conta? "}
            <a href={isRegister ? "/" : "/cadastro"}>{isRegister ? "Entrar" : "Crie sua conta"}</a>
          </p>
        </div>
        <p className="auth-panel-footer">© 2026 All Invest <span>•</span> Feito para cuidar melhor do seu patrimônio</p>
      </section>
    </main>
  );
}
