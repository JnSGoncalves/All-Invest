import type { CSSProperties } from "react";
import type { Portfolio, Position } from "../../services/api";
import Icon from "./Icon";

export type PortfolioFilter = "all" | "none" | number;

interface HoldingsPanelProps {
  positions: Position[];
  portfolios: Portfolio[] | null;
  filter: PortfolioFilter;
  loading: boolean;
  loadError: string | null;
  highlight: string | null;
  movingTicker: string | null;
  onFilterChange: (filter: PortfolioFilter) => void;
  onRetry: () => void;
  onBuy: (ticker: string, portfolioId?: number | null) => void;
  onSell: (position: Position) => void;
  onRemove: (position: Position) => void;
  onMoveRequest: (position: Position) => void;
  onNewPortfolio: () => void;
  onDeletePortfolio: (portfolio: Portfolio) => void;
}

// Paleta categórica validada (ordem fixa). A cor segue o ativo pela ordem da
// primeira compra (ordem da API), então filtros e novas compras não repintam ninguém.
const SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"];
const OTHER_COLOR = "#a3acb8";
const POPULAR = ["PETR4", "VALE3", "ITUB4", "BBAS3", "WEGE3"];
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const quantityFormat = new Intl.NumberFormat("pt-BR");
const percent = new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });

const valueOf = (position: Position) => position.preco_medio * position.stock_quantity;

function matchesFilter(position: Position, filter: PortfolioFilter): boolean {
  if (filter === "all") return true;
  if (filter === "none") return position.portfolio_id === null;
  return position.portfolio_id === filter;
}

export default function HoldingsPanel(props: HoldingsPanelProps) {
  const { positions, portfolios, filter, loading, loadError, highlight, movingTicker } = props;
  const hasPortfolios = Boolean(portfolios && portfolios.length > 0);
  const ranked = [...positions].sort((a, b) => valueOf(b) - valueOf(a));
  const colorByTicker = new Map(positions.slice(0, SERIES_COLORS.length).map((position, index) => [position.stock_name, SERIES_COLORS[index]]));
  const visible = ranked.filter((position) => matchesFilter(position, filter));
  const visibleTotal = visible.reduce((sum, position) => sum + valueOf(position), 0);
  const unassigned = positions.filter((position) => position.portfolio_id === null).length;
  const activePortfolio = typeof filter === "number" ? portfolios?.find((portfolio) => portfolio.portfolio_id === filter) : undefined;

  const segments = visible.filter((position) => colorByTicker.has(position.stock_name)).map((position) => ({
    key: position.stock_name,
    label: position.stock_name,
    value: valueOf(position),
    color: colorByTicker.get(position.stock_name) as string,
  }));
  const otherValue = visible.filter((position) => !colorByTicker.has(position.stock_name)).reduce((sum, position) => sum + valueOf(position), 0);
  if (otherValue > 0) segments.push({ key: "__outros", label: "Outros", value: otherValue, color: OTHER_COLOR });

  const chips: Array<{ key: string; label: string; count: number; value: PortfolioFilter }> = [
    { key: "all", label: "Todos", count: positions.length, value: "all" },
    ...(portfolios ?? []).map((portfolio) => ({
      key: `p${portfolio.portfolio_id}`,
      label: portfolio.portfolio_name,
      count: positions.filter((position) => position.portfolio_id === portfolio.portfolio_id).length,
      value: portfolio.portfolio_id as PortfolioFilter,
    })),
    ...(hasPortfolios && unassigned > 0 ? [{ key: "none", label: "Sem carteira", count: unassigned, value: "none" as PortfolioFilter }] : []),
  ];

  return (
    <article className="panel holdings-panel" id="carteira" aria-labelledby="holdings-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">ACOMPANHAMENTO</span>
          <h2 id="holdings-title">Minha carteira</h2>
        </div>
        <button type="button" className="ghost-button" onClick={() => props.onBuy("")}>
          <Icon name="plus" size={16} /> Registrar compra
        </button>
      </div>

      {portfolios && (
        <div className="filter-row">
          <div className="chip-group" role="tablist" aria-label="Filtrar por carteira">
            {chips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                role="tab"
                aria-selected={filter === chip.value}
                className={`chip ${filter === chip.value ? "active" : ""}`}
                onClick={() => props.onFilterChange(chip.value)}
              >
                {chip.value !== "all" && chip.value !== "none" && <Icon name="folder" size={14} />}
                {chip.label}
                <span className="chip-count">{chip.count}</span>
              </button>
            ))}
            <button type="button" className="chip chip-add" onClick={props.onNewPortfolio}>
              <Icon name="plus" size={14} /> Nova carteira
            </button>
          </div>
          {activePortfolio && (
            <button type="button" className="link-button danger" onClick={() => props.onDeletePortfolio(activePortfolio)}>
              <Icon name="trash" size={14} /> Excluir carteira
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div className="skeleton-list" aria-label="Carregando seus investimentos">
          {[0, 1, 2].map((item) => <div key={item} className="skeleton-row"><span /><span /><span /></div>)}
        </div>
      ) : loadError ? (
        <div className="empty-state error">
          <span className="empty-icon"><Icon name="alert" size={22} /></span>
          <strong>Não conseguimos carregar sua carteira</strong>
          <span>{loadError}</span>
          <button type="button" className="ghost-button" onClick={props.onRetry}>Tentar novamente</button>
        </div>
      ) : positions.length === 0 ? (
        <div className="empty-state onboarding">
          <span className="empty-icon"><Icon name="wallet" size={24} /></span>
          <strong>Sua carteira está vazia</strong>
          <span>Registre sua primeira compra no formulário ao lado. Leva menos de um minuto:</span>
          <ol className="onboarding-steps">
            <li><b>1</b> Busque o ativo pelo código ou nome da empresa</li>
            <li><b>2</b> Informe quantidade e preço (ou use a cotação atual)</li>
            <li><b>3</b> <span>Clique em <em>Registrar compra</em></span></li>
          </ol>
          <div className="popular">
            <span>Comece por um ativo popular:</span>
            <div>
              {POPULAR.map((ticker) => <button key={ticker} type="button" className="chip" onClick={() => props.onBuy(ticker)}>{ticker}</button>)}
            </div>
          </div>
        </div>
      ) : visible.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon"><Icon name="folder" size={22} /></span>
          <strong>{activePortfolio ? `Nenhum ativo em “${activePortfolio.portfolio_name}”` : "Nenhum ativo sem carteira"}</strong>
          <span>Registre uma compra escolhendo esta carteira, ou mova um ativo clicando na etiqueta de carteira dele em “Todos os ativos”.</span>
          {activePortfolio && (
            <button type="button" className="ghost-button" onClick={() => props.onBuy("", activePortfolio.portfolio_id)}>
              <Icon name="plus" size={16} /> Registrar compra nesta carteira
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="allocation">
            <div className="allocation-head">
              <span>Distribuição por ativo</span>
              <strong>{currency.format(visibleTotal)}</strong>
            </div>
            <div className="allocation-bar" role="img" aria-label={`Distribuição: ${segments.map((segment) => `${segment.label} ${percent.format(segment.value / visibleTotal)}`).join(", ")}`}>
              {segments.map((segment) => (
                <span
                  key={segment.key}
                  className="allocation-segment"
                  style={{ flexGrow: segment.value, background: segment.color } as CSSProperties}
                >
                  <span className="allocation-tip" role="tooltip">
                    <b>{segment.label}</b> {currency.format(segment.value)} · {percent.format(segment.value / visibleTotal)}
                  </span>
                </span>
              ))}
            </div>
            <ul className="allocation-legend">
              {segments.map((segment) => (
                <li key={segment.key}>
                  <span className="swatch" style={{ background: segment.color }} />
                  {segment.label} <span>{percent.format(segment.value / visibleTotal)}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="table-wrap">
            <table className="holdings-table">
              <thead>
                <tr>
                  <th scope="col">Ativo</th>
                  <th scope="col" className="num">Quantidade</th>
                  <th scope="col" className="num">Preço médio</th>
                  <th scope="col" className="num">Valor aplicado</th>
                  <th scope="col" className="actions-head">Ações</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((position) => {
                  const share = visibleTotal > 0 ? valueOf(position) / visibleTotal : 0;
                  const color = colorByTicker.get(position.stock_name) ?? OTHER_COLOR;
                  return (
                    <tr key={position.stock_name} className={highlight === position.stock_name ? "row-flash" : ""}>
                      <td data-label="Ativo">
                        <div className="asset-cell">
                          <span className="asset-badge">{position.stock_name.slice(0, 2)}</span>
                          <span>
                            <span className="asset-title">
                              <strong>{position.stock_name}</strong>
                              {hasPortfolios && (
                                <button
                                  type="button"
                                  className={`pf-tag ${position.portfolio_id === null ? "empty" : ""}`}
                                  onClick={() => props.onMoveRequest(position)}
                                  disabled={movingTicker === position.stock_name}
                                  title="Mover para outra carteira"
                                >
                                  <Icon name="folder" size={12} />
                                  {position.portfolio_name ?? "Sem carteira"}
                                </button>
                              )}
                            </span>
                            <small title={position.company_name}>{position.company_name}</small>
                          </span>
                        </div>
                      </td>
                      <td data-label="Quantidade" className="num">{quantityFormat.format(position.stock_quantity)}</td>
                      <td data-label="Preço médio" className="num">{currency.format(position.preco_medio)}</td>
                      <td data-label="Valor aplicado" className="num">
                        <span className="value-cell">{currency.format(valueOf(position))}</span>
                        <span className="share"><span className="swatch" style={{ background: color }} />{percent.format(share)}</span>
                      </td>
                      <td className="row-actions-cell">
                        <div className="row-actions">
                          <button type="button" className="action-button buy" onClick={() => props.onBuy(position.stock_name)} title={`Comprar mais ${position.stock_name}`} aria-label={`Comprar mais ${position.stock_name}`}>
                            <Icon name="plus" size={16} /><span>Comprar</span>
                          </button>
                          <button type="button" className="action-button sell" onClick={() => props.onSell(position)} title={`Vender ${position.stock_name}`} aria-label={`Vender ${position.stock_name}`}>
                            <Icon name="minus" size={16} /><span>Vender</span>
                          </button>
                          <button type="button" className="icon-button remove-button" onClick={() => props.onRemove(position)} aria-label={`Remover ${position.stock_name} e seu histórico`} title={`Remover ${position.stock_name}`}>
                            <Icon name="trash" size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="panel-footer">
        <span><Icon name="info" size={14} /> Valores calculados pelo preço médio das suas operações.</span>
      </div>
    </article>
  );
}
