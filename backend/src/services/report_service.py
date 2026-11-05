"""
Report Component: exporta a carteira do usuário em uma planilha Excel.

É consumidor do Serviço de Desempenho: cotações, valores e valorização vêm de
IPerformanceService, as movimentações de IInvestmentService e os proventos de
IIncomeService, para que a planilha mostre os mesmos números da API.

A planilha traz as abas Resumo e Posições e uma aba por ação, inclusive das
ações já vendidas por inteiro, cujo histórico não aparece nas posições abertas.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.worksheet import Worksheet

from .. import models
from ..db import schemas
from ..interfaces import (
    IIncomeService,
    IInvestmentService,
    IPerformanceService,
    IPortfolioService,
)

BRT = timezone(timedelta(hours=-3), "BRT")
SUMMARY_SHEET = "Resumo"
POSITIONS_SHEET = "Posições"

MONEY = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
PRICE = '"R$" #,##0.00##'
PERCENT = "0.00%;[Red]-0.00%"
QUANTITY = "#,##0"
DATE = "dd/mm/yyyy"
DATETIME = "dd/mm/yyyy hh:mm"

TITLE_FONT = Font(bold=True, size=14, color="14324A")
SECTION_FONT = Font(bold=True, color="14324A")
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="14324A")
LINK_FONT = Font(color="0563C1", underline="single")
NOTE_FONT = Font(italic=True, color="555555")
BOLD_FONT = Font(bold=True)
TOTAL_BORDER = Border(top=Side(style="thin"))
LEFT = Alignment(horizontal="left")
RIGHT = Alignment(horizontal="right")

TRADE_SIDES = {"BUY": "Compra", "SELL": "Venda"}
INCOME_KINDS = {"DIVIDEND": "Dividendo", "JCP": "JCP", "OTHER": "Outro"}

POSITION_COLUMNS = (
    ("Ação", 12),
    ("Empresa", 38),
    ("Carteira", 22),
    ("Situação", 14),
    ("Quantidade", 12),
    ("Preço médio", 15),
    ("Cotação", 13),
    ("Valor investido", 16),
    ("Valor de mercado", 17),
    ("Valorização", 15),
    ("Valorização (%)", 16),
    ("Proventos", 14),
)
ASSET_WIDTHS = (13, 11, 12, 15, 15, 24, 11, 15)


def _local_date(moment: datetime) -> date:
    # SQLite devolve datetimes sem fuso; o banco grava em UTC.
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(BRT).date()


def _fraction(percentage: Decimal | None) -> Decimal | None:
    """O serviço devolve 12.50 para 12,5%; o Excel formata a partir de 0.125."""
    return percentage / 100 if percentage is not None else None


def _write(
    sheet: Worksheet,
    row: int,
    column: int,
    value: object,
    number_format: str | None = None,
    font: Font | None = None,
):
    if isinstance(value, str):
        # Nomes de corretora e carteira são digitados por usuários: caracteres de
        # controle invalidam o arquivo e "=" no início viraria fórmula.
        value = ILLEGAL_CHARACTERS_RE.sub("", value)
    cell = sheet.cell(row=row, column=column, value=value)
    if isinstance(value, str):
        cell.data_type = "s"
    if number_format:
        cell.number_format = number_format
    if font:
        cell.font = font
    return cell


def _write_header(
    sheet: Worksheet, row: int, titles: tuple[str, ...], numeric_columns: tuple[int, ...]
) -> None:
    for column, title in enumerate(titles, start=1):
        cell = _write(sheet, row, column, title, font=HEADER_FONT)
        cell.fill = HEADER_FILL
        cell.alignment = RIGHT if column in numeric_columns else LEFT


def _link(sheet: Worksheet, row: int, column: int, text: str, target_sheet: str, font=LINK_FONT):
    cell = _write(sheet, row, column, text, font=font)
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"{quote_sheetname(target_sheet)}!A1")
    return cell


@dataclass
class _Asset:
    stock_name: str
    company_name: str = ""
    portfolio_name: str | None = None
    trades: list[models.UserStock] = field(default_factory=list)
    incomes: list[models.Income] = field(default_factory=list)

    @property
    def income_total(self) -> Decimal:
        return sum((item.amount for item in self.incomes), Decimal("0"))


class ReportService:
    def __init__(
        self,
        investments: IInvestmentService,
        portfolios: IPortfolioService,
        incomes: IIncomeService,
        performance: IPerformanceService,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._investments = investments
        self._portfolios = portfolios
        self._incomes = incomes
        self._performance = performance
        self._now = now or (lambda: datetime.now(BRT))

    async def export_workbook(self, user_id: int, portfolio_id: int | None = None) -> bytes:
        portfolio = (
            self._portfolios.get_portfolio(user_id, portfolio_id)
            if portfolio_id is not None
            else None
        )
        priced, unavailable = await self._performance.evaluate_available(user_id, portfolio_id)
        assets = self._load_assets(user_id, portfolio_id)

        workbook = Workbook()
        workbook.properties.creator = "All Invest"
        workbook.properties.title = "Carteira de investimentos"
        summary = workbook.active
        summary.title = SUMMARY_SHEET
        positions = workbook.create_sheet(POSITIONS_SHEET)

        self._fill_summary(summary, portfolio, assets, priced, unavailable)
        self._fill_positions(positions, assets, priced, unavailable)
        for ticker in sorted(assets):
            self._fill_asset(workbook.create_sheet(ticker), assets[ticker])

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def _load_assets(self, user_id: int, portfolio_id: int | None) -> dict[str, _Asset]:
        portfolios_by_stock = self._portfolios.get_investment_portfolios(user_id)
        assets: dict[str, _Asset] = {}

        # As operações chegam da mais recente para a mais antiga.
        for trade in reversed(self._investments.list_trades(user_id)):
            portfolio = portfolios_by_stock.get(trade.stock_id)
            if portfolio_id is not None and getattr(portfolio, "portfolio_id", None) != portfolio_id:
                continue
            ticker = trade.stock.stock_name
            asset = assets.setdefault(
                ticker,
                _Asset(
                    ticker,
                    trade.stock.company_name,
                    portfolio.portfolio_name if portfolio else None,
                ),
            )
            asset.trades.append(trade)

        for income in reversed(self._incomes.list(user_id)):
            if income.stock_name in assets:
                assets[income.stock_name].incomes.append(income)
            elif portfolio_id is None:
                # Proventos continuam registrados depois de remover as operações do ativo.
                assets[income.stock_name] = _Asset(income.stock_name, incomes=[income])
        return assets

    def _fill_summary(
        self,
        sheet: Worksheet,
        portfolio: models.Portfolio | None,
        assets: dict[str, _Asset],
        priced: list[schemas.StockPerformanceOut],
        unavailable: list[schemas.PositionOut],
    ) -> None:
        invested = sum((item.invested_value for item in priced), Decimal("0.00"))
        market_value = sum((item.market_value for item in priced), Decimal("0.00"))
        gain = market_value - invested
        rate = gain / invested if invested > 0 else None
        income = sum((asset.income_total for asset in assets.values()), Decimal("0"))
        open_positions = len(priced) + len(unavailable)

        _write(sheet, 1, 1, "All Invest: resumo da carteira", font=TITLE_FONT)
        rows = (
            ("Carteira", portfolio.portfolio_name if portfolio else "Todas as posições", None),
            ("Gerado em", self._now().replace(tzinfo=None), DATETIME),
            ("Posições abertas", open_positions, QUANTITY),
            ("Ações encerradas", len(assets) - open_positions, QUANTITY),
            ("Valor investido", invested, MONEY),
            ("Valor de mercado", market_value, MONEY),
            ("Valorização", gain, MONEY),
            ("Valorização (%)", rate, PERCENT),
            ("Proventos registrados", income, MONEY),
        )
        for row, (label, value, number_format) in enumerate(rows, start=3):
            _write(sheet, row, 1, label, font=BOLD_FONT)
            _write(sheet, row, 2, value, number_format).alignment = LEFT

        notes = [
            "Valorização = valor de mercado - valor investido, nas posições abertas com cotação.",
            "Não inclui lucro de vendas realizadas, bonificações não lançadas, impostos e taxas.",
        ]
        if unavailable:
            tickers = ", ".join(sorted(item.stock_name for item in unavailable))
            notes.insert(0, f"Sem cotação no momento, fora dos totais: {tickers}.")
        for row, note in enumerate(notes, start=len(rows) + 4):
            _write(sheet, row, 1, note, font=NOTE_FONT)

        sheet.column_dimensions["A"].width = 26
        sheet.column_dimensions["B"].width = 24

    def _fill_positions(
        self,
        sheet: Worksheet,
        assets: dict[str, _Asset],
        priced: list[schemas.StockPerformanceOut],
        unavailable: list[schemas.PositionOut],
    ) -> None:
        priced_by_ticker = {item.stock_name: item for item in priced}
        unavailable_by_ticker = {item.stock_name: item for item in unavailable}

        _write_header(
            sheet,
            1,
            tuple(title for title, _ in POSITION_COLUMNS),
            numeric_columns=tuple(range(5, len(POSITION_COLUMNS) + 1)),
        )
        for column, (_, width) in enumerate(POSITION_COLUMNS, start=1):
            sheet.column_dimensions[get_column_letter(column)].width = width

        row = 1
        for ticker in sorted(assets):
            row += 1
            asset = assets[ticker]
            _link(sheet, row, 1, ticker, ticker)
            _write(sheet, row, 2, asset.company_name)
            _write(sheet, row, 3, asset.portfolio_name or "Sem carteira")
            _write(sheet, row, 12, asset.income_total, MONEY)

            performance = priced_by_ticker.get(ticker)
            position = performance or unavailable_by_ticker.get(ticker)
            if position is None:
                _write(sheet, row, 4, "Encerrada")
                _write(sheet, row, 5, 0, QUANTITY)
                continue
            _write(sheet, row, 5, position.stock_quantity, QUANTITY)
            _write(sheet, row, 6, position.preco_medio, PRICE)
            if performance is None:
                _write(sheet, row, 4, "Sem cotação")
                continue
            _write(sheet, row, 4, "Aberta")
            _write(sheet, row, 7, performance.current_price, PRICE)
            _write(sheet, row, 8, performance.invested_value, MONEY)
            _write(sheet, row, 9, performance.market_value, MONEY)
            _write(sheet, row, 10, performance.gain, MONEY)
            _write(sheet, row, 11, _fraction(performance.profitability_pct), PERCENT)

        last_column = get_column_letter(len(POSITION_COLUMNS))
        sheet.freeze_panes = "B2"
        sheet.auto_filter.ref = f"A1:{last_column}{row}"

        invested = sum((item.invested_value for item in priced), Decimal("0.00"))
        market_value = sum((item.market_value for item in priced), Decimal("0.00"))
        total = row + 1
        cells = [
            _write(sheet, total, 1, "Total"),
            _write(sheet, total, 8, invested, MONEY),
            _write(sheet, total, 9, market_value, MONEY),
            _write(sheet, total, 10, market_value - invested, MONEY),
            _write(
                sheet,
                total,
                11,
                (market_value - invested) / invested if invested > 0 else None,
                PERCENT,
            ),
            _write(
                sheet,
                total,
                12,
                sum((asset.income_total for asset in assets.values()), Decimal("0")),
                MONEY,
            ),
        ]
        for cell in cells:
            cell.font = BOLD_FONT
        for column in range(1, len(POSITION_COLUMNS) + 1):
            sheet.cell(row=total, column=column).border = TOTAL_BORDER

    def _fill_asset(self, sheet: Worksheet, asset: _Asset) -> None:
        for column, width in enumerate(ASSET_WIDTHS, start=1):
            sheet.column_dimensions[get_column_letter(column)].width = width

        title = f"{asset.stock_name}: {asset.company_name}" if asset.company_name else asset.stock_name
        _write(sheet, 1, 1, title, font=TITLE_FONT)
        _link(sheet, 2, 1, "Voltar às posições", POSITIONS_SHEET)

        _write(sheet, 4, 1, "Movimentações", font=SECTION_FONT)
        _write_header(
            sheet,
            5,
            ("Data", "Operação", "Quantidade", "Preço", "Total", "Corretora", "Saldo", "Preço médio"),
            numeric_columns=(3, 4, 5, 7, 8),
        )
        row = 5
        balance = 0
        cost_basis = Decimal("0")
        for trade in asset.trades:
            row += 1
            amount = trade.stock_price * trade.stock_quantity
            # Mesma regra de IInvestmentService.get_positions: a venda não altera o preço médio.
            if trade.trade_side == "BUY":
                balance += trade.stock_quantity
                cost_basis += amount
            elif balance:
                average = cost_basis / balance
                balance -= trade.stock_quantity
                cost_basis -= average * trade.stock_quantity

            _write(sheet, row, 1, _local_date(trade.trade_date), DATE).alignment = LEFT
            _write(sheet, row, 2, TRADE_SIDES[trade.trade_side])
            _write(sheet, row, 3, trade.stock_quantity, QUANTITY)
            _write(sheet, row, 4, trade.stock_price, PRICE)
            _write(sheet, row, 5, amount, MONEY)
            _write(sheet, row, 6, trade.broker.broker_name)
            _write(sheet, row, 7, balance, QUANTITY)
            if balance > 0:
                _write(sheet, row, 8, (cost_basis / balance).quantize(Decimal("0.0001")), PRICE)
        if not asset.trades:
            row += 1
            _write(sheet, row, 1, "Nenhuma movimentação registrada.", font=NOTE_FONT)

        row += 2
        _write(sheet, row, 1, "Proventos", font=SECTION_FONT)
        if not asset.incomes:
            _write(sheet, row + 1, 1, "Nenhum provento registrado.", font=NOTE_FONT)
            return
        row += 1
        _write_header(sheet, row, ("Data", "Tipo", "Valor"), numeric_columns=(3,))
        for income in asset.incomes:
            row += 1
            _write(sheet, row, 1, _local_date(income.received_at), DATE).alignment = LEFT
            _write(sheet, row, 2, INCOME_KINDS.get(income.kind, income.kind))
            _write(sheet, row, 3, income.amount, MONEY)
        row += 1
        _write(sheet, row, 2, "Total", font=BOLD_FONT)
        _write(sheet, row, 3, asset.income_total, MONEY, font=BOLD_FONT)
