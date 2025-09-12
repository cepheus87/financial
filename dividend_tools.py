from copy import deepcopy
from datetime import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from pathlib import Path
import re


from html_utils import fetch_website_text
from utils_data import change_column_names
from utils_stock_price import get_stock_prices_yearly

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

# plotting functions

def save_div_plots(company_name: str):
    def check_results(company: str) -> bool:
        return os.path.exists(os.path.join("data", "results", company))

    output = os.path.join("data", "plots")
    os.makedirs(output, exist_ok=True)

    comp_file = f"{company_name}.csv"
    company_path = Path("data") / "companies" / comp_file
    df_div = prepare_div_df(company_path)


    company_path = Path("data") / "results" / comp_file
    df_res = prepare_results_df(company_path)

    if check_results(comp_file):
        prepare_div_results_plots(df_div, df_res, output)
    else:
        prepare_div_plot(df_div, output)


def prepare_div_df(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df.columns = change_column_names(df.columns)
    df["dyw_na_akcje"] = df["dyw_na_akcje"].apply(to_float)
    df["stopa"] = df["stopa"].apply(to_float)
    # df["rok"] = pd.to_datetime(df["data_dyw"]).apply(lambda x: x.year)

    return df

def to_float(val: str) -> float:
    if isinstance(val, str):
        val = val.replace(",", ".")
        if "\xa0" in val:
            val = val.replace('\xa0', "")
        if "%" in val:
            val = val.replace("%", "")
            val = float(val)
            val = val * 0.01
        elif " (" in val:
            val = val.split(" ")[0]
            val = float(val)
        else:
            val = float(val)
    return val


def prepare_results_df(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df.columns = change_column_names(df.columns)
    for col in df.columns:
        df[col] = df[col].apply(to_float)
    # df["dyw_na_akcje"] = df["dyw_na_akcje"].apply(to_float)
    # df["stopa"] = df["stopa"].apply(to_float)
    # df["rok"] = pd.to_datetime(df["data_dyw"]).apply(lambda x: x.year)

    return df

def add_same_years(df: pd.DataFrame) -> pd.DataFrame:
    years = df["rok"].unique()
    df2 = df.groupby("rok")[["dyw_na_akcje", "stopa"]].sum()
    df2.reset_index(inplace=True, drop=False)
    df2["spolka"] = df["spolka"].unique()[0]
    return df2


def prepare_div_plot(df: pd.DataFrame, output_path: str):
    os.makedirs(output_path, exist_ok=True)

    df = add_same_years(df)

    fig, ax1 = plt.subplots()

    # Bar plot on left y-axis
    ax1.bar(df["rok"], df["dyw_na_akcje"], color="skyblue", label="dyw_na_akcje")
    ax1.set_ylabel("dyw_na_akcje (bar)", color="skyblue")
    ax1.set_xlabel("Rok")

    coeffs = np.polyfit(df["rok"], df["dyw_na_akcje"], 1)
    dyw_na_akcje_fit = np.polyval(coeffs, df["rok"])
    ax1.plot(df["rok"], dyw_na_akcje_fit, 'b--', label='Dyw na akcje fit')

    # Line plot on right y-axis
    ax2 = ax1.twinx()
    ax2.plot(df["rok"], df["stopa"], color="red", marker="o", label="stopa")
    ax2.set_ylabel("stopa (line)", color="red")

    coeffs = np.polyfit(df["rok"], df["stopa"], 1)
    stopa_fit = np.polyval(coeffs, df["rok"])
    ax2.plot(df["rok"], stopa_fit, 'r--', label='stopa fit')

    company_name = df.spolka.unique()[0].lower()

    fig.suptitle(company_name)
    fig.legend(loc="upper left")

    plt.tight_layout()

    save_file = f"{company_name}.png"
    fig.savefig(os.path.join(output_path, save_file))
    print(f"Saved plot with dividends only to {os.path.join(output_path, save_file)}")

    plt.close()

    # plt.show()


def prepare_div_results_plots(df_div: pd.DataFrame, df_results: pd.DataFrame, output_path: str):
    df_div = add_same_years(df_div)

    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

    # First subplot: bar and line with twin y-axis
    ax1.bar(df_div["rok"], df_div["dyw_na_akcje"], color="skyblue", label="dyw_na_akcje")
    ax1.set_ylabel("dyw_na_akcje (bar)", color="skyblue")
    ax1.set_xlabel("Rok")

    coeffs = np.polyfit(df_div["rok"], df_div["dyw_na_akcje"], 1)
    dyw_na_akcje_fit = np.polyval(coeffs, df_div["rok"])
    ax1.plot(df_div["rok"], dyw_na_akcje_fit, 'b--', label='Dyw na akcje fit')

    ax2 = ax1.twinx()
    ax2.plot(df_div["rok"], df_div["stopa"], color="red", marker="o", label="stopa")
    ax2.set_ylabel("stopa (line)", color="red")
    coeffs = np.polyfit(df_div["rok"], df_div["stopa"], 1)
    stopa_fit = np.polyval(coeffs, df_div["rok"])
    ax2.plot(df_div["rok"], stopa_fit, 'r--', label='stopa fit')

    company_name = df_div.spolka.unique()[0].lower()
    fig.suptitle(company_name)
    fig.legend(loc="upper left")

    # Second subplot: results plot
    ax3.plot(df_results["rok"], df_results["zysk_netto"], marker="o", color="lightgreen", label="zysk_netto (line)")
    ax3.set_xlabel("Rok")
    ax3.set_ylabel("zysk_netto (line)", color="green")
    ax3.set_title("Zysk netto (line plot)")

    coeffs = np.polyfit(df_results["rok"], df_results["zysk_netto"], 1)
    zysk_netto_fit = np.polyval(coeffs, df_results["rok"])
    ax3.plot(df_results["rok"], zysk_netto_fit, 'g--', label='Zysk netto fit')
    ax3.hlines(y=0, xmin=df_results["rok"].min(), xmax=df_results["rok"].max(), linewidth=3, color='r')

    ax3.legend(loc="upper center")

    plt.tight_layout()

    save_file = f"{company_name}.png"
    fig.savefig(os.path.join(output_path, save_file))
    print(f"Saved plot with results to {os.path.join(output_path, save_file)}")

    plt.close()
    # plt.show()