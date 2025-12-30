import argparse
import math

def get_entry_values(full_cost: float, commission: float, price_in_currency: float, units: float, sell: bool):

    """
    Calculate the entry values for an investment.

    Parameters:
    - full_cost: The full cost of the investment.
    - commission: The commission in value (PLN) or percentage (decimal).
    - price_in_currency: The price of a single unit in the original currency.
    - units: The number of assets.
    - sell: Boolean indicating if the operation is a sell.

    """


    if sell:
        commission = 0.00522
        currency_rate = full_cost / (units * price_in_currency)
        commission_in_PLN = get_commision_value(commission, full_cost)
        # commission_in_PLN = commission * (cost_no_commission * (1 + commission))
    else:
        if commission < 1:
            # cost_no_commission = full_cost / (1 + commission)
            commission_in_PLN = get_commision_value(commission, full_cost)

        else:
            # cost_no_commission = full_cost - commission
            commission_in_PLN = commission

        currency_rate = full_cost / (units * price_in_currency)

    print(f"Currency rate: {currency_rate:.5f}")
    print(f"Commission PLN: {commission_in_PLN:.2f}")

def get_commision_value(commission: float, full_cost: float):
    commission_in_PLN = math.ceil(commission * full_cost * 100) / 100
    return commission_in_PLN

if __name__ == "__main__":


    parser = argparse.ArgumentParser()
    parser.add_argument("-fc", "--full-cost", type=float, required=True, help="Full cost in PLN")
    parser.add_argument("-c", "--commission", type=float, required=False, default=0.00516, help="Commission in value (PLN) or percentage (decimal)")
    parser.add_argument("-pic", "--price-in-currency", type=float, required=True, help="Price of single unit in "
                                                                                      "original "
                                                                               "currency")
    parser.add_argument("-u", "--units", type=float, required=True, help="Units of assets")
    parser.add_argument("-s", "--sell", action="store_true", help="Indicate if the operation is a sell")
    args = parser.parse_args()

    get_entry_values(args.full_cost, args.commission, args.price_in_currency, args.units, args.sell)