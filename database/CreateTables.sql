-- =========================================================
-- Script de criação das tabelas - PostgreSQL
-- Modelo: users, stocks, brokers, users_stocks, users_brokers
-- =========================================================

-- Tabela: users
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    name          VARCHAR(150) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela: stocks
CREATE TABLE stocks (
    stock_id     SERIAL PRIMARY KEY,
    stock_name   VARCHAR(20) NOT NULL,
    company_name VARCHAR(150) NOT NULL
);

-- Tabela: brokers
CREATE TABLE brokers (
    broker_id   SERIAL PRIMARY KEY,
    broker_name VARCHAR(150) NOT NULL
);

-- Tabela: users_stocks (associativa N:N entre users e stocks, com broker_id como FK adicional)
CREATE TABLE users_stocks (
    stock_id      INT NOT NULL,
    user_id       INT NOT NULL,
    stock_quantity INT NOT NULL,
    trade_date    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stock_price   NUMERIC(15,4) NOT NULL,
    broker_id     INT NOT NULL,
    trade_side    VARCHAR(10) NOT NULL,
    PRIMARY KEY (stock_id, user_id, trade_date),
    CONSTRAINT fk_users_stocks_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_users_stocks_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_users_stocks_broker
        FOREIGN KEY (broker_id) REFERENCES brokers(broker_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_trade_side
        CHECK (trade_side IN ('BUY', 'SELL'))
);

-- Tabela: users_brokers (associativa N:N entre users e brokers)
CREATE TABLE users_brokers (
    broker_id INT NOT NULL,
    user_id   INT NOT NULL,
    PRIMARY KEY (broker_id, user_id),
    CONSTRAINT fk_users_brokers_broker
        FOREIGN KEY (broker_id) REFERENCES brokers(broker_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_users_brokers_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- =========================================================
-- Índices auxiliares para consultas comuns
-- =========================================================
CREATE INDEX idx_users_stocks_user_id  ON users_stocks(user_id);
CREATE INDEX idx_users_stocks_stock_id ON users_stocks(stock_id);
CREATE INDEX idx_users_stocks_broker_id ON users_stocks(broker_id);
CREATE INDEX idx_users_brokers_user_id ON users_brokers(user_id);
CREATE INDEX idx_users_brokers_broker_id ON users_brokers(broker_id);