import argparse
import matplotlib.pyplot as plt

from bonds import anti_inflation_bond

# def draw_graph(
def draw_graph_total_amount(total_amounts1: list, total_amounts2: list):
    print(total_amounts1[-1], total_amounts2[-1])

    years = list(range(1, len(total_amounts1) + 1))
    plt.plot(years, total_amounts1, label='Total Amounts (Bond 1)')
    plt.plot(years, total_amounts2, label='Total Amounts (Bond 2)')
    plt.xlabel('Years')
    plt.ylabel('Amount')
    plt.title('Total Amounts and Compound Interests Over Time')
    plt.legend()
    plt.show()



def draw_graph_compound_interest(compound_interests1: list, compound_interests2: list):
    print(compound_interests1[-1], compound_interests2[-1])

    years = list(range(1, len(compound_interests1) + 1))
    plt.plot( years, compound_interests1, label='Compound Interests (Bond 1)')
    plt.plot( years, compound_interests2, label='Compound Interests (Bond 2)')
    plt.xlabel('Years')
    plt.ylabel('Amount')
    plt.title('Total Amounts and Compound Interests Over Time')
    plt.legend()
    plt.show()



def main(args: argparse.Namespace):
    # total_amounts, compound_interests = calculate_compound_interest_yearly(args.principal, args.rate, args.time, args.n)

    # TODO: handle penalty properly depending on withdraw time and time to maturity of bond
    total_amounts, compound_interests = anti_inflation_bond(args.principal, args.first_year_rate, args.coupon,
                                                            args.assumed_inflation, args.time, args.n, penalty=3)

    total_amounts2, compound_interests2 = anti_inflation_bond(args.principal, args.first_year_rate - 0.003,
                                                              args.coupon - 0.005,
                                                            args.assumed_inflation, args.time, args.n, penalty=2)

    draw_graph_compound_interest(compound_interests, compound_interests2)

    print(f"Total Amounts: {total_amounts}")
    print(f"Compound Interests: {compound_interests}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate compound interest.")
    parser.add_argument("-p", "--principal", type=float, required=True, help="Initial amount of money (P)")
    parser.add_argument("-fyr", "--first-year-rate", type=float, required=True, help="First year interest rate (as a "
                                                                                   "decimal)")
    parser.add_argument("-c", "--coupon", type=float, required=True, help="Coupon rate (as a decimal)")
    parser.add_argument("-i", "--assumed-inflation", type=float, required=True, help="Assumed inflation rate (as a decimal)")
    parser.add_argument("-t", "--time", type=float, required=True, help="Time in years")
    parser.add_argument("-n", "--n", type=int, default=1, help="Number of times interest is compounded per year")

    args = parser.parse_args()

    main(args)

