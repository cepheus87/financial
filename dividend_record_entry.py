import argparse

def get_dividends_entry_values(dividend_payment: float, dividend_in_currency: float, commission: float,
                               units: float, taxes: bool):

    """
    Calculate the entry values for a dividend payment.

    Parameters:
    :param dividend_payment: The total dividend payment in PLN.
    :param dividend_in_currency: The dividend payment for a single unit in the original currency.
    :param commission: The commission in percentage (decimal) if applied.
    :param units: The number of assets.
    :param taxes: Boolean indicating if taxes are applied to the dividend payment.

    """


    if taxes:
        dividend_for_unit = dividend_payment / ((1 - commission) * units)
        currency_rate = dividend_for_unit / dividend_in_currency
        commission_in_PLN = commission * (dividend_payment / (1 - commission))
    else:
        dividend_for_unit = dividend_payment / units
        currency_rate = dividend_for_unit / dividend_in_currency
        commission_in_PLN = 0

    print(f"Currency rate: {currency_rate:.5f}")
    print(f"Commission PLN: {commission_in_PLN:.5f}")


if __name__ == "__main__":


    parser = argparse.ArgumentParser()
    parser.add_argument("-dp", "--dividend-payment", type=float, required=True, help="Dividend in PLN")
    parser.add_argument("-dic", "--dividend-in-currency", type=float, required=True,
                        help="Dividend payment for single unit in original currency")
    parser.add_argument("-u", "--units", type=float, required=True, help="Units of assets")
    parser.add_argument( "--taxes", action="store_true", help="Indicate if taxes are applied to the dividend payment")
    parser.add_argument("-c", "--commission", type=float, default=0, help="Commission in percentage (decimal)")

    args = parser.parse_args()

    get_dividends_entry_values(**(vars(args)))