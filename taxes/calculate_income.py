from copy import deepcopy
from typing import List, Tuple

# from fx_data import FXData
# from taxes import trades

from reconing_rules import ReckoningRules, ReckoningRulesConfig
from trades import Statements, TradeEntry

class CalculateIncome:
    SELL_INDICATORS = ["C"]


    def __init__(self, statement_path: str):
        self.statements = Statements(statement_path)
        self.trades = self.statements.split_statement_into_trade_entries()

        self.reckoning_rules = ReckoningRules(ReckoningRulesConfig())
        self._fx_data = None

    def calculate_income_costs(self, symbol: str):
        all_trades = deepcopy(self.trades)
        trades_symbol = all_trades[symbol]

        income, costs = [], []

        if self.check_if_sold(trades_symbol):
            sell_entries = self.get_sell_entries(trades_symbol)

            for sell in sell_entries:
                previous_buys = [entry for entry in trades_symbol if entry < sell]
                used_buys, last_entry = self.get_fifo_buys(sell, previous_buys)

                if last_entry is not None:
                    raise NotImplementedError("Partial use of buy entry not implemented yet")

                #TODO: not tested yet
                # do fx calc, income calc
                #  fx_calculation_date = self.reckoning_rules.get_day_of_fx_calculation()

                all_trades.remove_trades(symbol, used_buys)
                all_trades.remove_trades(symbol, sell)


            #TODO: Finished here, implement getting fx_value and income calculation

        a = 1

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
            t_types = trade.type.split(";")
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
    calculator.calculate_income_costs("4GLD")

    a = 1


if __name__ == "__main__":
    main()