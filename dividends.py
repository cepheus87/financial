import argparse
import json
import os
from codecs import ignore_errors

import pandas as pd
from pathlib import Path

from html_utils import fetch_website_text

ISIN_PATH = os.path.join("data", "isin.json")

BASE_URL = "https://www.stockwatch.pl"
URL_ARISTOCRATS = "https://www.stockwatch.pl/dywidendowi-arystokraci"

def save_isin(data: list, company_name: str, ignore_save_errors: bool = False):

    isin = None
    for i, entries in enumerate(data):
        for j, entry in enumerate(entries):
            if "ISIN" in entry:
                isin = entry

    if isin is not None:

        isin = isin.split(":")[-1].strip()

        with open("data/isin.json", "r") as file:
            isin_data = json.load(file)

            if isin_data.get(company_name) is not None and not ignore_save_errors:
                raise RuntimeError(f"ISIN for {company_name} already exists in {ISIN_PATH}")

        isin_data[company_name] = isin
        with open("data/isin.json", "w") as file:
            json.dump(isin_data, file, indent=4)

def get_company_name_from_stockwatch(url: str) -> str:
    path = Path(url)
    name = path.name
    return name.split(",")[0]

def get_data_of_single_company(url: str, ignore_save_errors: bool = False) -> pd.DataFrame:

    def flatten(data_idxes: dict) -> dict:
        for key, val in data_idxes.items():
            if data_idxes[key][1] == 0:
                data_idxes[key] = data_idxes[key][0]

    txt = fetch_website_text(url)
    if not txt:
        raise RuntimeError(f"Failed to fetch data from {url}")
    rows = txt.split("\n\n\n\n\n")
    data = []

    for row in rows:
        # Split each row into columns
        columns = row.split("\n")
        # Clean and filter empty strings
        columns = [col.strip() for col in columns if col.strip()]
        if columns:
            data.append(columns)

    save_isin(data, get_company_name_from_stockwatch(url), ignore_save_errors=ignore_save_errors)

    data_idxes = dict()
    for i, entries in enumerate(data):
        for j, entry in enumerate(entries):
            if "Kalendarium dywidend" in entry:
                data_idxes["headers"] = (i + 1, j)
                data_idxes["data"] = (i + 2, j)

    flatten(data_idxes)
    table_headers = data[data_idxes["headers"]]
    table_headers.insert(3, "Data Dyw")

    idxes = [i for i, val in enumerate(data[data_idxes["data"]]) if val == data[data_idxes["data"]][0]]
    idxes.append(len(data[data_idxes["data"]]))

    rows = list()
    for i in range(len(idxes) - 1):
        rows.append(data[data_idxes["data"]][idxes[i]:idxes[i + 1]])

    for i in range(len(rows)):
        if len(rows[i]) != len(table_headers):
            rows[i] = rows[i] + [""] * (len(table_headers) - len(rows[i]))

    return pd.DataFrame(rows, columns=table_headers)


def main(args: argparse.Namespace):


    # Fetch the website text
    # text = fetch_website_text(args.url)
    #
    # if not text:
    #     raise RuntimeError(f"Failed to fetch data from {args.url}")

    df = get_data_of_single_company("https://www.stockwatch.pl/gpw/sniezka,notowania,dywidendy.aspx",
                                    ignore_save_errors=True)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch data from StockWatch website")
    parser.add_argument("--url", type=str, default=URL_ARISTOCRATS, help="URL to fetch data from")

    args = parser.parse_args()

    main(args)