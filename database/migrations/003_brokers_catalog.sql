-- Broker Component: catálogo global de corretoras.
-- Garante nome único (sem diferenciar maiúsculas) e cadastra as corretoras
-- que antes existiam apenas no catálogo fixo do código. Pode ser executada
-- mais de uma vez; as corretoras e operações existentes são preservadas.

CREATE UNIQUE INDEX IF NOT EXISTS uq_brokers_name_lower ON brokers (LOWER(broker_name));

INSERT INTO brokers (broker_name)
SELECT nome
FROM (VALUES ('XP Investimentos'), ('Rico'), ('Clear'), ('NuInvest')) AS padrao(nome)
WHERE NOT EXISTS (
    SELECT 1 FROM brokers WHERE LOWER(brokers.broker_name) = LOWER(padrao.nome)
);
