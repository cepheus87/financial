import argparse

from utils import calculate_compound_interest_yearly


def main(args: argparse.Namespace):
    total_amounts, compound_interests = calculate_compound_interest_yearly(args.principal, args.rate, args.time, args.n)

    print(f"Total Amounts: {total_amounts}")
    print(f"Compound Interests: {compound_interests}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate compound interest.")
    parser.add_argument("-p", "--principal", type=float, required=True, help="Initial amount of money (P)")
    parser.add_argument("-r", "--rate", type=float, required=True, help="Annual interest rate (as a decimal)")
    parser.add_argument("-t", "--time", type=float, required=True, help="Time in years")
    parser.add_argument("-n", "--n", type=int, default=1, help="Number of times interest is compounded per year")

    args = parser.parse_args()

    main(args)

