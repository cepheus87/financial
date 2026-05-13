from collections import defaultdict
from copy import deepcopy
from datetime import date
from typing import List, Tuple, Dict

from fx_data import FXData
# from taxes import trades

from reckoning_rules import ReckoningRules, ReckoningRulesConfig
from trades import Statements, TradeEntry

class CalculateIncome:
    SELL_INDICATORS = ["C"]


    def __init__(self, statement_path: str):
        self.statements = Statements(statement_path)
        self.trades = self.statements.split_statement_into_trade_entries()

        self.reckoning_rules = ReckoningRules(ReckoningRulesConfig())
        self._fx_data = FXData([str(date.today().year - 1)])  # load previous year

    def calculate_income_costs(self, symbol: str) -> Tuple[Dict[str, List], Dict[str, List]]:
        all_trades = deepcopy(self.trades)
        trades_symbol = all_trades[symbol]

        income, costs = defaultdict(list), defaultdict(list)

        if self.check_if_sold(trades_symbol):
            sell_entries = self.get_sell_entries(trades_symbol)

            for sell in sell_entries:
                sell_symbol = sell.symbol
                previous_buys = [entry for entry in trades_symbol if entry < sell]
                used_buys, last_entry = self.get_fifo_buys(sell, previous_buys)

                if last_entry is not None:
                    raise NotImplementedError("Partial use of buy entry not implemented yet")

                for buy in used_buys:
                    fx_calc_date = self.reckoning_rules.get_day_of_fx_calculation(buy.date.date())
                    self._fx_data.add_year(str(fx_calc_date.year))
                    fx_value = self._fx_data.get_fx_value(str(fx_calc_date), buy.currency)
                    costs[sell_symbol].append((buy.amount * buy.price + buy.commission) * fx_value)


                fx_calc_date = self.reckoning_rules.get_day_of_fx_calculation(sell.date.date())
                self._fx_data.add_year(str(fx_calc_date.year))
                fx_value = self._fx_data.get_fx_value(str(fx_calc_date), sell.currency)
                income[sell_symbol].append((sell.amount * sell.price - sell.commission) * fx_value)

                all_trades.remove_trades(symbol, used_buys)
                all_trades.remove_trades(symbol, [sell])

        return income, costs

    @staticmethod
    def get_fifo_buys(sell: TradeEntry, previous_buys: List[TradeEntry]) -> Tuple[List[TradeEntry],
    TradeEntry | None]:
        """

        Args:
            sell:
            previous_buys:

        Returns: List of used previous buy entries as FIFO list and Last used "buy entry" if not used completely

        """

        if sell.amount > sum([entry.amount for entry in previous_buys]):
            raise RuntimeError("Try to sell more than available")

        used_buys = []
        for entry in previous_buys:
            if sum([ub.amount for ub in used_buys]) < sell.amount:
                used_buys.append(entry)

        if sum([ub.amount for ub in used_buys]) == sell.amount:
            return used_buys, None
        else:
            return used_buys, used_buys[-1]


    @classmethod
    def check_if_sold(cls, trades: List[TradeEntry]) -> bool:
        if len (cls.get_sell_entries(trades)) > 0:
            return True
        return False

    @classmethod
    def get_sell_entries(cls, trades: List[TradeEntry]):
        sell_entries = []
        for trade in trades:
            t_types = trade.entry_type.split(";")
            for t in t_types:
                if t in cls.SELL_INDICATORS:
                    sell_entries.append(trade)
        return sell_entries

def main():
    url2 = "https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_2025.csv"

    url = "https://nbp.pl/statystyka-i-sprawozdawczosc/kursy/archiwum-tabela-a-csv-xls/"

    # text = fetch_website_text(url)

    # get_binary_response(url2, "./archiwum_tab_a_2025.csv")

    # statements = Statements("statements.csv")
    # trades = statements.split_statement_into_trade_entries()

    # fx = FXData(["2023", "2025"])
    # print(fx.year_urls)

    # df = fx.get_data("2023")

    # data = fx.data

    # fx_val = fx.get_fx_value("2025-12-02", "USD")

    calculator = CalculateIncome("statements.csv")
    income, costs = calculator.calculate_income_costs("4GLD")

    for symbol, income_vals in income.items():
        print(f"Income: for {symbol}: {sum(income_vals)} PLN")
    for symbol, costs_vals in costs.items():
        print(f"Costs: for {symbol}: {sum(costs_vals)} PLN")

    a = 1


if __name__ == "__main__":
    main()