import argparse
from argparse import ArgumentParser
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


    def __init__(self, statement_paths: str | List[str]):
        if isinstance(statement_paths, str):
            self.statements = [Statements(statement_paths)]
        elif isinstance(statement_paths, list):
            self.statements = [Statements(statement_path) for statement_path in statement_paths]
        else:
            raise TypeError("statement_paths must be a string or list of strings")

        self.trades = self.statements[0].split_statement_into_trade_entries()
        self.trades.merge_trades([statement.split_statement_into_trade_entries() for statement in self.statements[1:]])

        self.reckoning_rules = ReckoningRules(ReckoningRulesConfig())
        self._fx_data = FXData([str(date.today().year - 1)])  # load previous year

    def calculate_income_costs(self, tax_year: str, entity_symbol: str | None = None) -> Tuple[Dict[str, List],
    Dict[str, List]]:
        """

        Args:
            tax_year: year to calculate income and costs for, only trades with sell entries in this year will be used
            entity_symbol:  selected entity symbol if given, otherwise all entities with sell entries are used

        Returns: income and costs of all trades entries used during selling as dicts divided by entity symbol

        """

        all_trades = deepcopy(self.trades)

        if entity_symbol is None:
            entity_symbol = all_trades.get_all_symbols()
        else:
            entity_symbol = [entity_symbol]

        income, costs = defaultdict(list), defaultdict(list)

        for symbol in entity_symbol:
            trades_symbol = all_trades[symbol]

            if self.check_if_sold(trades_symbol, tax_year):
                sell_entries = self.get_sell_entries(trades_symbol, tax_year)

                for sell in sell_entries:
                    sell_symbol = sell.symbol
                    # choosing entries that will be sold by FIFO order
                    previous_buys = [entry for entry in trades_symbol if entry < sell]
                    used_buys, rest = self.get_fifo_buys(sell, previous_buys)



                    # calculating day of fx_value that must be used for buy entries
                    for buy in used_buys:
                        fx_calc_date = self.reckoning_rules.get_day_of_fx_calculation(buy.date.date(), buy.currency)
                        self._fx_data.add_year(str(fx_calc_date.year))
                        fx_value = self._fx_data.get_fx_value(str(fx_calc_date), buy.currency)
                        costs[sell_symbol].append((buy.amount * buy.price + buy.commission) * fx_value)

                    # calculating day of fx_value that must be used for sell entries
                    fx_calc_date = self.reckoning_rules.get_day_of_fx_calculation(sell.date.date(), sell.currency)
                    self._fx_data.add_year(str(fx_calc_date.year))
                    fx_value = self._fx_data.get_fx_value(str(fx_calc_date), sell.currency)
                    income[sell_symbol].append((sell.amount * sell.price - sell.commission) * fx_value)

                    all_trades.remove_trades(symbol, used_buys)
                    all_trades.remove_trades(symbol, [sell])
                    if rest is not None:
                        all_trades.add_trade(symbol, rest)
                        all_trades.sort_trades_by_date(symbol)


        return income, costs

    @staticmethod
    def get_fifo_buys(sell: TradeEntry, previous_buys: List[TradeEntry]) -> Tuple[List[TradeEntry],
    TradeEntry | None]:
        """
        Function selects buy entries that will be used to realize sell entry by FIFO order

        Args:
            sell: entry that define sell transaction
            previous_buys: all available buy entries (buy transactions realized before sell date)

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
            rest = deepcopy(used_buys[-1])
            rest.amount = sum([ub.amount for ub in used_buys]) - sell.amount
            return used_buys, rest


    @classmethod
    def check_if_sold(cls, trades: List[TradeEntry], tax_year: str) -> bool:
        if len (cls.get_sell_entries(trades, tax_year)) > 0:
            return True
        return False

    @classmethod
    def get_sell_entries(cls, trades: List[TradeEntry], tax_year: str) -> List[TradeEntry]:
        sell_entries = []
        for trade in trades:
            if trade.year == tax_year:
                t_types = trade.entry_type.split(";")
                for t in t_types:
                    if t in cls.SELL_INDICATORS:
                        sell_entries.append(trade)
        return sell_entries

def main(statement_paths: List[str], tax_year: str, entity_symbol: str = None):

    tax_year = tax_year.strip()

    calculator = CalculateIncome(statement_paths)
    income, costs = calculator.calculate_income_costs(tax_year, entity_symbol)

    for symbol, income_vals in income.items():
        print(f"Income: for {symbol}: {sum(income_vals)} PLN")
    for symbol, costs_vals in costs.items():
        print(f"Costs: for {symbol}: {sum(costs_vals)} PLN")


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--statement-paths", type=str, nargs="+", required=True, help="Paths to statement files (csv)")
    parser.add_argument("--entity-symbol", type=str, default=None, help="Entity symbol to calculate income and costs "
                                                                         "for (default: all entities)")
    parser.add_argument("--tax-year", type=str, required=True, help="Tax year to calculate income and costs for")
    return parser.parse_args()


if __name__ == "__main__":
    parsed_args = parse_arguments()
    main(**vars(parsed_args))