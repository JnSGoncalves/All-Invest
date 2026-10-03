-- Schema PostgreSQL conforme modelo relacional + refresh_tokens.

CREATE TABLE api_keys (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    token_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expire_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE stocks (
    stock_id SERIAL PRIMARY KEY,
    stock_name VARCHAR(20) NOT NULL,
    company_name VARCHAR(150) NOT NULL
);

CREATE TABLE brokers (
    broker_id SERIAL PRIMARY KEY,
    broker_name VARCHAR(150) NOT NULL
);

CREATE TABLE users_stocks (
    stock_id INTEGER NOT NULL REFERENCES stocks(stock_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    stock_quantity INTEGER NOT NULL,
    trade_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stock_price NUMERIC(15,4) NOT NULL,
    broker_id INTEGER NOT NULL REFERENCES brokers(broker_id),
    trade_side VARCHAR NOT NULL,
    PRIMARY KEY (stock_id, user_id, trade_date),
    CONSTRAINT chk_trade_side CHECK (trade_side IN ('BUY', 'SELL'))
);

CREATE TABLE users_brokers (
    broker_id INTEGER NOT NULL REFERENCES brokers(broker_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    PRIMARY KEY (broker_id, user_id)
);

CREATE INDEX ix_users_user_id ON users(user_id);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX ix_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX ix_stocks_stock_id ON stocks(stock_id);
CREATE INDEX ix_brokers_broker_id ON brokers(broker_id);
CREATE INDEX ix_users_stocks_user_id ON users_stocks(user_id);
CREATE INDEX ix_users_stocks_stock_id ON users_stocks(stock_id);
CREATE INDEX ix_users_brokers_user_id ON users_brokers(user_id);
