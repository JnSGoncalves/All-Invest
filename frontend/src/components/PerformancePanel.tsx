import { useEffect, useState } from "react";
import { getPerformance, type Performance } from "../services/api";

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const percent = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
function daysAgo(days: number) {
  const day = new Date(`${today()}T12:00:00Z`);
  day.setUTCDate(day.getUTCDate() - days + 1);
  return day.toISOString().slice(0, 10);
}

export default function PerformancePanel({ revision }: { revision: number }) {
  const [period, setPeriod] = useState({ start: daysAgo(30), end: today(), preset: "30" });
  const [result, setResult] = useState<{ data?: Performance; error?: string; key: string }>();
  const key = `${period.start}/${period.end}/${revision}`;

  useEffect(() => {
    let active = true;
    getPerformance(period.start, period.end).then(data => {
      if (active) setResult({ data, key });
    }).catch((reason: unknown) => {
      if (active) setResult({ error: reason instanceof Error ? reason.message : "Não foi possível carregar os rendimentos.", key });
    });
    return () => { active = false; };
  }, [period.start, period.end, key]);

  const data = result?.key === key ? result.data : undefined;
  const error = result?.key === key ? result.error : undefined;
  return <section className="panel feature-panel" id="rendimentos" aria-labelledby="performance-heading">
    <div className="panel-heading"><div><span className="eyebrow">DESEMPENHO DA CARTEIRA</span><h2 id="performance-heading">Rendimentos por período</h2></div></div>
    <div className="trade-form period-filter">
      <label>Período<select value={period.preset} onChange={event => setPeriod(event.target.value === "custom" ? { ...period, preset: "custom" } : { start: daysAgo(Number(event.target.value)), end: today(), preset: event.target.value })}>
        <option value="7">Últimos 7 dias</option><option value="30">Últimos 30 dias</option><option value="365">Último ano</option><option value="custom">Personalizado</option>
      </select></label>
      <label>Data inicial<input type="date" value={period.start} max={period.end} onChange={event => { if (event.target.value) setPeriod({ ...period, start: event.target.value, preset: "custom" }); }}/></label>
      <label>Data final<input type="date" value={period.end} min={period.start} max={today()} onChange={event => { if (event.target.value) setPeriod({ ...period, end: event.target.value, preset: "custom" }); }}/></label>
    </div>
    {error ? <p className="feature-error" role="alert">{error}</p>
      : !data ? <p className="feature-copy" role="status">Carregando rendimentos…</p>
      : !data.has_assets ? <p className="empty-state">Não há rendimentos. Cadastre um ativo para acompanhar seu rendimento ao longo do tempo.</p>
      : <>
        <div className="performance-summary" role="status"><span>Ganho ou perda no período</span><strong className={Number(data.gain) < 0 ? "feature-error" : "feature-success"}>{currency.format(data.gain)}</strong><span>{data.return_percent === null ? "Sem capital para calcular o percentual" : `${percent.format(data.return_percent)}% sobre o valor inicial e as compras`}</span></div>
        <div className="table-wrap"><table className="holdings-table"><thead><tr><th>ATIVO</th><th>VALOR INICIAL</th><th>VALOR FINAL</th><th>GANHO / PERDA</th></tr></thead><tbody>{data.assets.map(asset => <tr key={asset.stock_name}><td>{asset.stock_name}</td><td>{currency.format(asset.opening_value)}</td><td>{currency.format(asset.closing_value)}</td><td>{currency.format(asset.gain)}</td></tr>)}</tbody></table></div>
      </>}
    <p className="feature-copy">Variação do valor da carteira, descontando compras e somando vendas e proventos registrados. Usa o último fechamento disponível até cada data. Não inclui taxas e impostos.</p>
  </section>;
}
