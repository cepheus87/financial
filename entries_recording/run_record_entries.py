import argparse
from contextlib import redirect_stdout
import io
import pandas as pd
from typing import Optional

from record_entry import get_entry_values, COMMISION_RATE

DIVIDEND = "div"
PAYMENT = "pay"
SELL = "sell"

def run(args: argparse.Namespace):

    f = io.StringIO()

    df = pd.read_csv(args.path)
    df = postprocess_floats(df)

    for index, row in df.iterrows():
        full_cost = row['full_cost']
        price_in_currency = row['price_in_currency']
        units = row['units']

        sell = True if row["type"].lower() == SELL else False

        if DIVIDEND in row["type"].lower():
            currency_rate = 0.0
            format_output(currency_rate, row, full_cost_name="dividend")
        elif PAYMENT in row["type"].lower():
            currency_rate = 0.0
            format_output(currency_rate, row, full_cost_name="payment")
        else:
            with redirect_stdout(f):
                currency_rate, _ = get_entry_values(full_cost, COMMISION_RATE, price_in_currency, units, sell=sell)
            format_output(currency_rate, row)

def postprocess_floats(df_org: pd.DataFrame) -> pd.DataFrame:
    float_cols = ["units", "price_in_currency", "full_cost"]
    df = df_org.copy()

    for col in float_cols:
        df[col] = df[col].apply(lambda x: float(x.replace(",", ".")) if isinstance(x, str) else x)
    return df

def format_output(currency_rate: float, row: pd.Series, full_cost_name: Optional[str] = None):
    comment = ""
    if not pd.isnull(row["comments"]):
        comment = row["comments"]

    if not full_cost_name:
        full_cost_name = "Full Cost"

    msg = (f"Entry: {row['data']} | "
           f"{row['account'].upper()} | {row['type'].lower()} | Name: {row['name']} | Currency {row['currency']} | Units: {row['units']} | Price in Currency: {row['price_in_currency']} {row['currency']} | "
           f"{full_cost_name}:"
           f" {row['full_cost']} PLN | | Currency Rate: {currency_rate:.5f} "
           f"| {comment}")

    print(msg)
    print("\n")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run entries recording process.")
    parser.add_argument("--path", required=True, help="Path to csv file with entries.")

    args = parser.parse_args()

    run(args)
