import { useState, type FormEvent } from "react";
import { createPortfolio, type Portfolio } from "../../services/api";
import Icon from "./Icon";
import Modal from "./Modal";

interface PortfolioDialogProps {
  onClose: () => void;
  onCreated: (portfolio: Portfolio) => void;
}

export default function PortfolioDialog({ onClose, onCreated }: PortfolioDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Dê um nome para a carteira.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      onCreated(await createPortfolio(name.trim(), description.trim()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível criar a carteira.");
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Nova carteira"
      description="Agrupe seus ativos por objetivo, como dividendos, aposentadoria ou longo prazo."
      onClose={onClose}
    >
      <form className="modal-form" onSubmit={handleSubmit} noValidate>
        <div className={`form-field ${error ? "has-error" : ""}`}>
          <label htmlFor="portfolio-name">Nome da carteira</label>
          <input
            id="portfolio-name"
            value={name}
            onChange={(event) => { setName(event.target.value); setError(null); }}
            placeholder="Ex.: Dividendos"
            maxLength={100}
            autoFocus
            aria-invalid={Boolean(error)}
          />
          {error && <p className="field-error" role="alert"><Icon name="alert" size={14} /> {error}</p>}
        </div>
        <div className="form-field">
          <label htmlFor="portfolio-description">Descrição <span className="optional">(opcional)</span></label>
          <input
            id="portfolio-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Para que serve esta carteira?"
            maxLength={255}
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="ghost-button" onClick={onClose}>Cancelar</button>
          <button type="submit" className="solid-button" disabled={saving}>{saving ? "Criando…" : "Criar carteira"}</button>
        </div>
      </form>
    </Modal>
  );
}
