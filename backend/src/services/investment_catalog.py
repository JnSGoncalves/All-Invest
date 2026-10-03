"""Catálogo provisório de corretoras usado pelo componente de investimentos."""

MOCK_BROKERS = {
    1: "XP Investimentos",
    2: "Rico",
    3: "Clear",
    4: "NuInvest",
}
BROKER_IDS_BY_NAME = {
    broker_name: broker_id for broker_id, broker_name in MOCK_BROKERS.items()
}
