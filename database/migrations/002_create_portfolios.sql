-- Lab 4 - Portfolio Component.
-- Cria as carteiras do usuário e a associação ativo -> carteira.
-- Migração apenas aditiva: nenhuma tabela existente é alterada.

CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    portfolio_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_portfolios_user_name UNIQUE (user_id, portfolio_name),
    CONSTRAINT uq_portfolios_id_user UNIQUE (portfolio_id, user_id)
);

-- Cada ativo do usuário pertence a no máximo uma carteira (PK user_id + stock_id).
-- A FK composta impede associar o ativo a uma carteira de outro usuário.
CREATE TABLE IF NOT EXISTS portfolios_stocks (
    user_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL REFERENCES stocks(stock_id),
    portfolio_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, stock_id),
    CONSTRAINT fk_portfolios_stocks_portfolio
        FOREIGN KEY (portfolio_id, user_id)
        REFERENCES portfolios(portfolio_id, user_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_portfolios_portfolio_id ON portfolios(portfolio_id);
CREATE INDEX IF NOT EXISTS ix_portfolios_user_id ON portfolios(user_id);
CREATE INDEX IF NOT EXISTS ix_portfolios_stocks_portfolio_id ON portfolios_stocks(portfolio_id);
