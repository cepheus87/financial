import argparse

def get_entry_values(full_cost: float, commission: float, price_in_currency: float, units: float):

    """
    Calculate the entry values for an investment.

    Parameters:
    - full_cost: The full cost of the investment.
    - commission: The commission in value (PLN) or percentage (decimal).
    - price_in_currency: The price of a single unit in the original currency.
    - units: The number of assets.

    """



    if commission < 1:
        cost_no_commission = full_cost / (1 + commission)
        commission_in_PLN = full_cost * commission
    else:
        cost_no_commission = full_cost - commission
        commission_in_PLN = commission

    currency_rate = cost_no_commission / (units * price_in_currency)

    print(f"Currency rate: {currency_rate:.5f}")
    print(f"Commission PLN: {commission_in_PLN:.5f}")


if __name__ == "__main__":


    parser = argparse.ArgumentParser()
    parser.add_argument("-fc", "--full-cost", type=float, required=True, help="Full cost in PLN")
    parser.add_argument("-c", "--commission", type=float, required=True, help="Commission in value (PLN) or "
                                                                              "percentage ("
                                                                        "decimal)")
    parser.add_argument("-pic", "--price-in-currency", type=float, required=True, help="Price of single unit in "
                                                                                      "original "
                                                                               "currency")
    parser.add_argument("-u", "--units", type=float, required=True, help="Units of assets")
    args = parser.parse_args()

    get_entry_values(args.full_cost, args.commission, args.price_in_currency, args.units)