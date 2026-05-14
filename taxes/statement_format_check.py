import datetime

# Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
# Trades,Data,Order,Stocks,EUR,XDEB,"2026-01-26, 08:21:01",51,41.79,41.85,-2131.29,-1.36377676,2132.65377676,0,3.06,O

DEFAULT_ROW_EXAMPLE_IBKR = ('Trades,Data,Order,Stocks,EUR,XDEB,"2026-01-26, 08:21:01",51,41.79,41.85,-2131.29,'
                          '-1.36377676132.65377676,0,3.06,O')

PRECISION = 0.01

def check_ibkr_statement_format(row: str):

    row_split = row.split(',')
    assert len(row_split) == 17

    assert ",".join(row_split[:4]) == "Trades,Data,Order,Stocks"

    assert row_split[4] in ["EUR", "USD", "GBP", "PLN"]

    assert row_split[6].startswith('"')
    assert row_split[7].endswith('"')
    assert datetime.datetime.strptime(f"{row_split[6][1:]} {row_split[7][:-1]}", "%Y-%m-%d %H:%M:%S")
    assert float(row_split[8])
    assert float(row_split[9])
    assert float(row_split[10])
    assert float(row_split[11])
    assert float(row_split[12])

    assert abs(abs(float(row_split[8]) * float(row_split[9])) - abs(float(row_split[11]))) < PRECISION
    assert abs(float(row_split[12])) < 10  # assumes not to big commission
    assert abs((float(row_split[9]) - (float(row_split[10])) ) / float(row_split[9])) < 0.15  # close price should be
    # close to trade price

    try:
        int(row_split[-1])
        assert False, "Expected ValueError for last row entry"
    except ValueError:
        pass  # Test passes


if __name__ == "__main__":
    check_ibkr_statement_format(DEFAULT_ROW_EXAMPLE_IBKR)