CREATE TABLE IF NOT EXISTS investment_incomes (
    income_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    stock_name VARCHAR(20) NOT NULL,
    amount NUMERIC(15,4) NOT NULL CONSTRAINT chk_income_amount CHECK (amount > 0),
    received_at TIMESTAMPTZ NOT NULL,
    kind VARCHAR(20) NOT NULL CONSTRAINT chk_income_kind CHECK (kind IN ('DIVIDEND', 'JCP', 'OTHER'))
);
CREATE INDEX IF NOT EXISTS ix_investment_incomes_user_id ON investment_incomes(user_id);
