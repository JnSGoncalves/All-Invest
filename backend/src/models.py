from sqlalchemy import CheckConstraint, Column, Integer, String, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from .db.database import Base


class User(Base):
    """Tabela 'users' do MER — único bloco necessário para a HU01 (cadastro)."""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stocks = relationship("UserStock", back_populates="user")
    brokers = relationship("UserBroker", back_populates="user")


# ---------------------------------------------------------------------------
# Tabelas abaixo seguem o MER para manter o schema completo e consistente,
# mas ainda não têm regra de negócio implementada — entram nas próximas
# histórias (HU03 a HU11: corretoras e ações).
# ---------------------------------------------------------------------------

class Stock(Base):
    __tablename__ = "stocks"

    stock_id = Column(Integer, primary_key=True, index=True)
    stock_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)


class Broker(Base):
    __tablename__ = "brokers"

    broker_id = Column(Integer, primary_key=True, index=True)
    broker_name = Column(String, nullable=False)


class UserStock(Base):
    __tablename__ = "users_stocks"

    stock_id = Column(Integer, ForeignKey("stocks.stock_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    stock_quantity = Column(Integer, nullable=False)
    trade_date = Column(DateTime(timezone=True), primary_key=True, server_default=func.now())
    stock_price = Column(Numeric(15, 4), nullable=False)
    broker_id = Column(Integer, ForeignKey("brokers.broker_id"), nullable=False)
    trade_side = Column(String, nullable=False)  # valores aceitos pelo schema: BUY / SELL

    __table_args__ = (
        CheckConstraint("trade_side IN ('BUY', 'SELL')", name="chk_trade_side"),
    )

    user = relationship("User", back_populates="stocks")
    stock = relationship("Stock")
    broker = relationship("Broker")


class UserBroker(Base):
    __tablename__ = "users_brokers"

    broker_id = Column(Integer, ForeignKey("brokers.broker_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

    user = relationship("User", back_populates="brokers")
    broker = relationship("Broker")
