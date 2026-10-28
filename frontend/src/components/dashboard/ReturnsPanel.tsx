import { useEffect, useState } from "react";
import { getReturns, type AssetReturn, type ReturnPeriod, type Returns } from "../../services/api";
import Icon from "./Icon";
import { parseDay } from "./dates";
import ReturnsChart from "./ReturnsChart";

const PERIODS: Array<{ value: ReturnPeriod; label: string; phrase: string }> = [
  { value: "1w", label: "7 dias", phrase: "nos últimos 7 dias" },
  { value: "1mo", label: "30 dias", phrase: "nos últimos 30 dias" },
  { value: "3mo", label: "90 dias", phrase: "nos últimos 90 dias" },
  { value: "max", label: "Desde a compra", phrase: "desde a primeira compra" },
];
const PERIOD_KEY = "allinvest.returns_period";

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const signedCurrency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", signDisplay: "exceptZero" });
const signedPercent = new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 2, signDisplay: "exceptZero" });
const quantityFormat = new Intl.NumberFormat("pt-BR");
const dayMonth = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const fullDate = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" });

const tone = (value: number) => (value > 0 ? "gain" : value < 0 ? "loss" : "flat");
const errorMessage = (reason: unknown) => reason instanceof Error ? reason.message : "Confira sua conexão e tente novamente.";

function savedPeriod(): ReturnPeriod {
  try {
    const stored = localStorage.getItem(PERIOD_KEY);
    return PERIODS.some((period) => period.value === stored) ? stored as ReturnPeriod : "1mo";
  } catch {
    return "1mo";
  }
}

function RateBadge({ gain, rate }: { gain: number; rate: number | null }) {
  const kind = tone(gain);
  return (
    <span className={`rate-badge ${kind}`}>
      {kind !== "flat" && <Icon name={kind === "gain" ? "up" : "down"} size={13} />}
      {rate === null ? (kind === "gain" ? "Ganho" : kind === "loss" ? "Perda" : "Estável") : signedPercent.format(rate)}
    </span>
  );
}

function GainBar({ gain, scale }: { gain: number; scale: number }) {
  const share = scale > 0 ? Math.min(Math.abs(gain) / scale, 1) : 0;
  return (
    <span className="gain-bar" aria-hidden="true">
      <span className={`gain-bar-fill ${tone(gain)}`} style={{ width: `${share * 50}%` }} />
    </span>
  );
}

function movementLabel(asset: AssetReturn) {
  const parts = [];
  if (asset.bought > 0) parts.push(`compras de ${currency.format(asset.bought)}`);
  if (asset.sold > 0) parts.push(`vendas de ${currency.format(asset.sold)}`);
  return parts;
}

interface ReturnsPanelProps {
  refreshKey: number;
  onBuy: () => void;
}

export default function ReturnsPanel({ refreshKey, onBuy }: ReturnsPanelProps) {
  const [period, setPeriod] = useState<ReturnPeriod>(savedPeriod);
  const [data, setData] = useState<Returns | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  // Chave da última resposta recebida: diferente da atual = consulta em andamento.
  const [settledKey, setSettledKey] = useState<string | null>(null);
  const requestKey = `${period}:${refreshKey}:${retry}`;
  const fetching = settledKey !== requestKey;

  useEffect(() => {
    const controller = new AbortController();
    getReturns(period, controller.signal)
      .then((result) => { setData(result); setError(null); })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(reason));
      })
      .finally(() => { if (!controller.signal.aborted) setSettledKey(requestKey); });
    return () => controller.abort();
  }, [period, requestKey]);

  function choose(next: ReturnPeriod) {
    setPeriod(next);
    try { localStorage.setItem(PERIOD_KEY, next); } catch { /* preferência opcional */ }
  }

  // Enquanto recarrega, mantém o conteúdo anterior esmaecido (sem pular o layout);
  // os rótulos descrevem o período dos dados exibidos, não o recém-escolhido.
  const view = data;
  const shownPeriod = view?.period ?? period;
  const meta = PERIODS.find((item) => item.value === shownPeriod) ?? PERIODS[1];
  const isMax = shownPeriod === "max";
  const refreshing = fetching && view !== null;
  const scale = Math.max(0, ...(view?.assets ?? []).map((asset) => Math.abs(asset.gain)));

  let body;
  if (!view && fetching) {
    body = (
      <div className="returns-skeleton" aria-label="Calculando seus rendimentos">
        <span className="sk-hero" /><span className="sk-chart" /><span className="sk-line" /><span className="sk-line" />
      </div>
    );
  } else if (error && !view) {
    body = (
      <div className="empty-state error">
        <span className="empty-icon"><Icon name="alert" size={22} /></span>
        <strong>Não conseguimos calcular seus rendimentos</strong>
        <span>{error}</span>
        <button type="button" className="ghost-button" onClick={() => setRetry((count) => count + 1)}>Tentar novamente</button>
      </div>
    );
  } else if (view && !view.has_assets) {
    body = (
      <div className="empty-state onboarding">
        <span className="empty-icon"><Icon name="trend" size={24} /></span>
        <strong>Você ainda não tem ativos para acompanhar</strong>
        <span>Assim que você registrar sua primeira compra, mostramos aqui quanto seus investimentos renderam em cada período, com ganho ou perda por ativo.</span>
        <button type="button" className="ghost-button" onClick={onBuy}><Icon name="plus" size={16} /> Registrar primeira compra</button>
      </div>
    );
  } else if (view && view.assets.length === 0 && view.unavailable.length > 0) {
    body = (
      <div className="empty-state error">
        <span className="empty-icon"><Icon name="alert" size={22} /></span>
        <strong>Cotações indisponíveis no momento</strong>
        <span>Não conseguimos buscar o histórico de {view.unavailable.join(", ")}. Tente novamente em alguns minutos.</span>
        <button type="button" className="ghost-button" onClick={() => setRetry((count) => count + 1)}>Tentar novamente</button>
      </div>
    );
  } else if (view && view.assets.length === 0) {
    body = (
      <div className="empty-state">
        <span className="empty-icon"><Icon name="info" size={22} /></span>
        <strong>Nenhum ativo em carteira {meta.phrase}</strong>
        <span>Suas posições foram encerradas antes desse período. Veja o resultado completo desde a primeira compra.</span>
        <button type="button" className="ghost-button" onClick={() => choose("max")}>Ver desde a compra</button>
      </div>
    );
  } else if (view) {
    const kind = tone(view.gain);
    const range = view.start_date && view.end_date
      ? `${(isMax ? fullDate : dayMonth).format(parseDay(view.start_date))} a ${fullDate.format(parseDay(view.end_date))}`
      : null;
    const stats = isMax
      ? [
          { label: "Total comprado", value: currency.format(view.bought) },
          { label: "Total vendido", value: currency.format(view.sold) },
          { label: "Valor atual", value: currency.format(view.end_value) },
        ]
      : [
          { label: "Valor no início", value: currency.format(view.start_value) },
          { label: "Compras no período", value: currency.format(view.bought) },
          { label: "Vendas no período", value: currency.format(view.sold) },
          { label: "Valor atual", value: currency.format(view.end_value) },
        ];

    body = (
      <>
        <div className="returns-overview">
          <div className={`returns-hero ${kind}`}>
            <span className="returns-hero-label">{kind === "loss" ? "Perda" : "Rendimento"} {meta.phrase}</span>
            <div className="returns-hero-value">
              <strong>{signedCurrency.format(view.gain)}</strong>
              <RateBadge gain={view.gain} rate={view.gain_rate} />
            </div>
            {range && <span className="returns-hero-range"><Icon name="chart" size={14} /> {range}</span>}
          </div>
          <dl className="returns-stats">
            {stats.map((stat) => (
              <div key={stat.label}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>
            ))}
          </dl>
        </div>

        {view.unavailable.length > 0 && (
          <p className="returns-warning" role="note">
            <Icon name="alert" size={15} />
            <span>Sem cotação para <strong>{view.unavailable.join(", ")}</strong> agora. {view.unavailable.length === 1 ? "Esse ativo ficou" : "Esses ativos ficaram"} fora dos totais.</span>
          </p>
        )}

        {!isMax && view.series.length >= 2 && (
          <figure className="returns-figure">
            <figcaption>
              <span>Ganho acumulado no período</span>
              <small>Passe o mouse ou use as setas para ver cada pregão</small>
            </figcaption>
            <ReturnsChart points={view.series} />
          </figure>
        )}

        <div className="table-wrap">
          <table className="holdings-table returns-table">
            <caption className="sr-only">Resultado por ativo {meta.phrase}</caption>
            <thead>
              <tr>
                <th scope="col">Ativo</th>
                <th scope="col" className="num">Quantidade</th>
                <th scope="col" className="num">{isMax ? "Cotação atual" : "Cotação"}</th>
                <th scope="col" className="num">Valor atual</th>
                <th scope="col" className="num">Resultado</th>
              </tr>
            </thead>
            <tbody>
              {view.assets.map((asset) => {
                const movements = movementLabel(asset);
                const closed = asset.end_quantity === 0;
                return (
                  <tr key={asset.stock_name}>
                    <td data-label="Ativo">
                      <div className="asset-cell">
                        <span className="asset-badge">{asset.stock_name.slice(0, 2)}</span>
                        <span>
                          <span className="asset-title">
                            <strong>{asset.stock_name}</strong>
                            {closed && <span className="closed-tag">Encerrada</span>}
                          </span>
                          <small title={asset.company_name}>{asset.company_name}</small>
                        </span>
                      </div>
                    </td>
                    <td data-label="Quantidade" className="num">
                      <span>{quantityFormat.format(asset.end_quantity)}</span>
                      {!isMax && asset.start_quantity !== asset.end_quantity && (
                        <span className="cell-note">
                          {asset.start_quantity === 0 ? "comprado no período" : `antes ${quantityFormat.format(asset.start_quantity)}`}
                        </span>
                      )}
                    </td>
                    <td data-label={isMax ? "Cotação atual" : "Cotação"} className="num">
                      {!isMax && asset.start_price !== null ? (
                        <span className="price-move">
                          <span>{currency.format(asset.start_price)}</span>
                          <Icon name="arrow" size={13} />
                          <span>{currency.format(asset.end_price)}</span>
                        </span>
                      ) : (
                        <span>{currency.format(asset.end_price)}</span>
                      )}
                      {movements.map((movement) => <span key={movement} className="cell-note">{movement}</span>)}
                    </td>
                    <td data-label="Valor atual" className="num"><span className="value-cell">{currency.format(asset.end_value)}</span></td>
                    <td data-label="Resultado" className="num">
                      <span className={`result-value ${tone(asset.gain)}`}>{signedCurrency.format(asset.gain)}</span>
                      <span className="result-meta">
                        <GainBar gain={asset.gain} scale={scale} />
                        <RateBadge gain={asset.gain} rate={asset.gain_rate} />
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </>
    );
  }

  return (
    <section className="panel returns-panel" id="rendimentos" aria-labelledby="returns-title" aria-busy={fetching}>
      <div className="panel-heading returns-heading">
        <div>
          <span className="eyebrow">DESEMPENHO</span>
          <h2 id="returns-title">Rendimentos</h2>
        </div>
        {view?.has_assets !== false && (
          <div className="period-switch" role="radiogroup" aria-label="Período do rendimento">
            {PERIODS.map((item) => (
              <button
                key={item.value}
                type="button"
                role="radio"
                aria-checked={period === item.value}
                className={period === item.value ? "selected" : ""}
                onClick={() => choose(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && view && (
        <p className="returns-warning error" role="alert">
          <Icon name="alert" size={15} />
          <span>Não foi possível atualizar: {error}</span>
          <button type="button" className="link-button" onClick={() => setRetry((count) => count + 1)}>Tentar de novo</button>
        </p>
      )}

      <div className={`returns-body ${refreshing ? "is-refreshing" : ""}`}>{body}</div>

      {view && view.assets.length > 0 && (
        <div className="panel-footer">
          <span>
            <Icon name="info" size={14} />
            {isMax
              ? "Resultado = valor atual + vendas − compras. Cotações de fechamento da B3 (brapi.dev)."
              : "Compras e vendas no período não contam como rendimento. Cotações de fechamento da B3 (brapi.dev)."}
          </span>
        </div>
      )}
    </section>
  );
}
