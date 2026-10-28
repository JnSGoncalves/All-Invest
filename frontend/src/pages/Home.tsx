import { useCallback, useEffect, useRef, useState } from "react";
import {
  assignPositionPortfolio,
  deletePortfolio,
  getBrokers,
  getPortfolios,
  getPositions,
  removePosition,
  type Broker,
  type Portfolio,
  type Position,
  type Trade,
  type TradeSide,
} from "../services/api";
import { useAuth } from "../contexts/auth-context";
import BrokerDialog from "../components/dashboard/BrokerDialog";
import HoldingsPanel, { type PortfolioFilter } from "../components/dashboard/HoldingsPanel";
import Icon from "../components/dashboard/Icon";
import Modal from "../components/dashboard/Modal";
import PortfolioDialog from "../components/dashboard/PortfolioDialog";
import ReturnsPanel from "../components/dashboard/ReturnsPanel";
import ToastViewport, { type Toast } from "../components/dashboard/Toasts";
import TradeForm, { type TradeDraft } from "../components/dashboard/TradeForm";
import "./Home.css";

type Dialog =
  | { type: "remove"; position: Position }
  | { type: "move"; position: Position }
  | { type: "new-portfolio"; selectAfter: boolean }
  | { type: "new-broker" }
  | { type: "delete-portfolio"; portfolio: Portfolio };

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const quantityFormat = new Intl.NumberFormat("pt-BR");
const percent = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 });

const errorMessage = (reason: unknown, fallback: string) => reason instanceof Error ? reason.message : fallback;

function inFilter(position: Position, filter: PortfolioFilter): boolean {
  if (filter === "all") return true;
  if (filter === "none") return position.portfolio_id === null;
  return position.portfolio_id === filter;
}

export default function Home() {
  const { user, logout } = useAuth();
  const [positions, setPositions] = useState<Position[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[] | null>(null);
  const [brokers, setBrokers] = useState<Broker[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<PortfolioFilter>("all");
  const [draft, setDraft] = useState<TradeDraft>({ nonce: 0, side: "BUY", ticker: "", focus: null, portfolioId: null });
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [movingTicker, setMovingTicker] = useState<string | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [dialogBusy, setDialogBusy] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [section, setSection] = useState("visao-geral");
  // Incrementado a cada operação salva ou removida para recalcular os rendimentos.
  const [returnsVersion, setReturnsVersion] = useState(0);
  const [todayLabel] = useState(() => new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" }).format(new Date()).replace(/^./, (letter) => letter.toUpperCase()));
  const toastId = useRef(0);
  const highlightTimer = useRef<number | undefined>(undefined);
  const portfolioCreated = useRef<((portfolio: Portfolio) => void) | null>(null);
  const brokerCreated = useRef<((broker: Broker) => void) | null>(null);
  const tradePanelRef = useRef<HTMLElement>(null);

  const notify = useCallback((toast: Omit<Toast, "id">) => {
    toastId.current += 1;
    const id = toastId.current;
    setToasts((current) => [...current.slice(-2), { ...toast, id }]);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts((current) => current.filter((toast) => toast.id !== id)), []);

  const loadDashboard = useCallback(() => (
    Promise.allSettled([getPositions(), getPortfolios(), getBrokers()]).then(([positionsResult, portfoliosResult, brokersResult]) => {
      if (positionsResult.status === "fulfilled") {
        setPositions(positionsResult.value);
        setLoadError(null);
      } else {
        setLoadError(errorMessage(positionsResult.reason, "Confira sua conexão e tente novamente."));
      }
      // Sem a migração de carteiras, a tela segue funcionando sem esse recurso.
      setPortfolios(portfoliosResult.status === "fulfilled" ? portfoliosResult.value : null);
      if (brokersResult.status === "fulfilled") setBrokers(brokersResult.value);
      else notify({ kind: "error", title: "Não foi possível carregar as corretoras", message: errorMessage(brokersResult.reason, "Recarregue a página.") });
      setLoading(false);
    })
  ), [notify]);

  useEffect(() => {
    void loadDashboard();
    return () => window.clearTimeout(highlightTimer.current);
  }, [loadDashboard]);

  async function refreshPositions(): Promise<Position[] | null> {
    try {
      const fresh = await getPositions();
      setPositions(fresh);
      setLoadError(null);
      return fresh;
    } catch (reason) {
      notify({ kind: "error", title: "Não foi possível atualizar a carteira", message: errorMessage(reason, "Recarregue a página.") });
      return null;
    }
  }

  function flash(ticker: string) {
    window.clearTimeout(highlightTimer.current);
    setHighlight(ticker);
    highlightTimer.current = window.setTimeout(() => setHighlight(null), 2600);
  }

  function openTrade(side: TradeSide, ticker = "", portfolioId: number | null = null) {
    setDraft((current) => ({ nonce: current.nonce + 1, side, ticker, focus: ticker ? "quantity" : "ticker", portfolioId }));
    setSection("registrar");
    const panel = tradePanelRef.current;
    if (panel) {
      const { top, bottom } = panel.getBoundingClientRect();
      if (top < 70 || bottom > window.innerHeight) panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function focusTradeForm() {
    openTrade("BUY", "", typeof filter === "number" ? filter : null);
  }

  async function handleSaved(trade: Trade) {
    setReturnsVersion((version) => version + 1);
    const fresh = await refreshPositions();
    const position = fresh?.find((item) => item.stock_name === trade.stock_name);
    const verb = trade.trade_side === "BUY" ? "Compra" : "Venda";
    const summary = `${quantityFormat.format(trade.stock_quantity)} ${trade.stock_name} a ${currency.format(trade.stock_price)} (${trade.broker_name}).`;
    notify({
      kind: "success",
      title: `${verb} de ${trade.stock_name} registrada`,
      message: trade.trade_side === "SELL" && !position ? `${summary} Você zerou sua posição em ${trade.stock_name}.` : summary,
    });
    if (position) {
      if (!inFilter(position, filter)) setFilter("all");
      flash(position.stock_name);
    }
  }

  async function confirmRemove(position: Position) {
    setDialogBusy(true);
    try {
      await removePosition(position.stock_name);
      setDialog(null);
      setReturnsVersion((version) => version + 1);
      notify({ kind: "success", title: `${position.stock_name} removido da carteira`, message: "Todas as compras e vendas desse ativo foram apagadas." });
      await refreshPositions();
    } catch (reason) {
      notify({ kind: "error", title: `Não foi possível remover ${position.stock_name}`, message: errorMessage(reason, "Tente novamente.") });
    } finally {
      setDialogBusy(false);
    }
  }

  async function handleMove(position: Position, target: Portfolio) {
    setDialog(null);
    setMovingTicker(position.stock_name);
    try {
      await assignPositionPortfolio(position.stock_name, target.portfolio_id);
      await refreshPositions();
      notify({ kind: "success", title: `${position.stock_name} movido`, message: `Agora o ativo está na carteira “${target.portfolio_name}”.` });
      flash(position.stock_name);
    } catch (reason) {
      notify({ kind: "error", title: `Não foi possível mover ${position.stock_name}`, message: errorMessage(reason, "Tente novamente.") });
    } finally {
      setMovingTicker(null);
    }
  }

  function openNewPortfolio(onCreated?: (portfolio: Portfolio) => void) {
    portfolioCreated.current = onCreated ?? null;
    setDialog({ type: "new-portfolio", selectAfter: !onCreated });
  }

  function handlePortfolioCreated(portfolio: Portfolio, selectAfter: boolean) {
    setPortfolios((current) => [...(current ?? []), portfolio]);
    setDialog(null);
    notify({ kind: "success", title: `Carteira “${portfolio.portfolio_name}” criada`, message: "Escolha esta carteira ao registrar uma compra ou mova ativos para ela." });
    portfolioCreated.current?.(portfolio);
    portfolioCreated.current = null;
    if (selectAfter) setFilter(portfolio.portfolio_id);
  }

  function openNewBroker(onCreated: (broker: Broker) => void) {
    brokerCreated.current = onCreated;
    setDialog({ type: "new-broker" });
  }

  function handleBrokerCreated(broker: Broker) {
    setBrokers((current) => [...(current ?? []), broker].sort((a, b) => a.broker_name.localeCompare(b.broker_name, "pt-BR")));
    setDialog(null);
    notify({ kind: "success", title: `Corretora “${broker.broker_name}” cadastrada`, message: "Ela já está selecionada no formulário de operação." });
    brokerCreated.current?.(broker);
    brokerCreated.current = null;
  }

  async function confirmDeletePortfolio(portfolio: Portfolio) {
    setDialogBusy(true);
    try {
      await deletePortfolio(portfolio.portfolio_id);
      setDialog(null);
      setFilter("all");
      setPortfolios((current) => current?.filter((item) => item.portfolio_id !== portfolio.portfolio_id) ?? null);
      notify({ kind: "success", title: `Carteira “${portfolio.portfolio_name}” excluída`, message: "Os ativos dela continuam na sua conta, sem carteira." });
      await refreshPositions();
    } catch (reason) {
      notify({ kind: "error", title: "Não foi possível excluir a carteira", message: errorMessage(reason, "Tente novamente.") });
    } finally {
      setDialogBusy(false);
    }
  }

  async function handleLogout() {
    setSigningOut(true);
    try {
      await logout();
    } catch {
      notify({ kind: "error", title: "Não foi possível sair", message: "A sessão não foi encerrada no servidor. Tente novamente." });
      setSigningOut(false);
    }
  }

  if (!user) return null;

  const firstName = user.name.split(" ")[0];
  const initial = user.name.slice(0, 1).toUpperCase();
  const totalInvested = positions.reduce((sum, position) => sum + position.preco_medio * position.stock_quantity, 0);
  const totalShares = positions.reduce((sum, position) => sum + position.stock_quantity, 0);
  const largest = positions.reduce<Position | null>((best, position) => (
    !best || position.preco_medio * position.stock_quantity > best.preco_medio * best.stock_quantity ? position : best
  ), null);
  const portfolioCount = portfolios?.length ?? 0;

  const navItems = [
    { id: "visao-geral", label: "Visão geral", icon: "grid" as const },
    { id: "rendimentos", label: "Rendimentos", icon: "trend" as const },
    { id: "carteira", label: "Minha carteira", icon: "wallet" as const },
    { id: "registrar", label: "Registrar operação", icon: "chart" as const },
  ];

  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <a className="brand-lockup" href="/" aria-label="All Invest, início"><span className="brand-mark">A<span>I</span></span><span>all<span>invest</span></span></a>
        <div className="workspace-label">ESPAÇO PESSOAL</div>
        <nav className="side-nav" aria-label="Navegação principal">
          {navItems.map((item) => (
            <a
              key={item.id}
              className={`side-link ${section === item.id ? "active" : ""}`}
              href={`#${item.id}`}
              aria-current={section === item.id ? "location" : undefined}
              title={item.label}
              onClick={(event) => {
                if (item.id === "registrar") {
                  event.preventDefault();
                  focusTradeForm();
                } else {
                  setSection(item.id);
                }
              }}
            >
              <Icon name={item.icon} /><span>{item.label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-user">
            <span className="avatar">{initial}</span>
            <span className="sidebar-user-copy"><strong>{user.name}</strong><small>{user.email}</small></span>
          </div>
          <button className="side-link logout-link" type="button" onClick={handleLogout} disabled={signingOut}>
            <Icon name="logout" /><span>{signingOut ? "Saindo…" : "Sair da conta"}</span>
          </button>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="breadcrumb">Minha conta <span>/</span> <strong>Visão geral</strong></div>
          <div className="topbar-right">
            <button type="button" className="topbar-cta" onClick={focusTradeForm}>
              <Icon name="plus" size={17} /> Nova operação
            </button>
            <span className="topbar-avatar" title={user.name}>{initial}</span>
            <button className="topbar-logout" type="button" onClick={handleLogout} disabled={signingOut}>
              <Icon name="logout" size={16} /><span className="sr-only">{signingOut ? "Saindo…" : "Sair da conta"}</span>
            </button>
          </div>
        </header>

        <div className="dashboard-content" id="visao-geral">
          <section className="welcome-row">
            <div>
              <span className="eyebrow">SUA VIDA FINANCEIRA, ORGANIZADA</span>
              <h1>Olá, {firstName}!</h1>
              <p>{positions.length > 0 ? "Este é o resumo dos seus investimentos." : "Vamos montar sua carteira? Registre sua primeira compra."}</p>
            </div>
            <span className="today-label">{todayLabel}</span>
          </section>

          <section className="summary-grid" aria-label="Resumo da carteira">
            <article className="summary-card featured-card">
              <div className="summary-top"><span>Valor aplicado</span><span className="summary-icon gold-icon"><Icon name="wallet" size={18} /></span></div>
              <strong>{loading ? "—" : currency.format(totalInvested)}</strong>
              <small>Custo total das posições pelo preço médio</small>
            </article>
            <article className="summary-card">
              <div className="summary-top"><span>Ativos na carteira</span><span className="summary-icon teal-icon"><Icon name="layers" size={18} /></span></div>
              <strong>{loading ? "—" : positions.length}</strong>
              <small>{loading ? "Carregando…" : `${quantityFormat.format(totalShares)} ações em custódia${portfolioCount ? ` · ${portfolioCount} ${portfolioCount === 1 ? "carteira" : "carteiras"}` : ""}`}</small>
            </article>
            <article className="summary-card">
              <div className="summary-top"><span>Maior posição</span><span className="summary-icon blue-icon"><Icon name="pie" size={18} /></span></div>
              <strong>{loading ? "—" : largest ? largest.stock_name : "Nenhuma"}</strong>
              <small>
                {loading ? "Carregando…" : largest
                  ? `${currency.format(largest.preco_medio * largest.stock_quantity)} · ${percent.format((largest.preco_medio * largest.stock_quantity) / totalInvested)} do total`
                  : "Registre uma compra para começar"}
              </small>
            </article>
          </section>

          <ReturnsPanel refreshKey={returnsVersion} onBuy={focusTradeForm} />

          <section className="workspace-grid">
            <HoldingsPanel
              positions={positions}
              portfolios={portfolios}
              filter={filter}
              loading={loading}
              loadError={loadError}
              highlight={highlight}
              movingTicker={movingTicker}
              onFilterChange={setFilter}
              onRetry={() => { setLoading(true); void loadDashboard(); }}
              onBuy={(ticker, portfolioId) => openTrade("BUY", ticker, portfolioId ?? (typeof filter === "number" ? filter : null))}
              onSell={(position) => openTrade("SELL", position.stock_name)}
              onRemove={(position) => setDialog({ type: "remove", position })}
              onMoveRequest={(position) => setDialog({ type: "move", position })}
              onNewPortfolio={() => openNewPortfolio()}
              onDeletePortfolio={(portfolio) => setDialog({ type: "delete-portfolio", portfolio })}
            />

            <aside className="panel trade-panel" id="registrar" ref={tradePanelRef} aria-labelledby="trade-title">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">NOVA MOVIMENTAÇÃO</span>
                  <h2 id="trade-title">Registrar operação</h2>
                </div>
              </div>
              <p className="trade-intro">Informe uma compra ou venda de ações da B3. O ativo é validado antes de salvar.</p>
              <TradeForm
                key={draft.nonce}
                draft={draft}
                positions={positions}
                portfolios={portfolios}
                brokers={brokers}
                onSaved={handleSaved}
                onNotify={notify}
                onNewPortfolio={openNewPortfolio}
                onNewBroker={openNewBroker}
              />
            </aside>
          </section>

          <footer className="dashboard-footer">
            <span>All Invest <span className="footer-dot">•</span> Dados seguros e vinculados à sua conta</span>
            <span>Investir envolve riscos. Acompanhe seus ativos com atenção.</span>
          </footer>
        </div>
      </main>

      <ToastViewport toasts={toasts} onDismiss={dismissToast} />

      {dialog?.type === "remove" && (
        <Modal
          tone="danger"
          title={`Remover ${dialog.position.stock_name}?`}
          description={<>Todas as compras e vendas de <strong>{dialog.position.stock_name}</strong> ({quantityFormat.format(dialog.position.stock_quantity)} ações, {currency.format(dialog.position.preco_medio * dialog.position.stock_quantity)} aplicados) serão apagadas. Esta ação não pode ser desfeita.</>}
          onClose={() => !dialogBusy && setDialog(null)}
        >
          <div className="modal-actions">
            <button type="button" className="ghost-button" onClick={() => setDialog(null)} disabled={dialogBusy} autoFocus>Cancelar</button>
            <button type="button" className="solid-button danger" onClick={() => void confirmRemove(dialog.position)} disabled={dialogBusy}>
              {dialogBusy ? "Removendo…" : "Remover ativo"}
            </button>
          </div>
        </Modal>
      )}

      {dialog?.type === "move" && (
        <Modal
          title={`Mover ${dialog.position.stock_name}`}
          description={dialog.position.portfolio_name ? <>Hoje o ativo está em <strong>{dialog.position.portfolio_name}</strong>. Escolha a nova carteira.</> : "Escolha a carteira onde este ativo deve ficar."}
          onClose={() => setDialog(null)}
        >
          <div className="move-options">
            {portfolios?.map((portfolio) => {
              const current = portfolio.portfolio_id === dialog.position.portfolio_id;
              return (
                <button
                  key={portfolio.portfolio_id}
                  type="button"
                  className={`move-option ${current ? "current" : ""}`}
                  disabled={current}
                  onClick={() => void handleMove(dialog.position, portfolio)}
                >
                  <Icon name="folder" size={18} />
                  <span>{portfolio.portfolio_name}</span>
                  {current ? <small>Carteira atual</small> : <Icon name="arrow" size={16} />}
                </button>
              );
            })}
          </div>
          <div className="modal-actions">
            <button type="button" className="link-button" onClick={() => {
              const position = dialog.position;
              openNewPortfolio((created) => void handleMove(position, created));
            }}>
              <Icon name="plus" size={14} /> Criar nova carteira
            </button>
            <button type="button" className="ghost-button" onClick={() => setDialog(null)}>Cancelar</button>
          </div>
        </Modal>
      )}

      {dialog?.type === "delete-portfolio" && (
        <Modal
          tone="danger"
          title={`Excluir a carteira “${dialog.portfolio.portfolio_name}”?`}
          description="Os ativos dela não são apagados: eles continuam na sua conta, sem carteira."
          onClose={() => !dialogBusy && setDialog(null)}
        >
          <div className="modal-actions">
            <button type="button" className="ghost-button" onClick={() => setDialog(null)} disabled={dialogBusy} autoFocus>Cancelar</button>
            <button type="button" className="solid-button danger" onClick={() => void confirmDeletePortfolio(dialog.portfolio)} disabled={dialogBusy}>
              {dialogBusy ? "Excluindo…" : "Excluir carteira"}
            </button>
          </div>
        </Modal>
      )}

      {dialog?.type === "new-portfolio" && (
        <PortfolioDialog
          onClose={() => { portfolioCreated.current = null; setDialog(null); }}
          onCreated={(portfolio) => handlePortfolioCreated(portfolio, dialog.selectAfter)}
        />
      )}

      {dialog?.type === "new-broker" && (
        <BrokerDialog
          onClose={() => { brokerCreated.current = null; setDialog(null); }}
          onCreated={handleBrokerCreated}
        />
      )}
    </div>
  );
}
