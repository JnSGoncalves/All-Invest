import { useEffect, useRef, useState, type KeyboardEvent, type Ref } from "react";
import { autocompleteTickers, type Position, type TickerSuggestion, type TradeSide } from "../../services/api";
import Icon from "./Icon";

export type TickerStatus =
  | { state: "idle" }
  | { state: "checking"; ticker: string }
  | { state: "valid"; ticker: string; company: string }
  | { state: "invalid"; ticker: string; message: string }
  | { state: "unavailable"; ticker: string };

interface TickerFieldProps {
  id: string;
  value: string;
  side: TradeSide;
  status: TickerStatus;
  positions: Position[];
  inputRef?: Ref<HTMLInputElement>;
  onChange: (value: string) => void;
  onPick: (suggestion: TickerSuggestion) => void;
  onCommit: () => void;
}

interface RemoteResult {
  query: string;
  items: TickerSuggestion[];
  failed: boolean;
}

const MIN_QUERY = 2;
const suggestionCache = new Map<string, TickerSuggestion[]>();
const quantityFormat = new Intl.NumberFormat("pt-BR");

function matches(position: Position, query: string): boolean {
  return !query
    || position.stock_name.includes(query)
    || position.company_name.toUpperCase().includes(query);
}

export default function TickerField({ id, value, side, status, positions, inputRef, onChange, onPick, onCommit }: TickerFieldProps) {
  const [remote, setRemote] = useState<RemoteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<number | undefined>(undefined);
  const controllerRef = useRef<AbortController | null>(null);
  // A escolha de uma sugestão já define o ativo; o blur que vem em seguida não deve revalidar o texto antigo.
  const pickedRef = useRef(false);

  useEffect(() => () => {
    window.clearTimeout(debounceRef.current);
    controllerRef.current?.abort();
  }, []);

  const query = value.trim().toUpperCase();
  const owned = positions.filter((position) => matches(position, query));
  const ownedTickers = new Set(owned.map((position) => position.stock_name));
  const remoteItems = side === "BUY" && remote?.query === query
    ? remote.items.filter((item) => !ownedTickers.has(item.stock_name))
    : [];
  const options = [
    ...owned.slice(0, side === "SELL" ? 8 : 3).map((position) => ({ ...position, owned: true })),
    ...remoteItems.map((item) => ({ ...item, owned: false, stock_quantity: 0 })),
  ];
  const searching = side === "BUY" && query.length >= MIN_QUERY && loading;
  const noResults = side === "BUY" && query.length >= MIN_QUERY && !searching && remote?.query === query && !remote.failed && options.length === 0;
  const showHint = side === "BUY" && query.length < MIN_QUERY && options.length === 0;
  const listOpen = open && (options.length > 0 || searching || noResults || showHint || side === "SELL");
  const listId = `${id}-options`;

  function requestSuggestions(nextQuery: string) {
    window.clearTimeout(debounceRef.current);
    controllerRef.current?.abort();
    if (side === "SELL" || nextQuery.length < MIN_QUERY) {
      setLoading(false);
      return;
    }
    const cached = suggestionCache.get(nextQuery);
    if (cached) {
      setRemote({ query: nextQuery, items: cached, failed: false });
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = window.setTimeout(() => {
      const controller = new AbortController();
      controllerRef.current = controller;
      autocompleteTickers(nextQuery, controller.signal)
        .then((items) => {
          suggestionCache.set(nextQuery, items);
          setRemote({ query: nextQuery, items, failed: false });
        })
        .catch(() => {
          if (!controller.signal.aborted) setRemote({ query: nextQuery, items: [], failed: true });
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
  }

  function pick(index: number) {
    const option = options[index];
    if (!option) return;
    pickedRef.current = true;
    onPick({ stock_name: option.stock_name, company_name: option.company_name });
    setOpen(false);
    setActiveIndex(-1);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => Math.min(current + 1, options.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && listOpen && activeIndex >= 0) {
      event.preventDefault();
      pick(activeIndex);
    } else if (event.key === "Escape" && listOpen) {
      event.preventDefault();
      setOpen(false);
    }
  }

  const statusTone = status.state === "valid" ? "valid" : status.state === "invalid" ? "invalid" : "";

  return (
    <div className={`ticker-field ${statusTone}`}>
      <div className="input-shell">
        <span className="input-leading"><Icon name="search" size={17} /></span>
        <input
          id={id}
          ref={inputRef}
          value={value}
          onChange={(event) => {
            const next = event.target.value.toUpperCase();
            onChange(next);
            setOpen(true);
            setActiveIndex(-1);
            requestSuggestions(next.trim());
          }}
          onFocus={() => {
            // Com erro, mantém a mensagem visível até a pessoa voltar a digitar.
            setOpen(status.state !== "invalid");
            if (remote?.query !== query) requestSuggestions(query);
          }}
          onBlur={() => {
            setOpen(false);
            if (pickedRef.current) pickedRef.current = false;
            else onCommit();
          }}
          onKeyDown={handleKeyDown}
          placeholder={side === "SELL" ? "Escolha um ativo da sua carteira" : "Ex.: PETR4 ou Petrobras"}
          autoComplete="off"
          spellCheck={false}
          maxLength={20}
          role="combobox"
          aria-expanded={listOpen}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
          aria-invalid={status.state === "invalid"}
          aria-describedby={`${id}-status`}
        />
        <span className="input-trailing" aria-hidden="true">
          {status.state === "checking" && <span className="mini-spinner" />}
          {status.state === "valid" && <span className="status-badge valid"><Icon name="check" size={14} /></span>}
          {status.state === "invalid" && <span className="status-badge invalid"><Icon name="alert" size={14} /></span>}
        </span>
      </div>

      {listOpen && (
        <ul className="ticker-options" id={listId} role="listbox" aria-label="Sugestões de ativos">
          {options.map((option, index) => (
            <li
              key={option.stock_name}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={index === activeIndex ? "active" : ""}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => pick(index)}
              onMouseEnter={() => setActiveIndex(index)}
            >
              <span className="option-badge">{option.stock_name.slice(0, 2)}</span>
              <span className="option-copy">
                <strong>{option.stock_name}</strong>
                <small>{option.company_name}</small>
              </span>
              {option.owned && <span className="option-tag">Você tem {quantityFormat.format(option.stock_quantity)}</span>}
            </li>
          ))}
          {searching && <li className="option-note" role="presentation"><span className="mini-spinner" /> Buscando ativos na B3…</li>}
          {noResults && <li className="option-note warn" role="presentation"><Icon name="alert" size={16} /> Nenhum ativo encontrado para “{query}”.</li>}
          {showHint && <li className="option-note" role="presentation">Digite ao menos 2 caracteres para buscar.</li>}
          {side === "SELL" && options.length === 0 && (
            <li className="option-note warn" role="presentation">
              <Icon name="alert" size={16} /> {positions.length === 0 ? "Você ainda não tem ativos para vender." : `Nenhum ativo da sua carteira corresponde a “${query}”.`}
            </li>
          )}
        </ul>
      )}

      <p className={`field-status ${statusTone}`} id={`${id}-status`} aria-live="polite">
        {status.state === "idle" && (side === "SELL" ? "Somente ativos da sua carteira podem ser vendidos." : "Digite o código do ativo ou o nome da empresa.")}
        {status.state === "checking" && "Verificando o ativo na B3…"}
        {status.state === "valid" && <><Icon name="check" size={15} /> <span><strong>{status.company}</strong></span></>}
        {status.state === "invalid" && <><Icon name="alert" size={15} /> <span>{status.message}</span></>}
        {status.state === "unavailable" && "Não foi possível verificar agora. O ativo será validado ao registrar."}
      </p>
    </div>
  );
}
