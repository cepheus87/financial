import argparse
import pandas as pd

from record_entry import get_entry_values, COMMISION_RATE


def run(args: argparse.Namespace):
    df = pd.read_csv(args.path)

    for index, row in df.iterrows():
        full_cost = row['full_cost']
        price_in_currency = row['price_in_currency']
        units = row['units']

        sell = True if row["type"].lower() == "sell" else False

        currency_rate, _ = get_entry_values(full_cost, COMMISION_RATE, price_in_currency, units, sell=sell)
        format_output(currency_rate, row)

def format_output(currency_rate: float, row: pd.Series):
    msg = (f"Entry: {row['data']} "
           f"{row['account']} {row['type'].lower()}| Name: {row['name']} | Units: {row['units']} | Full "
           f"Cost:"
           f" {row['full_cost']} PLN | Price in Currency:"
           f" {row['price_in_currency']}  | Currency Rate: {currency_rate:.5f} | Currency: {row['currency']}")

    print(msg)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run entries recording process.")
    parser.add_argument("--path", required=True, help="Path to csv file with entries.")

    args = parser.parse_args()

    run(args)