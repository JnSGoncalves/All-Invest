import { useState, type FormEvent } from "react";
import { createBroker, type Broker } from "../../services/api";
import Icon from "./Icon";
import Modal from "./Modal";

interface BrokerDialogProps {
  onClose: () => void;
  onCreated: (broker: Broker) => void;
}

export default function BrokerDialog({ onClose, onCreated }: BrokerDialogProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Informe o nome da corretora.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      onCreated(await createBroker(name.trim()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível cadastrar a corretora.");
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Nova corretora"
      description="A corretora fica disponível para todos os usuários ao registrar operações."
      onClose={onClose}
    >
      <form className="modal-form" onSubmit={handleSubmit} noValidate>
        <div className={`form-field ${error ? "has-error" : ""}`}>
          <label htmlFor="broker-name">Nome da corretora</label>
          <input
            id="broker-name"
            value={name}
            onChange={(event) => { setName(event.target.value); setError(null); }}
            placeholder="Ex.: BTG Pactual"
            maxLength={150}
            autoFocus
            aria-invalid={Boolean(error)}
          />
          {error && <p className="field-error" role="alert"><Icon name="alert" size={14} /> {error}</p>}
        </div>
        <div className="modal-actions">
          <button type="button" className="ghost-button" onClick={onClose}>Cancelar</button>
          <button type="submit" className="solid-button" disabled={saving}>{saving ? "Cadastrando…" : "Cadastrar corretora"}</button>
        </div>
      </form>
    </Modal>
  );
}
