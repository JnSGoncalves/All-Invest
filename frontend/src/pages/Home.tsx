import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { createTrade, getPositions, removePosition, type Position } from "../services/api";
import { useAuth } from "../contexts/auth-context";
import "./Home.css";

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function Icon({ name }: { name: "grid" | "wallet" | "chart" | "settings" | "plus" | "arrow" | "logout" | "trash" }) {
  const shared = { width: 19, height: 19, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true as const };
  const paths = {
    grid: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></>,
    wallet: <><rect x="3" y="6" width="18" height="14" rx="2.5"/><path d="M3 9h18M16 14h.01M7 6V4.5A1.5 1.5 0 0 1 8.5 3H19"/></>,
    chart: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 6-7"/><path d="M16.5 6H20v3.5"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.2 1-1.2 2.1-1.5-.5a8 8 0 0 1-1.8 1l-.3 1.6h-2.4l-.3-1.6a8 8 0 0 1-1.8-1l-1.5.5-1.2-2.1 1.2-1a7 7 0 0 1 0-2l-1.2-1 1.2-2.1 1.5.5a8 8 0 0 1 1.8-1l.3-1.6h2.4l.3 1.6a8 8 0 0 1 1.8 1l1.5-.5 1.2 2.1-1.2 1a7 7 0 0 1-.1 1.9Z"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></>,
    trash: <><path d="M4 7h16M10 11v6M14 11v6M5 7l1 13h12l1-13M9 7V4h6v3"/></>,
  };
  return <svg {...shared}>{paths[name]}</svg>;
}

export default function Home() {
  const { user, logout } = useAuth();
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [broker, setBroker] = useState("1");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");

  const refreshPositions = useCallback(async () => {
    setError(null);
    try { setPositions(await getPositions()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar sua carteira."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    let active = true;
    getPositions()
      .then((data) => { if (active) setPositions(data); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Não foi possível carregar sua carteira.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const totalInvested = useMemo(() => positions.reduce((sum, position) => sum + position.preco_medio * position.stock_quantity, 0), [positions]);
  const totalShares = useMemo(() => positions.reduce((sum, position) => sum + position.stock_quantity, 0), [positions]);

  async function handleTrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setNotice(null); setSaving(true);
    try {
      await createTrade({ stock_name: ticker.trim().toUpperCase(), stock_quantity: Number(quantity), stock_price: Number(price.replace(",", ".")), broker_id: Number(broker), trade_side: side });
      setNotice(side === "BUY" ? "Compra registrada. Sua carteira foi atualizada." : "Venda registrada. Sua carteira foi atualizada.");
      setTicker(""); setQuantity(""); setPrice(""); setSide("BUY");
      await refreshPositions();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível registrar a movimentação."); }
    finally { setSaving(false); }
  }

  async function handleRemove(position: Position) {
    const confirmed = window.confirm(`Remover ${position.stock_name} e todo o histórico de movimentações desta carteira? Esta ação não pode ser desfeita.`);
    if (!confirmed) return;
    setError(null); setNotice(null);
    try { await removePosition(position.stock_name); setNotice(`${position.stock_name} foi removida da carteira.`); await refreshPositions(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível remover o ativo."); }
  }

  async function handleLogout() {
    setSigningOut(true);
    setError(null);
    try { await logout(); }
    catch { setError("Não foi possível encerrar a sessão no servidor. Tente sair novamente."); }
    finally { setSigningOut(false); }
  }
  if (!user) return null;

  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <a className="brand-lockup" href="/" aria-label="All Invest, início"><span className="brand-mark">A<span>I</span></span><span>all<span>invest</span></span></a>
        <div className="workspace-label">ESPAÇO PESSOAL</div>
        <nav className="side-nav" aria-label="Navegação principal">
          <a className="side-link active" href="#visao-geral"><Icon name="grid"/><span>Visão geral</span></a>
          <a className="side-link" href="#carteira"><Icon name="wallet"/><span>Minha carteira</span></a>
          <a className="side-link" href="#registrar-acao"><Icon name="chart"/><span>Registrar ação</span></a>
        </nav>
        <div className="sidebar-bottom"><button className="side-link logout-link" onClick={handleLogout} disabled={signingOut}><Icon name="logout"/><span>{signingOut ? "Saindo…" : "Sair da conta"}</span></button><div className="sidebar-user"><span className="avatar">{user.name.slice(0, 1).toUpperCase()}</span><span className="sidebar-user-copy"><strong>{user.name}</strong><small>Investidor</small></span><Icon name="settings"/></div></div>
      </aside>

      <main className="dashboard-main" id="visao-geral">
        <header className="topbar"><div className="breadcrumb">Minha conta <span>/</span> <strong>Visão geral</strong></div><div className="topbar-right"><span className="market-status"><i/> B3 • carteira pessoal</span><span className="topbar-avatar">{user.name.slice(0, 1).toUpperCase()}</span><button className="topbar-logout" type="button" onClick={handleLogout} disabled={signingOut}>{signingOut ? "Saindo…" : "Sair da conta"}</button></div></header>
        <div className="dashboard-content">
          <section className="welcome-row"><div><span className="eyebrow">SUA VIDA FINANCEIRA, ORGANIZADA</span><h1>Olá, {user.name.split(" ")[0]} <span>👋</span></h1><p>Acompanhe seus investimentos em um só lugar.</p></div><span className="today-label">CARTEIRA B3</span></section>

          {error && <div className="dashboard-alert error-alert" role="alert">{error}<button onClick={() => setError(null)} aria-label="Fechar">×</button></div>}
          {notice && <div className="dashboard-alert success-alert" role="status">{notice}<button onClick={() => setNotice(null)} aria-label="Fechar">×</button></div>}

          <section className="summary-grid" aria-label="Resumo da carteira">
            <article className="summary-card featured-card"><div className="summary-top"><span>VALOR APLICADO</span><span className="summary-icon gold-icon"><Icon name="wallet"/></span></div><strong>{loading ? "—" : currency.format(totalInvested)}</strong><small>Com base no preço médio das posições</small></article>
            <article className="summary-card"><div className="summary-top"><span>ATIVOS NA CARTEIRA</span><span className="summary-icon teal-icon"><Icon name="chart"/></span></div><strong>{loading ? "—" : positions.length.toString().padStart(2, "0")}</strong><small>Ações com posição aberta</small><div className="summary-meta"><span className="meta-dot"/> Seus ativos</div></article>
            <article className="summary-card"><div className="summary-top"><span>AÇÕES EM CUSTÓDIA</span><span className="summary-icon blue-icon"><Icon name="grid"/></span></div><strong>{loading ? "—" : totalShares.toLocaleString("pt-BR")}</strong><small>Total de unidades em carteira</small><div className="summary-meta">Quantidade registrada</div></article>
          </section>

          <section className="workspace-grid">
            <article className="panel holdings-panel" id="carteira"><div className="panel-heading"><div><span className="eyebrow">ACOMPANHAMENTO</span><h2>Minha carteira</h2></div><span className="holdings-count">{positions.length} {positions.length === 1 ? "ativo" : "ativos"}</span></div>
              {loading ? <div className="empty-state"><span className="loader"/>Carregando seus investimentos…</div> : positions.length === 0 ? <div className="empty-state"><span className="empty-icon"><Icon name="wallet"/></span><strong>Sua carteira começa aqui</strong><span>Registre sua primeira compra para acompanhar seus investimentos.</span></div> : <div className="table-wrap"><table className="holdings-table"><thead><tr><th>ATIVO</th><th>QUANTIDADE</th><th>PREÇO MÉDIO</th><th>VALOR APLICADO</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{positions.map((position) => <tr key={position.stock_name}><td><div className="asset-cell"><span className="asset-badge">{position.stock_name.slice(0, 1)}</span><span><strong>{position.stock_name}</strong><small>{position.company_name}</small></span></div></td><td>{position.stock_quantity.toLocaleString("pt-BR")} <small className="table-muted">un.</small></td><td>{currency.format(position.preco_medio)}</td><td className="value-cell">{currency.format(position.preco_medio * position.stock_quantity)}</td><td><button className="icon-button remove-button" onClick={() => void handleRemove(position)} title={`Remover ${position.stock_name}`} aria-label={`Remover ${position.stock_name} e seu histórico`}><Icon name="trash"/></button></td></tr>)}</tbody></table></div>}
              <div className="panel-footer"><span>Os valores exibidos consideram o custo médio das operações.</span><a href="#registrar-acao">Registrar movimentação <Icon name="arrow"/></a></div>
            </article>

            <article className="panel trade-panel" id="registrar-acao"><div className="panel-heading"><div><span className="eyebrow">NOVA MOVIMENTAÇÃO</span><h2>Registrar ação</h2></div><span className="panel-plus"><Icon name="plus"/></span></div><p className="trade-intro">Adicione uma compra ou venda à sua carteira.</p>
              <form className="trade-form" onSubmit={handleTrade}>
                <div className="side-toggle" role="group" aria-label="Tipo da operação"><button type="button" className={side === "BUY" ? "selected" : ""} onClick={() => setSide("BUY")}>Compra</button><button type="button" className={side === "SELL" ? "selected sell-selected" : ""} onClick={() => setSide("SELL")}>Venda</button></div>
                <label>Ticker da ação<input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} placeholder="Ex.: PETR4" autoComplete="off" required maxLength={20}/></label>
                <div className="form-pair"><label>Quantidade<input type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="0" min="1" step="1" required/></label><label>Preço por ação<input type="number" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="0,00" min="0.0001" step="0.0001" required/></label></div>
                <label>Corretora<select value={broker} onChange={(event) => setBroker(event.target.value)}><option value="1">XP Investimentos</option><option value="2">Rico</option><option value="3">Clear</option><option value="4">NuInvest</option></select></label>
                <button className="trade-submit" type="submit" disabled={saving}>{saving ? "Registrando…" : side === "BUY" ? "Registrar compra" : "Registrar venda"}<Icon name="arrow"/></button>
              </form>
              <div className="trade-note"><span>i</span>O ticker será validado pela B3 antes de salvar.</div>
            </article>
          </section>
          <footer className="dashboard-footer"><span>All Invest <span className="footer-dot">•</span> Dados seguros e vinculados à sua conta</span><span>Investir envolve riscos. Acompanhe seus ativos com atenção.</span></footer>
        </div>
      </main>
    </div>
  );
}
