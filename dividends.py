import argparse
import json
import os
import random
from tqdm import tqdm
from typing import Optional

import bs4
import pandas as pd
from pathlib import Path
from time import sleep
from copy import deepcopy
from datetime import datetime
import re

from html_utils import fetch_website_text, fetch_website_text_with_soup, get_binary_response

ISIN_PATH = os.path.join("data", "isin.json")
BASE_DIVIDEND_PATH = os.path.join("data", "dividends")
BASE_COMPANIES_PATH = os.path.join("data", "companies")
BASE_COMPANIES_RESULTS_PATH = os.path.join("data", "results")

BASE_URL = "https://www.stockwatch.pl"
URL_ARISTOCRATS = "https://www.stockwatch.pl/dywidendowi-arystokraci"

# GPW data: https://www.gpw.pl/archiwum-notowan?fetch=0&type=10&instrument=&date=24-06-2025&show_x=Poka%C5%BC+wyniki

#TODO: add company results
#TODO: add company stock price

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

def check_and_correct_row(row: list, header: list) -> list:
    if len(row) == len(header):
        return row

    try:
        datetime.strptime(row[3], "%Y-%m-%d")
    except ValueError as e:
        row.insert(3, "")

    if len(row) + 1 == len(header):
        row = row + [""]
    else:
        row = row + [""] * (len(header) - len(row))

    return row

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

    # save_isin(data, get_company_name_from_stockwatch(url), ignore_save_errors=ignore_save_errors)

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
    divid_table = deepcopy(data[data_idxes["data"]])
    company_name = divid_table[0]
    k = 1
    while data[data_idxes["data"] + k][0] == company_name:
        divid_table += data[data_idxes["data"] + k]
        k += 1

    idxes = [i for i, val in enumerate(divid_table) if val == company_name]
    idxes.append(len(divid_table))

    rows = list()
    for i in range(len(idxes) - 1):
        row = divid_table[idxes[i]:idxes[i + 1]]
        if len(row) > 3:
            rows.append(check_and_correct_row(row, table_headers))
        else:
            raise RuntimeError(f"Something went wrong for {company_name} at {url}.")

    df = pd.DataFrame(rows, columns=table_headers)
    years = df.iloc[:,1].apply(get_year)

    df["Rok"] = years
    df.sort_values(by="Rok", inplace=True)
    return df

def get_year(text: str) -> int:

    pattern = r"\d{4}-\d{2}-\d{2}"
    match = re.search(pattern, text)
    if match:
        date_str = match.group(0)
        year = int(date_str.split("-")[0])
        return year
    else:
        raise ValueError(f"No valid date found in the text: {text}")

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


def save_companies_data(df: pd.DataFrame, company_name: str, ignore_save_errors: bool = False):
    """
    Saves the data of a single company to a CSV file.
    :param df: DataFrame containing the data of the company
    :param company_name: Name of the company
    :param ignore_save_errors: If True, ignores errors when saving the data
    """
    save_path = Path(BASE_COMPANIES_PATH) / f"{company_name}.csv"
    if save_path.exists() and not ignore_save_errors:
        raise RuntimeError(f"Data for {company_name} already exists in {save_path}")

    os.makedirs(BASE_COMPANIES_PATH, exist_ok=True)
    df.to_csv(save_path, index=False)
    print(f"Saved data for {company_name} to {save_path}")

def get_isin_of_company(company_name: str) -> str:

    path = Path(ISIN_PATH)
    with open(path, "r") as file:
        isin_data = json.load(file)

    isin = isin_data.get(company_name, None)
    if not isin:
        raise ValueError(f"ISIN for {company_name} not found in {ISIN_PATH}")
    return isin

def get_companies_results(company_name: str, save_results: bool=False) -> pd.DataFrame:

    def flatten(data_idxes: dict) -> dict:
        for key, val in data_idxes.items():
            if data_idxes[key][1] == 0:
                data_idxes[key] = data_idxes[key][0]

    url =f"https://strefainwestorow.pl/notowania/spolki/{get_isin_of_company(company_name)}/wyniki-finansowe"

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

    data_idxes = dict()
    tagged = False
    for i, entries in enumerate(data):
        for j, entry in enumerate(entries):
            if f"Stanowisko" in entry and not tagged:
                data_idxes["headers"] = (i, j)
                data_idxes["data"] = (i + 1, j)
                # data_idxes["data2"] = (i + 2, j)
                tagged = True


    flatten(data_idxes)
    table_headers = data[data_idxes["headers"]]

    # select idx of beginning of each row name starting from letters
    idxes = [i for i, val in enumerate(data[data_idxes["data"]]) if val[0].isalpha()]
    idxes.append(len(data[data_idxes["data"]]))

    rows = list()
    for i in range(len(idxes) - 1):
        rows.append(data[data_idxes["data"]][idxes[i]:idxes[i + 1]])

    for i in range(len(rows)):
        if len(rows[i]) != len(table_headers):
            raise RuntimeError(f"Something went wrong with the data format {rows[i]}.")

    df = pd.DataFrame(rows, columns=table_headers)

    df = df.T
    df.reset_index(drop=False, inplace=True)
    cols = df.iloc[0].tolist()
    cols[0] = "Rok"
    df.columns = cols
    df = df[1:]  # Remove the first row which is now the header

    if save_results:
        os.makedirs(BASE_COMPANIES_RESULTS_PATH, exist_ok=True)
        save_path = Path(BASE_COMPANIES_RESULTS_PATH) / f"{company_name}.csv"
        df.to_csv(save_path, index=False)
        print(f"Saved data to {save_path}")

    return df

def get_company_stock_price(company_name: str, date: Optional[str] = None, save_data: bool = True) -> pd.DataFrame:
    """
    Fetches the stock price of a company from gpw.pl.
    :param company_name: Name of the company
    :param date: Date in the format "dd-mm-yyyy" to fetch the stock price for a specific date
    :param save_data: If True, saves the fetched data to a XLS file
    :return: DataFrame containing the stock price data
    """
    if date:
        url = f"https://www.gpw.pl/archiwum-notowan?fetch=1&type=10&instrument={company_name}&date={date}"
    else:
        url = f"https://www.gpw.pl/archiwum-notowan?fetch=1&type=10&instrument={company_name.upper()}&date="

    stock_prices_path = os.path.join("data", "stock_prices")
    os.makedirs(stock_prices_path, exist_ok=True)

    if save_data:
        get_binary_response(url, save_path=os.path.join(stock_prices_path, f"{company_name}_stock_price.xls"))
    else:
        raise NotImplementedError("Not saving stock price data is not implemented yet.")



def main(args: argparse.Namespace):


    # if not os.path.exists(BASE_DIVIDEND_PATH):

    u = "https://www.gpw.pl/archiwum-notowan?fetch=0&type=10&instrument=&date=24-06-2025&show_x=Poka%C5%BC+wyniki"
    # to trzeba getem zapisac jako binarny xls
    # chyba
    u2 = "https://www.gpw.pl/archiwum-notowan?fetch=1&type=10&instrument=&date=11-06-2025"

    get_company_stock_price("sonel", save_data=True)

    # get_binary_response(u2, save_path="aaa.xls")


    text, soup = fetch_website_text_with_soup(u)

    links = list()
    for link in soup.find_all("a"):
        links.append(link.get("href"))

    comp = "handlowy"
    df = get_data_of_single_company(f"https://www.stockwatch.pl/gpw/{comp},notowania,dywidendy.aspx",
                                    ignore_save_errors=True)
    save_companies_data(df, comp, ignore_save_errors=True)
    #
    get_companies_results(comp, save_results=True)

    for company_name in tqdm(os.listdir(BASE_COMPANIES_PATH)):
        company_name = os.path.splitext(company_name)[0]
        save_path = Path(BASE_COMPANIES_RESULTS_PATH) / f"{company_name}.csv"
        if not os.path.exists(save_path):

            s = random.randint(3,7)
            sleep(s)
            try:
                df = get_companies_results(company_name, save_results=True)
            except Exception as e:
                print(f"Failed for {company_name}")
                #Compaies not present are from newconnect
                #https://www.bankier.pl/gielda/notowania/new-connect/POLTRONIC/wyniki-finansowe/jednostkowy/kwartalny/standardowy/1
                continue



    # company_links = json.load(open(os.path.join(BASE_DIVIDEND_PATH, "aristocrats_5_years_links.json"), "r"))
    #
    # for company_name, url in tqdm(company_links.items()):
    #     save_path = Path(BASE_COMPANIES_PATH) / f"{company_name}.csv"
    #     if not os.path.exists(save_path):
    #
    #         s = random.randint(3,7)
    #         sleep(s)
    #         try:
    #             df = get_data_of_single_company(url, ignore_save_errors=True)
    #             save_companies_data(df, company_name, ignore_save_errors=True)
    #         except Exception as e:
    #             print(f"Failed for {url}")
    #             continue


    # df = get_data_of_single_company("https://www.stockwatch.pl/gpw/sniezka,notowania,dywidendy.aspx",
    #                             ignore_save_errors=True)




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch data from StockWatch website")
    parser.add_argument("--url", type=str, default=URL_ARISTOCRATS, help="URL to fetch data from")

    args = parser.parse_args()

    main(args)
