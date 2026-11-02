"""
Testes da exportação em Excel (Report Component) pela API REST.

Cada teste abre o arquivo gerado com o openpyxl e confere o conteúdo das abas.
Somente a autenticação e o Market Data são simulados.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import HTTPException, status
from openpyxl import load_workbook

from src import main, models
from src.dependencies.auth import get_current_user
from src.services import performance_service

URL = "/api/reports/export"
QUOTE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada.")


def _portfolio(client, name="Dividendos") -> int:
    response = client.post("/api/portfolios", json={"portfolio_name": name})
    assert response.status_code == 201, response.text
    return response.json()["portfolio_id"]


def _trade(client, ticker="PETR4", quantity=10, price="30.00", side="BUY", **changes):
    payload = {
        "stock_name": ticker,
        "stock_quantity": quantity,
        "stock_price": price,
        "broker_id": 1,
        "trade_side": side,
        **changes,
    }
    response = client.post("/api/stocks", json=payload)
    assert response.status_code == 201, response.text


def _income(client, ticker="PETR4", amount="15.50", kind="DIVIDEND"):
    response = client.post(
        "/api/incomes",
        json={"stock_name": ticker, "amount": amount, "received_at": "2026-09-02T12:00:00Z", "kind": kind},
    )
    assert response.status_code == 201, response.text


def _workbook(client, **params):
    response = client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return load_workbook(BytesIO(response.content))


def _position_rows(sheet) -> dict[str, dict]:
    headers = [cell.value for cell in sheet[1]]
    return {
        row[0]: dict(zip(headers, row))
        for row in sheet.iter_rows(min_row=2, values_only=True)
        if row[0] != "Total"
    }


def _total_row(sheet) -> dict:
    headers = [cell.value for cell in sheet[1]]
    return dict(zip(headers, next(row for row in sheet.iter_rows(values_only=True) if row[0] == "Total")))


def _summary(sheet) -> dict:
    return {row[0]: row[1] for row in sheet.iter_rows(values_only=True) if row[0]}


def _trade_rows(sheet) -> list[tuple]:
    rows = []
    for row in sheet.iter_rows(min_row=6, max_col=8, values_only=True):
        if row[0] is None:
            break
        rows.append(row)
    return rows


def test_resposta_e_um_arquivo_excel_para_download(client):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert 'attachment; filename="all-invest-carteira.xlsx"' == response.headers["content-disposition"]
    assert load_workbook(BytesIO(response.content)).properties.creator == "All Invest"


def test_abas_resumo_posicoes_e_uma_por_acao(client):
    _trade(client, "VALE3")
    _trade(client, "PETR4")

    assert _workbook(client).sheetnames == ["Resumo", "Posições", "PETR4", "VALE3"]


def test_posicoes_trazem_numeros_reais_e_os_valores_do_servico(client, market_data):
    market_data.quotes["PETR4"] = Decimal("33.50")
    portfolio_id = _portfolio(client)
    _trade(client, portfolio_id=portfolio_id)

    sheet = _workbook(client)["Posições"]
    row = _position_rows(sheet)["PETR4"]

    assert row["Empresa"] == "Petróleo Brasileiro S.A. - Petrobras"
    assert row["Carteira"] == "Dividendos"
    assert row["Situação"] == "Aberta"
    assert row["Quantidade"] == 10
    assert row["Preço médio"] == 30
    assert row["Cotação"] == 33.5
    assert row["Valor investido"] == 300
    assert row["Valor de mercado"] == 335
    assert row["Valorização"] == 35
    assert row["Valorização (%)"] == pytest.approx(0.1167)
    for value in (row["Cotação"], row["Valor de mercado"], row["Valorização (%)"]):
        assert isinstance(value, (int, float))
    assert sheet["K2"].number_format.startswith("0.00%")
    assert sheet["H2"].number_format.startswith('"R$"')


def test_valores_batem_com_a_api_de_desempenho(client, market_data):
    market_data.quotes.update({"PETR4": Decimal("33"), "VALE3": Decimal("30")})
    portfolio_id = _portfolio(client)
    _trade(client, "PETR4", 100, "30", portfolio_id=portfolio_id)
    _trade(client, "VALE3", 1, "60", portfolio_id=portfolio_id)
    api = client.get(f"/api/performance/portfolios/{portfolio_id}").json()

    workbook = _workbook(client, portfolio_id=portfolio_id)
    total = _total_row(workbook["Posições"])
    summary = _summary(workbook["Resumo"])

    assert Decimal(str(total["Valor investido"])) == Decimal(api["total_invested"])
    assert Decimal(str(total["Valor de mercado"])) == Decimal(api["total_market_value"])
    assert Decimal(str(total["Valorização"])) == Decimal(api["total_gain"])
    # Pelos totais (270 / 3060), como no serviço, e não pela média das ações.
    assert total["Valorização (%)"] * 100 == pytest.approx(float(api["profitability_pct"]), abs=0.01)
    assert summary["Valor investido"] == total["Valor investido"]
    assert summary["Valorização (%)"] == pytest.approx(total["Valorização (%)"])


def test_acao_sem_carteira_entra_na_exportacao_completa(client):
    _trade(client)

    row = _position_rows(_workbook(client)["Posições"])["PETR4"]

    assert row["Carteira"] == "Sem carteira"
    assert row["Situação"] == "Aberta"


def test_filtro_por_carteira_mostra_somente_as_acoes_dela(client):
    primeira = _portfolio(client, "Primeira")
    segunda = _portfolio(client, "Segunda")
    _trade(client, "PETR4", portfolio_id=primeira)
    _trade(client, "VALE3", portfolio_id=segunda)
    _trade(client, "ITUB4")
    _income(client, "VALE3")

    workbook = _workbook(client, portfolio_id=primeira)

    assert workbook.sheetnames == ["Resumo", "Posições", "PETR4"]
    summary = _summary(workbook["Resumo"])
    assert summary["Carteira"] == "Primeira"
    assert summary["Proventos registrados"] == 0


def test_aba_da_acao_tem_saldo_e_preco_medio_de_cada_operacao(client, db, user):
    _trade(client, quantity=10, price="30", trade_date="2026-01-10T15:00:00Z")
    _trade(client, quantity=10, price="20", trade_date="2026-02-10T15:00:00Z")
    _trade(client, quantity=5, price="50", side="SELL", trade_date="2026-03-10T15:00:00Z")

    workbook = _workbook(client)
    rows = _trade_rows(workbook["PETR4"])

    assert [row[1] for row in rows] == ["Compra", "Compra", "Venda"]
    assert [row[2] for row in rows] == [10, 10, 5]
    assert [row[4] for row in rows] == [300, 200, 250]
    assert [row[5] for row in rows] == ["XP Investimentos"] * 3
    assert [row[6] for row in rows] == [10, 20, 15]
    assert [row[7] for row in rows] == [30, 25, 25]
    # O último preço médio é o mesmo da aba Posições, calculado pelo Investment.
    assert _position_rows(workbook["Posições"])["PETR4"]["Preço médio"] == rows[-1][7]


def test_data_da_operacao_usa_o_dia_em_brasilia(client):
    _trade(client, trade_date="2026-01-01T01:00:00Z")

    cell = _workbook(client)["PETR4"]["A6"]

    assert cell.value == datetime(2025, 12, 31)
    assert cell.number_format == "dd/mm/yyyy"


def test_acao_vendida_por_inteiro_mantem_aba_e_fica_encerrada(client, market_data):
    _trade(client, quantity=10, trade_date="2026-01-10T15:00:00Z")
    _trade(client, quantity=10, side="SELL", trade_date="2026-02-10T15:00:00Z")
    _income(client)
    performance_service._QUOTE_CACHE.clear()
    market_data.calls.clear()

    workbook = _workbook(client)
    row = _position_rows(workbook["Posições"])["PETR4"]

    assert row["Situação"] == "Encerrada"
    assert row["Quantidade"] == 0
    assert row["Valor de mercado"] is None
    assert row["Proventos"] == 15.5
    assert len(_trade_rows(workbook["PETR4"])) == 2
    assert _trade_rows(workbook["PETR4"])[-1][7] is None
    assert _summary(workbook["Resumo"])["Ações encerradas"] == 1
    assert market_data.calls == []


def test_proventos_aparecem_na_aba_da_acao_e_nos_totais(client):
    _trade(client)
    _income(client, amount="15.50")
    _income(client, amount="4.50", kind="JCP")

    workbook = _workbook(client)
    values = [row for row in workbook["PETR4"].iter_rows(values_only=True)]

    assert (datetime(2026, 9, 2), "JCP", 4.5) in [row[:3] for row in values]
    assert (None, "Total", 20) in [row[:3] for row in values]
    assert _position_rows(workbook["Posições"])["PETR4"]["Proventos"] == 20
    assert _total_row(workbook["Posições"])["Proventos"] == 20
    assert _summary(workbook["Resumo"])["Proventos registrados"] == 20


def test_provento_de_ativo_removido_continua_na_planilha(client):
    _trade(client)
    _income(client)
    assert client.delete("/api/stocks/PETR4").status_code == 200

    workbook = _workbook(client)

    assert "PETR4" in workbook.sheetnames
    assert _position_rows(workbook["Posições"])["PETR4"]["Situação"] == "Encerrada"
    assert workbook["PETR4"]["A6"].value == "Nenhuma movimentação registrada."


def test_acao_sem_cotacao_fica_marcada_e_fora_dos_totais(client, market_data):
    market_data.quotes["PETR4"] = Decimal("40")
    _trade(client, "PETR4", 10, "30")
    _trade(client, "VALE3", 10, "60")
    market_data.quotes["VALE3"] = QUOTE_NOT_FOUND
    performance_service._QUOTE_CACHE.clear()

    workbook = _workbook(client)
    rows = _position_rows(workbook["Posições"])

    assert rows["PETR4"]["Situação"] == "Aberta"
    assert rows["VALE3"]["Situação"] == "Sem cotação"
    assert rows["VALE3"]["Quantidade"] == 10
    assert rows["VALE3"]["Valor de mercado"] is None
    assert _total_row(workbook["Posições"])["Valor investido"] == 300
    summary = _summary(workbook["Resumo"])
    assert summary["Posições abertas"] == 2
    assert summary["Valor de mercado"] == 400
    assert "Sem cotação no momento, fora dos totais: VALE3." in summary


def test_provedor_lento_nao_impede_a_exportacao(client, market_data, monkeypatch):
    _trade(client)
    performance_service._QUOTE_CACHE.clear()

    async def slow_quote(_ticker):
        await asyncio.sleep(1)

    monkeypatch.setattr(performance_service, "QUOTES_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(market_data, "get_quote", slow_quote)

    assert _position_rows(_workbook(client)["Posições"])["PETR4"]["Situação"] == "Sem cotação"


def test_texto_digitado_nao_vira_formula(client, db):
    formula = '=HYPERLINK("http://exemplo.test","clique")'
    db.add(models.Broker(broker_id=50, broker_name=formula))
    db.commit()
    portfolio_id = _portfolio(client, "=1+1")
    _trade(client, broker_id=50, portfolio_id=portfolio_id)

    workbook = _workbook(client)

    broker = workbook["PETR4"]["F6"]
    assert broker.value == formula
    assert broker.data_type == "s"
    portfolio = workbook["Posições"]["C2"]
    assert portfolio.value == "=1+1"
    assert portfolio.data_type == "s"


def test_caractere_de_controle_nao_quebra_o_arquivo(client, db):
    db.add(models.Broker(broker_id=50, broker_name="Corretora\x01 Teste"))
    db.commit()
    _trade(client, broker_id=50)

    assert _workbook(client)["PETR4"]["F6"].value == "Corretora Teste"


def test_links_levam_para_as_abas(client):
    _trade(client)

    workbook = _workbook(client)

    assert workbook["Posições"]["A2"].hyperlink.location == "'PETR4'!A1"
    assert workbook["PETR4"]["A2"].hyperlink.location == "'Posições'!A1"


def test_carteira_vazia_gera_planilha_com_totais_zerados(client):
    workbook = _workbook(client)

    assert workbook.sheetnames == ["Resumo", "Posições"]
    summary = _summary(workbook["Resumo"])
    assert summary["Carteira"] == "Todas as posições"
    assert summary["Posições abertas"] == 0
    assert summary["Valor de mercado"] == 0
    assert summary["Valorização (%)"] is None


def test_dados_de_outro_usuario_nao_aparecem(client, other_user):
    portfolio_id = _portfolio(client)
    _trade(client, portfolio_id=portfolio_id)
    _income(client)

    main.app.dependency_overrides[get_current_user] = lambda: other_user

    assert _workbook(client).sheetnames == ["Resumo", "Posições"]
    assert client.get(URL, params={"portfolio_id": portfolio_id}).status_code == 404


@pytest.mark.parametrize("portfolio_id", ["0", "-1", "abc"])
def test_portfolio_id_invalido_retorna_422(client, portfolio_id):
    assert client.get(URL, params={"portfolio_id": portfolio_id}).status_code == 422


def test_carteira_inexistente_retorna_404(client):
    assert client.get(URL, params={"portfolio_id": 999}).status_code == 404


def test_sem_autenticacao_retorna_401(client):
    del main.app.dependency_overrides[get_current_user]

    assert client.get(URL).status_code == 401


def test_chave_de_api_invalida_retorna_401(client):
    assert client.get(URL, headers={"X-API-Key": "chave-errada"}).status_code == 401
