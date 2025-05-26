import argparse
import json
import os
from codecs import ignore_errors

import bs4
import pandas as pd
from pathlib import Path

from html_utils import fetch_website_text, fetch_website_text_with_soup

ISIN_PATH = os.path.join("data", "isin.json")
BASE_DIVIDEND_PATH = os.path.join("data", "dividends")


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

    # select idx of beginning of each row (company name)
    idxes = [i for i, val in enumerate(data[data_idxes["data"]]) if val == data[data_idxes["data"]][0]]
    idxes.append(len(data[data_idxes["data"]]))

    rows = list()
    for i in range(len(idxes) - 1):
        rows.append(data[data_idxes["data"]][idxes[i]:idxes[i + 1]])

    for i in range(len(rows)):
        if len(rows[i]) != len(table_headers):
            rows[i] = rows[i] + [""] * (len(table_headers) - len(rows[i]))

    return pd.DataFrame(rows, columns=table_headers)

def get_data_of_aristocrats(url: str, aristoctrat_years: int = 10, save_table: bool = True) -> pd.DataFrame:

    if aristoctrat_years not in [5, 10]:
        raise ValueError("aristoctrat_years must be either 5 or 10")

    def flatten(data_idxes: dict) -> dict:
        for key, val in data_idxes.items():
            data_idxes[key] = data_idxes[key][0]

    txt, soup = fetch_website_text_with_soup(url)
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

    data_idxes = dict()
    for i, entries in enumerate(data):
        for j, entry in enumerate(entries):
            if f"Dywidendowi arystokraci {aristoctrat_years} LAT" in entry:
                data_idxes["headers"] = (i + 1, j)
                data_idxes["data"] = (i + 2, j)

    flatten(data_idxes)
    table_headers = data[data_idxes["headers"]]
    table_headers.insert(3, "Data Dyw")

    # select idx of beginning of each row (company name in capital letters)
    idxes = [i for i, val in enumerate(data[data_idxes["data"]]) if val.isupper()]
    idxes.append(len(data[data_idxes["data"]]))

    rows = list()
    for i in range(len(idxes) - 1):
        rows.append(data[data_idxes["data"]][idxes[i]:idxes[i + 1]])

    for i in range(len(rows)):
        if len(rows[i]) != len(table_headers):
            rows[i] = rows[i] + [""] * (len(table_headers) - len(rows[i]))

    df = pd.DataFrame(rows, columns=table_headers)

    if save_table:
        os.makedirs(BASE_DIVIDEND_PATH, exist_ok=True)
        save_path = Path(BASE_DIVIDEND_PATH) / f"aristocrats_{aristoctrat_years}_years.csv"
        df.to_csv(save_path, index=False)
        print(f"Saved data to {save_path}")

        links = get_companies_links(soup, df["Spółka"].unique())
        with open(os.path.join(BASE_DIVIDEND_PATH, f"aristocrats_{aristoctrat_years}_years_links.json"), "w") as file:
            json.dump(links, file, indent=4)

    return df

def get_companies_links(soup: bs4.BeautifulSoup, names: list[str]) -> dict:

    names = [name.lower() for name in names]
    links = list()
    for link in soup.find_all("a"):
        links.append(link.get("href"))

    found_links = dict()

    for link in links:
        for company in names:
            if company in found_links.keys():
                continue
            pattern = f"{company},notowania,dywidendy"
            if pattern in link:
                found_links[company] = BASE_URL + link

    return found_links



def main(args: argparse.Namespace):


    # Fetch the website text
    # text = fetch_website_text(args.url)
    #
    # if not text:
    #     raise RuntimeError(f"Failed to fetch data from {args.url}")

    get_data_of_aristocrats(URL_ARISTOCRATS, 5, True)

    df = get_data_of_single_company("https://www.stockwatch.pl/gpw/sniezka,notowania,dywidendy.aspx",
                                    ignore_save_errors=True)




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch data from StockWatch website")
    parser.add_argument("--url", type=str, default=URL_ARISTOCRATS, help="URL to fetch data from")

    args = parser.parse_args()

    main(args)