from datetime import date
import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from taxes.calculate_income import CalculateIncome
from taxes.reckoning_rules import ReckoningRules, ReckoningRulesConfig


def example_statement(symbol, currency, year= "2026", sell_amount = "8" ):
    statement = f"""
Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
Trades,Data,Order,Stocks,{currency},{symbol},"{year}-01-28, 08:33:42",2,141.8399,142.36,-283.6798,-1.25,284.9298,0,1.0402,O
Trades,Data,Order,Stocks,{currency},{symbol},"{year}-01-30, 03:50:43",2,137.8795,134.41,-275.76,-1.25,277.01,0,-6.94,O
Trades,Data,Order,Stocks,{currency},{symbol},"{year}-02-02, 08:00:01",2,129.95,127.06,-259.9,-1.2914356,261.1914356,0,-5.78,O
Trades,Data,Order,Stocks,{currency},{symbol},"{year}-02-17, 05:08:54",2,133.749,132.54,-267.498,-1.25,268.748,0,-2.418,O
Trades,Data,Order,Stocks,{currency},{symbol},"{year}-03-20, 04:34:51",-{sell_amount},130.8,127.55,1046.4,-1.3860416,-1091.879236,-46.865276,26,C;P
    """
    return statement



@pytest.mark.parametrize("symbol, currency, sell_amount, expected_used_buys, expected_rest_amount",
                         [
                             ("4GLD", "USD", "7", 4, 1),
                             ("XDEB", "EUR", "8", 4, None),
                             ("XDEB", "EUR", "6", 3, None),
                             ("XDEB", "EUR", "5", 3, 1)
                          ]
                         )
def test_selling_amount(symbol, currency, sell_amount, expected_used_buys, expected_rest_amount):
    year = "2026"

    with tempfile.TemporaryDirectory() as tmpdirname:
        csv_path = os.path.join(tmpdirname, "statement.csv")
        with open(csv_path, "w") as f:
            f.write(example_statement(symbol, currency, year,  sell_amount=sell_amount))

        with patch("taxes.trades.check_ibkr_statement_format", lambda row: None):
            calc_inc = CalculateIncome(csv_path)

            trades = calc_inc.trades[symbol]
            sell_entries = calc_inc.get_sell_entries(trades, year)
            assert len(sell_entries) == 1

            #TODO replace with function call after splitting previous buys selection into function
            previous_buys = [entry for entry in trades if entry < sell_entries[0]]
            used_buys, rest = calc_inc.get_fifo_buys(sell_entries[0], previous_buys)
            assert len(used_buys) == expected_used_buys
            if rest:
                assert rest.amount == expected_rest_amount


def test_statement_merge():
    year1 = "2025"
    year2 = "2026"

    symbol = "4GLD"
    currency = "EUR"
    sell_amount = "7"

    with tempfile.TemporaryDirectory() as tmpdirname:
        csv_path1 = os.path.join(tmpdirname, "statement1.csv")
        with open(csv_path1, "w") as f:
            f.write(example_statement(symbol, currency, year1,  sell_amount=sell_amount))

        csv_path2 = os.path.join(tmpdirname, "statement2.csv")
        with open(csv_path2, "w") as f:
            f.write(example_statement(symbol, currency, year2, sell_amount=sell_amount))

        with patch("taxes.trades.check_ibkr_statement_format", lambda row: None):
            calc_inc = CalculateIncome([csv_path2, csv_path1])

            trades = calc_inc.trades[symbol]

            # check sorting
            assert trades[0].date.year == int(year1)
            assert trades[-1].date.year == int(year2)

            assert len(trades) == 10

            sell_entries = calc_inc.get_sell_entries(trades, year1)
            assert len(sell_entries) == 1
            assert sell_entries[0].date.year == int(year1)

            sell_entries = calc_inc.get_sell_entries(trades, year2)
            assert len(sell_entries) == 1
            assert sell_entries[0].date.year == int(year2)


@pytest.mark.parametrize("currency, sell_date, days_of_reckoning_by_stock, fx_calculation_day, expected_date",
                         [
                             # normal
                             ("USD", date(2026, 5, 26), 2, 1, date(2026, 5, 27)),
                             ("EUR", date(2026, 5, 26), 2, 1, date(2026, 5, 27)),
                             ("PLN", date(2026, 5, 26), 2, 1, date(2026, 5, 27)),
                             ("GBP", date(2026, 5, 26), 2, 1, date(2026, 5, 27)),
                             ("USD", date(2026, 5, 26), 1, 1, date(2026, 5, 26)),
                             ("EUR", date(2026, 5, 26), 1, 1, date(2026, 5, 26)),
                             ("PLN", date(2026, 5, 26), 1, 1, date(2026, 5, 26)),
                             ("GBP", date(2026, 5, 26), 1, 1, date(2026, 5, 26)),
                             ("USD", date(2026, 5, 26), 2, 0, date(2026, 5, 28)),
                             ("EUR", date(2026, 5, 26), 2, 0, date(2026, 5, 28)),
                             ("PLN", date(2026, 5, 26), 2, 0, date(2026, 5, 28)),
                             ("GBP", date(2026, 5, 26), 2, 0, date(2026, 5, 28)),
                             # weekend
                             ("USD", date(2026, 5, 15), 2, 1, date(2026, 5, 15)),
                             ("EUR", date(2026, 5, 15), 2, 1, date(2026, 5, 15)),
                             ("PLN", date(2026, 5, 15), 2, 1, date(2026, 5, 15)),
                             ("GBP", date(2026, 5, 15), 2, 1, date(2026, 5, 15)),
                             # holiday in Poland 2026-6-4
                             ("USD", date(2026, 6, 3), 2, 1, date(2026, 6, 3)),
                             ("EUR", date(2026, 6, 3), 2, 1, date(2026, 6, 3)),
                             ("GBP", date(2026, 6, 3), 2, 1, date(2026, 6, 3)),
                             ("PLN", date(2026, 6, 3), 2, 1, date(2026, 6, 3)),
                             # holiday in Germany 2026-5-1, 2026-12-24
                             ("EUR", date(2026, 4, 29), 2, 1, date(2026, 4, 30)),
                             ("EUR", date(2026, 12, 22), 2, 1, date(2026, 12, 23)),
                             ("USD", date(2026, 12, 22), 2, 1, date(2026, 12, 23)),
                             # # holiday in UK 2025-05-04
                             ("USD", date(2026, 4, 30), 2, 1, date(2026, 5, 4)),
                             ("GBP", date(2026, 4, 30), 2, 1, date(2026, 5, 4)),
                             ("EUR", date(2026, 4, 30), 2, 1, date(2026, 4, 30)),
                          ]
                         )
def test_fx_calc_date(currency, sell_date, days_of_reckoning_by_stock, fx_calculation_day, expected_date):
    rec_rules_conf = ReckoningRulesConfig(days_of_reckoning_by_stock=days_of_reckoning_by_stock,
                                          fx_calculation_day=fx_calculation_day)
    reckoning_rules = ReckoningRules(rec_rules_conf)

    calc_date = reckoning_rules.get_day_of_fx_calculation(sell_date, currency)
    assert calc_date == expected_date

