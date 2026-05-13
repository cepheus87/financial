import os.path
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
    entry_type: str
    amount: float
    price: float
    currency: str
    commission: float

    @property
    def year(self) -> str:
        return str(self.date.year)

    def __eq__(self, other) -> bool:
        conds = [self.symbol == other.symbol, self.entry_type == other.entry_type,
                 self.amount == other.amount,
                 self.price == other.price, self.date == other.date]

        if not all(conds):
            return False
        return True

    def problem(self, other):
        #TODO: not 24 clock in ibkr statement
        if self.date.date() == other.date.date() and self != other:
            raise NotImplementedError("Few trades in the same day for ibkr")


    def __lt__(self, other) -> bool:
        self.problem(other)
        return self.date < other.date


    def __gt__(self, other) -> bool:
        self.problem(other)
        return self.date > other.date


class Trades:

    def __init__(self):
        self._trades = defaultdict(list)

    def __getitem__(self, symbol: str):
        trades_symbol = self._trades.get(symbol)
        if trades_symbol is None:
            raise KeyError(f"Trade symbol not found: {symbol} in data")
        return trades_symbol

    def add_trade(self, symbol: str, trade_data: TradeEntry):
        self._trades[symbol].append(trade_data)

    def sort_trades_by_date(self):
        for symbol in self._trades:
            self._trades[symbol].sort(key=lambda trade: trade.date)

    def remove_trades(self, symbol: str, trades_to_remove: list[TradeEntry]):
        if symbol not in self._trades:
            raise KeyError(f"Trade symbol not found: {symbol} in data")

        to_remove_idx = []
        for trade in trades_to_remove:
            for i, tr in enumerate(self._trades[symbol]):
                if trade == tr:
                    to_remove_idx.append(i)
                    break

        if len(to_remove_idx) != len(trades_to_remove):
            raise ValueError(f"Not all trade entry were found to remove for symbol {symbol}")
        else:
            for i in reversed(to_remove_idx):
                del self._trades[symbol][i]






class Statements:
    def __init__(self, statement_path: str):
        self._statement_path = statement_path
        self._statement_txt = self._read_statement()
        self._trades = Trades()

    @property
    def trades(self) -> Trades:
        return deepcopy(self._trades)

    def _read_statement(self):
        if not os.path.exists(self._statement_path):
            raise FileNotFoundError(f"State file not found: {self._statement_path}")
        with open(self._statement_path, "r") as f:
            txt = f.readlines()

        return txt

    def split_statement_into_trade_entries(self) -> Trades:
        for line in self._statement_txt:
            if line.startswith("Trades,Data,Order,Stocks"):
                data = line.strip().split(",")
                symbol = data[5]
                #TODO: problem with not 24h clock from ibkr
                date = datetime.strptime(f"{data[6][1:]}_{data[7][:-1].strip()}", "%Y-%m-%d_%H:%M:%S")
                entry_type = data[-1]
                amount = abs(float(data[8]))
                price = float(data[9])
                currency = data[4]
                commission = abs(float(data[12]))

                trade_entry = TradeEntry(symbol=symbol, date=date, entry_type=entry_type, amount=amount,
                                         price=price, currency=currency, commission=commission)

                self._trades.add_trade(symbol, trade_entry)
        self._trades.sort_trades_by_date()

        return self.trades
