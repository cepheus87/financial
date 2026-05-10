from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime


# Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
# Trades,Data,Order,Stocks,EUR,XDEB,"2026-01-26, 08:21:01",51,41.79,41.85,-2131.29,-1.36377676,2132.65377676,0,3.06,O


@dataclass
class TradeEntry:
    symbol: str
    date: datetime
    type: str
    amount: float
    price: float
    currency: str
    commission: float

    @property
    def year(self) -> str:
        return str(self.date.year)


class Trades:

    def __init__(self):
        self._trades = defaultdict(list)

    def add_trade(self, symbol: str, trade_data: TradeEntry):
        self._trades[symbol].append(trade_data)

    def sort_trades_by_date(self):
        for symbol in self._trades:
            self._trades[symbol].sort(key=lambda trade: trade.date)


class Statements:
    def __init__(self, statement_path: str):
        self._statement_path = statement_path
        self._statement_txt = self._read_statement()
        self._trades = Trades()

    @property
    def trades(self) -> Trades:
        return deepcopy(self._trades)

    def _read_statement(self):
        with open(self._statement_path, "r") as f:
            txt = f.readlines()

        return txt

    def split_statement_into_trade_entries(self) -> Trades:
        for line in self._statement_txt:
            if line.startswith("Trades,Data,Order,Stocks"):
                data = line.strip().split(",")
                symbol = data[5]
                date = datetime.strptime(data[6][1:], "%Y-%m-%d")
                type = data[-1]
                amount = float(data[8])
                price = float(data[9])
                currency = data[4]
                commission = float(data[12])

                trade_entry = TradeEntry(symbol=symbol, date=date, type=type, amount=amount,
                                         price=price, currency=currency, commission=commission)

                self.trades.add_trade(symbol, trade_entry)
        self.trades.sort_trades_by_date()

        return self.trades
