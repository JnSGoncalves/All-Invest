import { useState, type FormEvent } from "react";
import "./CadastroAcaoForm.css";

interface FormErrors {
  nomeAtivo?: string;
  quantidade?: string;
  corretora?: string;
}

interface CadastroAcaoFormProps {
  /**
   * Deve realizar a chamada à API de cadastro.
   * Se o ativo não existir na B3 (CA02), rejeite a Promise com a mensagem
   * "Tente novamente! Esse ativo não existe na B3." — o formulário exibe
   * esse erro automaticamente no campo "Ativo".
   */
  onSubmit?: (nomeAtivo: string, quantidade: number, corretora: string) => Promise<void>;
}

export default function CadastroAcaoForm({ onSubmit }: CadastroAcaoFormProps) {
  const [nomeAtivo, setNomeAtivo] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [corretora, setCorretora] = useState("");
  const [erros, setErros] = useState<FormErrors>({});
  const [enviando, setEnviando] = useState(false);

  function validarNomeAtivo(valor: string): string | undefined {
    if (!valor.trim()) return "Informe o nome do ativo";
    return undefined;
  }

  function validarQuantidade(valor: string): string | undefined {
    if (!valor.trim()) return "Informe a quantidade";
    const numero = Number(valor);
    if (Number.isNaN(numero)) return "Quantidade inválida";
    if (numero <= 0) return "A quantidade deve ser maior que zero";
    if (!Number.isInteger(numero)) return "A quantidade deve ser um número inteiro";
    return undefined;
  }

  function validarCorretora(valor: string): string | undefined {
    if (!valor.trim()) return "Informe a corretora";
    return undefined;
  }

  function validarCampos(): boolean {
    const novosErros: FormErrors = {
      nomeAtivo: validarNomeAtivo(nomeAtivo),
      quantidade: validarQuantidade(quantidade),
      corretora: validarCorretora(corretora),
    };
    setErros(novosErros);
    return !novosErros.nomeAtivo && !novosErros.quantidade && !novosErros.corretora;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validarCampos()) return;

    setEnviando(true);
    try {
      if (onSubmit) {
        await onSubmit(nomeAtivo.trim().toUpperCase(), Number(quantidade), corretora.trim());
      } else {
        console.log("Cadastro de ação:", { nomeAtivo, quantidade, corretora });
      }
    } catch (erro) {
      // CA02: ativo inexistente na B3 (ou outro erro vindo da API)
      const mensagem =
        erro instanceof Error ? erro.message : "Tente novamente! Esse ativo não existe na B3.";
      setErros((prev) => ({ ...prev, nomeAtivo: mensagem }));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="cadastro-acao-screen">
      <div className="cadastro-acao-card">
        <h1 className="cadastro-acao-title">Cadastrar ação</h1>
        <p className="cadastro-acao-subtitle">
          Informe os dados do ativo que você possui em carteira.
        </p>

        <form onSubmit={handleSubmit} noValidate className="cadastro-acao-form">
          <div className={`field ${erros.nomeAtivo ? "field-error" : ""}`}>
            <label htmlFor="nomeAtivo">Ativo</label>
            <input
              id="nomeAtivo"
              type="text"
              value={nomeAtivo}
              onChange={(e) => setNomeAtivo(e.target.value)}
              aria-invalid={!!erros.nomeAtivo}
              placeholder="Ex: PETR4"
              autoComplete="off"
            />
            {erros.nomeAtivo && (
              <span className="field-message" role="alert">
                {erros.nomeAtivo}
              </span>
            )}
          </div>

          <div className={`field ${erros.quantidade ? "field-error" : ""}`}>
            <label htmlFor="quantidade">Quantidade</label>
            <input
              id="quantidade"
              type="number"
              min={1}
              step={1}
              value={quantidade}
              onChange={(e) => setQuantidade(e.target.value)}
              aria-invalid={!!erros.quantidade}
              placeholder="Ex: 100"
            />
            {erros.quantidade && (
              <span className="field-message" role="alert">
                {erros.quantidade}
              </span>
            )}
          </div>

          <div className={`field ${erros.corretora ? "field-error" : ""}`}>
            <label htmlFor="corretora">Corretora</label>
            <input
              id="corretora"
              type="text"
              value={corretora}
              onChange={(e) => setCorretora(e.target.value)}
              aria-invalid={!!erros.corretora}
              placeholder="Ex: XP Investimentos"
              autoComplete="off"
            />
            {erros.corretora && (
              <span className="field-message" role="alert">
                {erros.corretora}
              </span>
            )}
          </div>

          <button type="submit" className="cadastro-acao-button" disabled={enviando}>
            {enviando ? "Cadastrando…" : "Cadastrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
