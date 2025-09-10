from copy import deepcopy
from datetime import datetime
import json
import os
import pandas as pd
from pathlib import Path
import re

from html_utils import fetch_website_text

BASE_COMPANIES_PATH = os.path.join("data", "companies")
ISIN_PATH = os.path.join("data", "isin.json")
BASE_COMPANIES_RESULTS_PATH = os.path.join("data", "results")

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

def get_financial_results_url(company_name: str) -> str:
    return f"https://strefainwestorow.pl/notowania/spolki/{get_isin_of_company(company_name)}/wyniki-finansowe"

def get_companies_results(company_name: str, save_results: bool=False) -> pd.DataFrame:

    def flatten(data_idxes: dict) -> dict:
        for key, val in data_idxes.items():
            if data_idxes[key][1] == 0:
                data_idxes[key] = data_idxes[key][0]

    # url =f"https://strefainwestorow.pl/notowania/spolki/{get_isin_of_company(company_name)}/wyniki-finansowe"
    url = get_financial_results_url(company_name)

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


def get_isin_of_company(company_name: str) -> str:

    path = Path(ISIN_PATH)
    with open(path, "r") as file:
        isin_data = json.load(file)

    isin = isin_data.get(company_name, None)
    if not isin:
        raise ValueError(f"ISIN for {company_name} not found in {ISIN_PATH}")
    return isin