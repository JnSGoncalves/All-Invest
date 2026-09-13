import { useState, type FormEvent } from "react";
import "./CadastroForm.css";
import logo from "../../assets/all-invest-logo.png";

interface FormErrors {
  nome?: string;
  email?: string;
  senha?: string;
  confirmarSenha?: string;
}

interface CadastroFormProps {
  onSubmit?: (nome: string, email: string, senha: string) => Promise<void> | void;
}

export default function CadastroForm({ onSubmit }: CadastroFormProps) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [erros, setErros] = useState<FormErrors>({});
  const [enviando, setEnviando] = useState(false);
  const [sucesso, setSucesso] = useState(false);

  function validarNome(valor: string): string | undefined {
    if (!valor.trim()) return "Informe seu nome completo";
    if (valor.trim().length < 3) return "Nome muito curto";
    return undefined;
  }

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

  function validarConfirmarSenha(valor: string, senhaAtual: string): string | undefined {
    if (!valor) return "Confirme sua senha";
    if (valor !== senhaAtual) return "As senhas não coincidem";
    return undefined;
  }

  function validarCampos(): boolean {
    const novosErros: FormErrors = {
      nome: validarNome(nome),
      email: validarEmail(email),
      senha: validarSenha(senha),
      confirmarSenha: validarConfirmarSenha(confirmarSenha, senha),
    };
    setErros(novosErros);
    return Object.values(novosErros).every((erro) => !erro);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSucesso(false);
    if (!validarCampos()) return;

    setEnviando(true);
    try {
      if (onSubmit) {
        await onSubmit(nome, email, senha);
      } else {
        console.log("Cadastro:", { nome, email, senha });
      }
      setSucesso(true);
      setNome("");
      setEmail("");
      setSenha("");
      setConfirmarSenha("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="register-screen">
      <div className="register-card">
        <h1 className="register-logo">
          <img src={logo} alt="All-invest" />
        </h1>

        <p className="register-subtitle">Crie sua conta para começar a investir.</p>

        <form onSubmit={handleSubmit} noValidate className="register-form">
          <div className={`field ${erros.nome ? "field-error" : ""}`}>
            <label htmlFor="nome">Nome completo</label>
            <input
              id="nome"
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              aria-invalid={!!erros.nome}
              placeholder="Seu nome"
              autoComplete="name"
            />
            {erros.nome && (
              <span className="field-message" role="alert">
                {erros.nome}
              </span>
            )}
          </div>

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
              autoComplete="new-password"
            />
            {erros.senha && (
              <span className="field-message" role="alert">
                {erros.senha}
              </span>
            )}
          </div>

          <div className={`field ${erros.confirmarSenha ? "field-error" : ""}`}>
            <label htmlFor="confirmarSenha">Confirmar senha</label>
            <input
              id="confirmarSenha"
              type="password"
              value={confirmarSenha}
              onChange={(e) => setConfirmarSenha(e.target.value)}
              aria-invalid={!!erros.confirmarSenha}
              placeholder="••••••••"
              autoComplete="new-password"
            />
            {erros.confirmarSenha && (
              <span className="field-message" role="alert">
                {erros.confirmarSenha}
              </span>
            )}
          </div>

          {sucesso && (
            <p className="register-success" role="status">
              Cadastro realizado com sucesso!
            </p>
          )}

          <button type="submit" className="register-button" disabled={enviando}>
            {enviando ? "Cadastrando…" : "Criar conta"}
          </button>
        </form>

        <p className="register-footer">Já tem conta? <a href="/login">Faça login.</a></p>
      </div>
    </div>
  );
}