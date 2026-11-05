import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ApiError,
  createTrade,
  validateTicker,
  type Broker,
  type Portfolio,
  type Position,
  type TickerSuggestion,
  type Trade,
  type TradeSide,
} from "../../services/api";
import type { Toast } from "./Toasts";
import Icon from "./Icon";
import TickerField, { type TickerStatus } from "./TickerField";

export interface TradeDraft {
  nonce: number;
  side: TradeSide;
  ticker: string;
  focus: "ticker" | "quantity" | null;
  portfolioId: number | null;
}

interface TradeFormProps {
  draft: TradeDraft;
  positions: Position[];
  portfolios: Portfolio[] | null;
  brokers: Broker[] | null;
  onSaved: (trade: Trade, portfolioId: number | null) => Promise<void>;
  onNotify: (toast: Omit<Toast, "id">) => void;
  onNewPortfolio: (onCreated: (portfolio: Portfolio) => void) => void;
  onNewBroker: (onCreated: (broker: Broker) => void) => void;
}

interface FormResult {
  kind: "success" | "error";
  title: string;
  message: string;
}

type FieldErrors = Partial<Record<"quantity" | "price" | "date" | "broker", string>>;

const BROKER_KEY = "allinvest.last_broker";
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const quantityFormat = new Intl.NumberFormat("pt-BR");

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function savedBroker(): string {
  try {
    return localStorage.getItem(BROKER_KEY) ?? "";
  } catch {
    return "";
  }
}

// Aceita "37,15", "37.15" e "1.234,56".
function parseDecimal(raw: string): number {
  const value = raw.trim();
  if (!value) return Number.NaN;
  const normalized = value.includes(",") ? value.replace(/\./g, "").replace(",", ".") : value;
  return Number(normalized);
}

// Datas passadas recebem o horário atual para não colidir com outra operação do mesmo dia.
function tradeDateFor(date: string, today: string): string | undefined {
  if (date === today) return undefined;
  const [year, month, day] = date.split("-").map(Number);
  const now = new Date();
  return new Date(year, month - 1, day, now.getHours(), now.getMinutes(), now.getSeconds(), now.getMilliseconds()).toISOString();
}

async function remoteStatus(value: string): Promise<TickerStatus> {
  try {
    const info = await validateTicker(value);
    return { state: "valid", ticker: value, company: info.company_name };
  } catch (reason) {
    if (reason instanceof ApiError && reason.status === 404) {
      return { state: "invalid", ticker: value, message: `${reason.message} Confira o código, ex.: PETR4 ou VALE3.` };
    }
    return { state: "unavailable", ticker: value };
  }
}

function initialStatus(draft: TradeDraft, positions: Position[]): TickerStatus {
  if (!draft.ticker) return { state: "idle" };
  const owned = positions.find((position) => position.stock_name === draft.ticker);
  if (owned) return { state: "valid", ticker: owned.stock_name, company: owned.company_name };
  return { state: "checking", ticker: draft.ticker };
}

export default function TradeForm({ draft, positions, portfolios, brokers, onSaved, onNotify, onNewPortfolio, onNewBroker }: TradeFormProps) {
  const [today] = useState(todayIso);
  const [side, setSide] = useState<TradeSide>(draft.side);
  const [ticker, setTicker] = useState(draft.ticker);
  const [tickerStatus, setTickerStatus] = useState<TickerStatus>(() => initialStatus(draft, positions));
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [useQuote, setUseQuote] = useState(false);
  const [date, setDate] = useState(today);
  const [broker, setBroker] = useState(savedBroker);
  const [portfolioId, setPortfolioId] = useState(() => {
    const owned = positions.find((position) => position.stock_name === draft.ticker);
    return String(owned?.portfolio_id ?? draft.portfolioId ?? "");
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [result, setResult] = useState<FormResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const tickerRef = useRef<HTMLInputElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);
  const priceRef = useRef<HTMLInputElement>(null);
  const latestTicker = useRef(draft.ticker);

  const normalizedTicker = ticker.trim().toUpperCase();
  const owned = positions.find((position) => position.stock_name === normalizedTicker);
  const quantityValue = Number(quantity);
  const priceValue = parseDecimal(price);
  const total = quantityValue > 0 && priceValue > 0 ? quantityValue * priceValue : null;
  const isSell = side === "SELL";
  // A corretora salva pode ter saído do catálogo; nesse caso usa a primeira da lista.
  const brokerId = brokers?.some((item) => String(item.broker_id) === broker)
    ? broker
    : String(brokers?.[0]?.broker_id ?? "");

  function checkRemote(value: string) {
    remoteStatus(value).then((status) => {
      if (latestTicker.current === value) setTickerStatus(status);
    });
  }

  useEffect(() => {
    if (draft.focus === "quantity") quantityRef.current?.focus();
    else if (draft.focus === "ticker") tickerRef.current?.focus();
    if (draft.ticker && !positions.some((position) => position.stock_name === draft.ticker)) {
      remoteStatus(draft.ticker).then((status) => {
        if (latestTicker.current === draft.ticker) setTickerStatus(status);
      });
    }
    // Executa apenas na montagem: o rascunho muda junto com a key do formulário.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function statusForSell(value: string): TickerStatus {
    const position = positions.find((item) => item.stock_name === value);
    return position
      ? { state: "valid", ticker: value, company: position.company_name }
      : { state: "invalid", ticker: value, message: `Você não possui ${value} na carteira para vender.` };
  }

  function commitTicker() {
    const value = normalizedTicker;
    if (!value) {
      setTickerStatus({ state: "idle" });
      return;
    }
    if (tickerStatus.state !== "idle" && tickerStatus.ticker === value) return;
    if (isSell) {
      setTickerStatus(statusForSell(value));
      return;
    }
    if (owned) {
      setTickerStatus({ state: "valid", ticker: value, company: owned.company_name });
      return;
    }
    setTickerStatus({ state: "checking", ticker: value });
    checkRemote(value);
  }

  function handlePick(suggestion: TickerSuggestion) {
    latestTicker.current = suggestion.stock_name;
    setTicker(suggestion.stock_name);
    setTickerStatus({ state: "valid", ticker: suggestion.stock_name, company: suggestion.company_name });
    const position = positions.find((item) => item.stock_name === suggestion.stock_name);
    if (position?.portfolio_id) setPortfolioId(String(position.portfolio_id));
    quantityRef.current?.focus();
  }

  function changeSide(next: TradeSide) {
    setSide(next);
    setFieldErrors({});
    setResult(null);
    if (!normalizedTicker) return;
    if (next === "SELL") setTickerStatus(statusForSell(normalizedTicker));
    else if (owned) setTickerStatus({ state: "valid", ticker: normalizedTicker, company: owned.company_name });
    else {
      setTickerStatus({ state: "checking", ticker: normalizedTicker });
      checkRemote(normalizedTicker);
    }
  }

  function validate(): FieldErrors & { ticker?: string } {
    const errors: FieldErrors & { ticker?: string } = {};
    if (!normalizedTicker) errors.ticker = "Informe o código do ativo.";
    else if (tickerStatus.state === "invalid" && tickerStatus.ticker === normalizedTicker) errors.ticker = tickerStatus.message;
    if (!Number.isInteger(quantityValue) || quantityValue <= 0) errors.quantity = "Informe uma quantidade inteira maior que zero.";
    else if (isSell && owned && quantityValue > owned.stock_quantity) {
      errors.quantity = `Você possui ${quantityFormat.format(owned.stock_quantity)} ações de ${owned.stock_name}.`;
    }
    if (!useQuote && !(priceValue > 0)) errors.price = "Informe o preço por ação.";
    if (!date || date > today) errors.date = "Escolha uma data até hoje.";
    if (!brokerId) errors.broker = "Cadastre ou escolha uma corretora.";
    return errors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validate();
    const { ticker: tickerError, ...otherErrors } = errors;
    setFieldErrors(otherErrors);
    if (tickerError) {
      setTickerStatus({ state: "invalid", ticker: normalizedTicker, message: tickerError });
    }
    const firstError = tickerError ?? otherErrors.quantity ?? otherErrors.price ?? otherErrors.date ?? otherErrors.broker;
    if (firstError) {
      setResult({ kind: "error", title: "Revise os campos destacados", message: firstError });
      if (tickerError) tickerRef.current?.focus();
      else if (otherErrors.quantity) quantityRef.current?.focus();
      else if (otherErrors.price) priceRef.current?.focus();
      return;
    }

    setSubmitting(true);
    setResult(null);
    const selectedPortfolio = !isSell && portfolioId ? Number(portfolioId) : null;
    try {
      const trade = await createTrade({
        stock_name: normalizedTicker,
        stock_quantity: quantityValue,
        ...(useQuote ? { auto_cotacao: true } : { stock_price: Math.round(priceValue * 10000) / 10000 }),
        broker_id: Number(brokerId),
        trade_side: side,
        trade_date: tradeDateFor(date, today),
        ...(selectedPortfolio ? { portfolio_id: selectedPortfolio } : {}),
      });
      try { localStorage.setItem(BROKER_KEY, brokerId); } catch { /* preferência opcional */ }

      const verb = trade.trade_side === "BUY" ? "Compra" : "Venda";
      const summary = `${quantityFormat.format(trade.stock_quantity)} ${trade.stock_name} a ${currency.format(trade.stock_price)} · total ${currency.format(trade.stock_quantity * trade.stock_price)}`;
      setResult({ kind: "success", title: `${verb} de ${trade.stock_name} registrada`, message: summary });
      latestTicker.current = "";
      setTicker("");
      setTickerStatus({ state: "idle" });
      setQuantity("");
      setPrice("");
      setDate(today);
      setFieldErrors({});
      await onSaved(trade, selectedPortfolio);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Tente novamente em instantes.";
      const status = reason instanceof ApiError ? reason.status : 0;
      let title = "Não foi possível registrar a operação";
      if (status === 404 && message.toLowerCase().includes("ativo")) {
        title = "Ativo não encontrado na B3";
        setTickerStatus({ state: "invalid", ticker: normalizedTicker, message: `${message} Confira o código, ex.: PETR4 ou VALE3.` });
        tickerRef.current?.focus();
      } else if (status === 422 && message.toLowerCase().includes("saldo")) {
        title = "Saldo insuficiente para a venda";
        setFieldErrors({ quantity: message });
        quantityRef.current?.focus();
      } else if (status === 400 && message.toLowerCase().includes("corretora")) {
        title = "Corretora não encontrada";
        setFieldErrors({ broker: "Escolha outra corretora ou cadastre uma nova." });
      } else if (status === 404 && message.toLowerCase().includes("carteira")) {
        title = "Carteira não encontrada";
      } else if ([429, 502, 503, 504].includes(status)) {
        title = "Não foi possível consultar a B3 agora";
      }
      setResult({ kind: "error", title, message });
      onNotify({ kind: "error", title, message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className={`trade-form ${isSell ? "is-sell" : "is-buy"}`} onSubmit={handleSubmit} noValidate>
      <div className="side-toggle" role="radiogroup" aria-label="Tipo da operação">
        <button type="button" role="radio" aria-checked={!isSell} className={!isSell ? "selected buy" : ""} onClick={() => changeSide("BUY")}>
          <Icon name="plus" size={16} /> Compra
        </button>
        <button type="button" role="radio" aria-checked={isSell} className={isSell ? "selected sell" : ""} onClick={() => changeSide("SELL")}>
          <Icon name="minus" size={16} /> Venda
        </button>
      </div>

      <div className="form-field">
        <label htmlFor="trade-ticker">Ativo</label>
        <TickerField
          id="trade-ticker"
          value={ticker}
          side={side}
          status={tickerStatus}
          positions={positions}
          inputRef={tickerRef}
          onChange={(next) => {
            latestTicker.current = next.trim();
            setTicker(next);
            setTickerStatus({ state: "idle" });
            setResult(null);
          }}
          onPick={handlePick}
          onCommit={commitTicker}
        />
        {owned && (
          <div className="holding-hint">
            <span>Você possui <strong>{quantityFormat.format(owned.stock_quantity)}</strong> ações · preço médio {currency.format(owned.preco_medio)}</span>
            {isSell && <button type="button" onClick={() => { setQuantity(String(owned.stock_quantity)); setFieldErrors((current) => ({ ...current, quantity: undefined })); }}>Vender tudo</button>}
          </div>
        )}
      </div>

      <div className="form-pair">
        <div className={`form-field ${fieldErrors.quantity ? "has-error" : ""}`}>
          <label htmlFor="trade-quantity">Quantidade</label>
          <input
            id="trade-quantity"
            ref={quantityRef}
            type="number"
            inputMode="numeric"
            min="1"
            step="1"
            value={quantity}
            onChange={(event) => { setQuantity(event.target.value); setFieldErrors((current) => ({ ...current, quantity: undefined })); }}
            placeholder="Ex.: 100"
            aria-invalid={Boolean(fieldErrors.quantity)}
            aria-describedby={fieldErrors.quantity ? "trade-quantity-error" : undefined}
          />
          {fieldErrors.quantity && <p className="field-error" id="trade-quantity-error"><Icon name="alert" size={14} /> {fieldErrors.quantity}</p>}
        </div>
        <div className={`form-field ${fieldErrors.price ? "has-error" : ""}`}>
          <label htmlFor="trade-price">Preço por ação</label>
          <div className={`input-shell money ${useQuote ? "disabled" : ""}`}>
            <span className="input-leading">R$</span>
            <input
              id="trade-price"
              ref={priceRef}
              type="text"
              inputMode="decimal"
              value={useQuote ? "" : price}
              onChange={(event) => { setPrice(event.target.value.replace(/[^\d.,]/g, "")); setFieldErrors((current) => ({ ...current, price: undefined })); }}
              placeholder={useQuote ? "Cotação atual" : "0,00"}
              disabled={useQuote}
              aria-invalid={Boolean(fieldErrors.price)}
              aria-describedby={fieldErrors.price ? "trade-price-error" : undefined}
            />
          </div>
          {fieldErrors.price && <p className="field-error" id="trade-price-error"><Icon name="alert" size={14} /> {fieldErrors.price}</p>}
        </div>
      </div>

      <label className="quote-toggle">
        <input type="checkbox" checked={useQuote} onChange={(event) => { setUseQuote(event.target.checked); setFieldErrors((current) => ({ ...current, price: undefined })); }} />
        <span className="switch" aria-hidden="true" />
        <span>Usar a cotação atual da B3 como preço</span>
      </label>

      <div className="form-pair">
        <div className={`form-field ${fieldErrors.date ? "has-error" : ""}`}>
          <label htmlFor="trade-date">Data da operação</label>
          <input id="trade-date" type="date" value={date} max={today} onChange={(event) => { setDate(event.target.value); setFieldErrors((current) => ({ ...current, date: undefined })); }} aria-invalid={Boolean(fieldErrors.date)} />
          {fieldErrors.date && <p className="field-error"><Icon name="alert" size={14} /> {fieldErrors.date}</p>}
        </div>
        <div className={`form-field ${fieldErrors.broker ? "has-error" : ""}`}>
          <div className="label-row">
            <label htmlFor="trade-broker">Corretora</label>
            <button type="button" className="link-button" onClick={() => onNewBroker((created) => { setBroker(String(created.broker_id)); setFieldErrors((current) => ({ ...current, broker: undefined })); })}>
              <Icon name="plus" size={14} /> Nova
            </button>
          </div>
          <select
            id="trade-broker"
            value={brokerId}
            onChange={(event) => { setBroker(event.target.value); setFieldErrors((current) => ({ ...current, broker: undefined })); }}
            disabled={!brokers?.length}
            aria-invalid={Boolean(fieldErrors.broker)}
          >
            {brokers === null && <option value="">Carregando…</option>}
            {brokers?.length === 0 && <option value="">Nenhuma cadastrada</option>}
            {brokers?.map((item) => <option key={item.broker_id} value={item.broker_id}>{item.broker_name}</option>)}
          </select>
          {fieldErrors.broker && <p className="field-error"><Icon name="alert" size={14} /> {fieldErrors.broker}</p>}
        </div>
      </div>

      {portfolios && !isSell && (
        <div className="form-field">
          <div className="label-row">
            <label htmlFor="trade-portfolio">Carteira <span className="optional">(opcional)</span></label>
            <button type="button" className="link-button" onClick={() => onNewPortfolio((created) => setPortfolioId(String(created.portfolio_id)))}>
              <Icon name="plus" size={14} /> Nova carteira
            </button>
          </div>
          <select id="trade-portfolio" value={portfolioId} onChange={(event) => setPortfolioId(event.target.value)}>
            <option value="">Sem carteira</option>
            {portfolios.map((portfolio) => <option key={portfolio.portfolio_id} value={portfolio.portfolio_id}>{portfolio.portfolio_name}</option>)}
          </select>
          {owned?.portfolio_name && String(owned.portfolio_id) !== portfolioId && (
            <p className="field-hint">{owned.stock_name} está em “{owned.portfolio_name}”. Ao registrar, o ativo vai para a carteira escolhida.</p>
          )}
        </div>
      )}

      <div className="trade-total">
        <span>Total da operação</span>
        {useQuote
          ? <strong className="pending">Calculado com a cotação no momento do registro</strong>
          : <strong>{total !== null ? currency.format(total) : "R$ 0,00"}</strong>}
      </div>

      {result && (
        <div className={`form-result ${result.kind}`} role={result.kind === "error" ? "alert" : "status"}>
          <span className="form-result-icon"><Icon name={result.kind === "success" ? "check" : "alert"} size={18} /></span>
          <div>
            <strong>{result.title}</strong>
            <span>{result.message}</span>
          </div>
          <button type="button" onClick={() => setResult(null)} aria-label="Fechar mensagem"><Icon name="close" size={16} /></button>
        </div>
      )}

      <button className="trade-submit" type="submit" disabled={submitting}>
        {submitting ? <><span className="mini-spinner light" /> Validando na B3 e registrando…</> : <>{isSell ? "Registrar venda" : "Registrar compra"} <Icon name="arrow" size={18} /></>}
      </button>
    </form>
  );
}
