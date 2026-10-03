import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..services import security
from .. import models
from . import schemas


def validate_api_key(db: Session, api_key: str) -> bool:
    return (
        db.query(models.ApiKey)
        .filter(models.ApiKey.api_key == api_key)
        .first()
        is not None
    )
    

def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return (
        db.query(models.User)
        .filter(models.User.email == email.strip().lower())
        .first()
    )


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """Persistência do Usuário (CA01): cria o registro com a senha já hasheada."""
    db_user = models.User(
        name=user_in.name.strip(),
        email=str(user_in.email).strip().lower(),
        password_hash=security.hash_password(user_in.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_google_user(db: Session, name: str, email: str) -> models.User:
    """Cria um usuário autenticado pelo Google sem armazenar senha utilizável."""
    db_user = models.User(
        name=name.strip(),
        email=email.strip().lower(),
        password_hash=security.hash_password(secrets.token_urlsafe(32)),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def add_refresh_token(
    db: Session,
    *,
    user_id: int,
    token_hash: str,
    expire_at: datetime,
) -> models.RefreshToken:
    token = models.RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expire_at=expire_at,
    )
    db.add(token)
    return token


def get_refresh_token_for_update(
    db: Session,
    token_hash: str,
) -> models.RefreshToken | None:
    return (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first()
    )


def revoke_refresh_token(db: Session, *, token_hash: str, user_id: int) -> bool:
    result = db.execute(
        delete(models.RefreshToken).where(
            models.RefreshToken.token_hash == token_hash,
            models.RefreshToken.user_id == user_id,
        )
    )
    db.commit()
    return bool(result.rowcount)


def revoke_all_refresh_tokens(db: Session, user_id: int) -> int:
    result = db.execute(
        delete(models.RefreshToken).where(models.RefreshToken.user_id == user_id)
    )
    db.commit()
    return int(result.rowcount or 0)


# ===========================================================================
# Stocks / Brokers / UserStocks
# ---------------------------------------------------------------------------
# Suporte ao cadastro de operações (routers/stocks.py). O ticker em si já é
# validado na B3 via services/market_data_service.py (brapi.dev); as funções
# abaixo só garantem a linha correspondente no catálogo local (`stocks`,
# `brokers`) para satisfazer as FKs de `users_stocks`.
# ===========================================================================


def get_stock_by_name(db: Session, stock_name: str) -> models.Stock | None:
    return db.query(models.Stock).filter(models.Stock.stock_name == stock_name).first()


def get_or_create_stock(db: Session, stock_name: str, company_name: str) -> models.Stock:
    """
    Retorna a linha de `stocks` para o ticker, criando-a se ainda não
    existir no catálogo local.
    """
    stock = get_stock_by_name(db, stock_name)
    if stock:
        return stock

    try:
        with db.begin_nested():
            stock = models.Stock(stock_name=stock_name, company_name=company_name)
            db.add(stock)
            db.flush()
    except IntegrityError:
        # Outra transação criou o mesmo ticker enquanto esta era processada.
        stock = get_stock_by_name(db, stock_name)
        if not stock:
            raise
    return stock


def get_broker_by_name(db: Session, broker_name: str) -> models.Broker | None:
    return (
        db.query(models.Broker)
        .filter(models.Broker.broker_name == broker_name)
        .first()
    )


def get_or_create_broker(db: Session, broker_name: str) -> models.Broker:
    """Garante a corretora usada pelo catálogo temporário no banco."""
    broker = get_broker_by_name(db, broker_name)
    if broker:
        return broker

    try:
        with db.begin_nested():
            broker = models.Broker(broker_name=broker_name)
            db.add(broker)
            db.flush()
    except IntegrityError:
        broker = get_broker_by_name(db, broker_name)
        if not broker:
            raise
    return broker


def get_broker_by_id(db: Session, broker_id: int) -> models.Broker | None:
    return db.get(models.Broker, broker_id)


def ensure_user_broker(db: Session, *, user_id: int, broker_id: int) -> None:
    """Vincula a corretora existente à carteira do usuário, se necessário."""
    association = db.get(models.UserBroker, (broker_id, user_id))
    if association is None:
        db.add(models.UserBroker(broker_id=broker_id, user_id=user_id))
        db.flush()


def get_user_stock_balance(
    db: Session, *, user_id: int, stock_name: str, lock: bool = False
) -> int:
    """Quantidade líquida de um ativo; `lock` evita vendas concorrentes acima do saldo."""
    statement = (
        select(models.UserStock)
        .join(models.Stock, models.Stock.stock_id == models.UserStock.stock_id)
        .where(
            models.UserStock.user_id == user_id,
            models.Stock.stock_name == stock_name,
        )
    )
    if lock:
        statement = statement.with_for_update()

    return sum(
        trade.stock_quantity if trade.trade_side == "BUY" else -trade.stock_quantity
        for trade in db.scalars(statement)
    )


def get_user_stock_trades(db: Session, user_id: int) -> list[models.UserStock]:
    """Retorna operações da carteira com os relacionamentos necessários carregados."""
    statement = (
        select(models.UserStock)
        .where(models.UserStock.user_id == user_id)
        .order_by(models.UserStock.trade_date.desc())
    )
    return list(db.scalars(statement))


def delete_user_stock_trades(db: Session, *, user_id: int, stock_name: str) -> int:
    """Remove apenas as operações do ativo pertencentes ao usuário."""
    statement = (
        select(models.UserStock)
        .join(models.Stock, models.Stock.stock_id == models.UserStock.stock_id)
        .where(
            models.UserStock.user_id == user_id,
            models.Stock.stock_name == stock_name,
        )
    )
    trades = list(db.scalars(statement))
    for trade in trades:
        db.delete(trade)
    if trades:
        db.commit()
    return len(trades)


def create_user_stock(
    db: Session,
    *,
    user_id: int,
    stock_id: int,
    broker_id: int,
    stock_quantity: int,
    stock_price: Decimal,
    trade_side: str,
    trade_date: datetime,
) -> models.UserStock:
    """
    Persiste uma operação de compra/venda em `users_stocks`.

    Commit único: como get_or_create_stock/broker usam apenas flush(), a
    linha nova de stocks/brokers (se houver) e a operação em si são
    gravadas juntas, na mesma transação.
    """
    user_stock = models.UserStock(
        user_id=user_id,
        stock_id=stock_id,
        broker_id=broker_id,
        stock_quantity=stock_quantity,
        stock_price=stock_price,
        trade_side=trade_side,
        trade_date=trade_date,
    )
    db.add(user_stock)
    db.commit()
    db.refresh(user_stock)
    return user_stock


# ===========================================================================
# Portfolios (Portfolio Component)
# ---------------------------------------------------------------------------
# Carteiras do usuário e a associação ativo -> carteira (`portfolios_stocks`).
# As regras de negócio ficam em services/portfolio_service.py.
# ===========================================================================


def create_portfolio(
    db: Session, *, user_id: int, portfolio_name: str, description: str | None
) -> models.Portfolio:
    portfolio = models.Portfolio(
        user_id=user_id,
        portfolio_name=portfolio_name,
        description=description,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def get_portfolio(
    db: Session, *, user_id: int, portfolio_id: int
) -> models.Portfolio | None:
    """Busca a carteira somente se ela pertencer ao usuário informado."""
    return (
        db.query(models.Portfolio)
        .filter(
            models.Portfolio.portfolio_id == portfolio_id,
            models.Portfolio.user_id == user_id,
        )
        .first()
    )


def get_portfolio_by_name(
    db: Session, *, user_id: int, portfolio_name: str
) -> models.Portfolio | None:
    return (
        db.query(models.Portfolio)
        .filter(
            models.Portfolio.user_id == user_id,
            func.lower(models.Portfolio.portfolio_name) == portfolio_name.lower(),
        )
        .first()
    )


def list_portfolios(db: Session, user_id: int) -> list[models.Portfolio]:
    statement = (
        select(models.Portfolio)
        .where(models.Portfolio.user_id == user_id)
        .order_by(models.Portfolio.portfolio_name)
    )
    return list(db.scalars(statement))


def update_portfolio(
    db: Session, portfolio: models.Portfolio, changes: dict
) -> models.Portfolio:
    for field, value in changes.items():
        setattr(portfolio, field, value)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def delete_portfolio(db: Session, portfolio: models.Portfolio) -> None:
    """Remove a carteira e as associações; as operações em users_stocks são mantidas."""
    db.execute(
        delete(models.PortfolioStock).where(
            models.PortfolioStock.portfolio_id == portfolio.portfolio_id
        )
    )
    db.delete(portfolio)
    db.commit()


def set_stock_portfolio(
    db: Session, *, user_id: int, stock_id: int, portfolio_id: int
) -> models.PortfolioStock:
    """Associa o ativo à carteira ou move-o, se já estiver em outra."""
    association = db.get(models.PortfolioStock, (user_id, stock_id))
    if association is None:
        association = models.PortfolioStock(
            user_id=user_id, stock_id=stock_id, portfolio_id=portfolio_id
        )
        db.add(association)
    else:
        association.portfolio_id = portfolio_id
    db.commit()
    return association


def delete_stock_portfolio(db: Session, *, user_id: int, stock_id: int) -> bool:
    result = db.execute(
        delete(models.PortfolioStock).where(
            models.PortfolioStock.user_id == user_id,
            models.PortfolioStock.stock_id == stock_id,
        )
    )
    db.commit()
    return bool(result.rowcount)


def get_stock_portfolios(db: Session, user_id: int) -> dict[int, models.Portfolio]:
    """Mapa stock_id -> carteira para os ativos associados do usuário."""
    statement = (
        select(models.PortfolioStock.stock_id, models.Portfolio)
        .join(
            models.Portfolio,
            models.Portfolio.portfolio_id == models.PortfolioStock.portfolio_id,
        )
        .where(models.PortfolioStock.user_id == user_id)
    )
    return {stock_id: portfolio for stock_id, portfolio in db.execute(statement)}
