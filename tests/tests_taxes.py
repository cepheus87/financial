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

#TODO

"""
Tests for
 * fx date selection based on currency
  * merging many statement files
"""



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

