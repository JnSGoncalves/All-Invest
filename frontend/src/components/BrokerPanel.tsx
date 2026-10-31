import { useState, type FormEvent } from "react";
import { createBroker, type Broker } from "../services/api";

interface Props {
  brokers: Broker[]; loading: boolean; error: string | null;
  onCreated: (broker: Broker) => void;
}

export default function BrokerPanel({ brokers, loading, error, onCreated }: Props) {
  const [name, setName] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setNotice(null);
    if (!name.trim() || name.trim().length > 150) { setFieldError("Informe o nome da corretora com até 150 caracteres."); return; }
    setFieldError(null); setSaving(true);
    try {
      const broker = await createBroker(name.trim());
      onCreated(broker); setName(""); setNotice("Corretora cadastrada com sucesso.");
    } catch (reason) {
      setFieldError(reason instanceof Error ? reason.message : "Não foi possível cadastrar a corretora.");
    } finally { setSaving(false); }
  }

  return <section className="panel feature-panel" id="corretoras" aria-labelledby="brokers-heading">
    <div className="panel-heading"><div><span className="eyebrow">SUAS CONTAS</span><h2 id="brokers-heading">Corretoras</h2></div></div>
    {error && <p className="feature-error" role="alert">{error}</p>}
    {loading ? <p className="feature-copy" role="status">Carregando corretoras…</p>
      : !error && (brokers.length ? <ul className="broker-list">{brokers.map(broker => <li key={broker.broker_id}>{broker.broker_name}</li>)}</ul>
        : <p className="feature-copy">Nenhuma corretora cadastrada. Cadastre uma corretora para começar.</p>)}
    <form className="trade-form broker-form" onSubmit={submit} noValidate>
      <label>Nome da corretora<input value={name} onChange={event => setName(event.target.value)} required maxLength={150}
        aria-invalid={!!fieldError} aria-describedby={fieldError ? "broker-name-error" : undefined}/></label>
      {fieldError && <p id="broker-name-error" className="feature-error" role="alert">{fieldError}</p>}
      <button className="trade-submit" disabled={saving}>{saving ? "Cadastrando…" : "Cadastrar corretora"}</button>
      {notice && <p className="feature-success" role="status">{notice}</p>}
    </form>
  </section>;
}
