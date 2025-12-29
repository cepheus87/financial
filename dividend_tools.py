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

from stockwatch_utils.get_headers_stockwatch_financials import extract_header_names as extract_headers
from stockwatch_utils.get_headers_stockwatch_financials import sample_text as sample_financial_text

BASE_COMPANIES_PATH = os.path.join("data", "companies")
ISIN_PATH = os.path.join("data", "isin.json")
BASE_COMPANIES_RESULTS_PATH = os.path.join("data", "results")

YEARS_RANGE = 15

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

    ax1.grid(True)

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
    max_year = max(df_div["rok"].max(), df_results["rok"].max())
    df_results = df_results[df_results["rok"] >= max_year - YEARS_RANGE]


    df_div = add_same_years(df_div)
    df_div = df_div[df_div["rok"] >= max_year - YEARS_RANGE]

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

    ax1.grid(True)

    # Second subplot: results plot
    ax3.plot(df_results["rok"], df_results["zysk_netto"], marker="o", color="lightgreen", label="zysk_netto (line)")
    ax3.set_xlabel("Rok")
    ax3.set_ylabel("zysk_netto (line)", color="green")
    ax3.set_title("Zysk netto (line plot)")

    coeffs = np.polyfit(df_results["rok"], df_results["zysk_netto"], 1)
    zysk_netto_fit = np.polyval(coeffs, df_results["rok"])
    ax3.plot(df_results["rok"], zysk_netto_fit, 'g--', label='Zysk netto fit')
    ax3.hlines(y=0, xmin=df_results["rok"].min(), xmax=df_results["rok"].max(), linewidth=3, color='r')

    ax3.grid(True)

    ax3.legend(loc="upper center")

    plt.tight_layout()

    save_file = f"{company_name}.png"
    fig.savefig(os.path.join(output_path, save_file))
    print(f"Saved plot with results to {os.path.join(output_path, save_file)}")

    plt.close()
    # plt.show()


def get_company_financial_data(company_sw_url: str) -> pd.DataFrame:

    def find_pattern_indexes(lst: list, pattern: str = r"^Q\d{1}\s\d{4}"):
        """
        Returns a list of indexes in lst where elements match the given regex pattern.
        Args:
            lst (list): List of strings to search.
            pattern (str): Regex pattern to match. Default matches 'Q' (optional) followed by 4 digits.
        Returns:
            List[int]: List of matching indexes.
        """
        return [i for i, val in enumerate(lst) if re.match(pattern, val)]

    def div_to_float(val: str) -> list:

        formatted_val = []

        if isinstance(val, str):
            val = val.replace(",", ".")
            vals = val.split(" ")

            val_joined = ""
            for i, v in enumerate(vals):
                if len(v) > 3:
                    val_joined += v[:3]
                    formatted_val.append(val_joined)
                    val_joined = v[3:]
                elif i == len(vals) - 1:
                    val_joined += v
                    formatted_val.append(val_joined)
                else:
                    val_joined += v

        return formatted_val

    if not "stockwatch" in company_sw_url:
        raise ValueError(f"URL {company_sw_url} is not a valid Stockwatch URL.")

    # data = []
    # TODO:
    import pickle
    with open("asbis_financial_raw.plk", "rb") as file:
        data = pickle.load(file)

    if not data:

        txt = fetch_website_text(company_sw_url)

        if not txt:
            raise RuntimeError(f"Failed to fetch data from {company_sw_url}")
        rows = txt.split("\n\n\n\n\n")
        data = []

        for row in rows:
            # Split each row into columns
            columns = row.split("\n")
            # Clean and filter empty strings
            columns = [col.strip() for col in columns if col.strip()]
            if columns:
                data.append(columns)


    START = "Dane / Okres"
    DYNAMIKA = "dynamika kw/kw"
    DATA_RAPORTU = "Data raportu"

    rows_headers = extract_headers(sample_financial_text)

    data = [data[i] for i in range(len(data)) if (len(data[i]) > 0 and data[i][0] == START)][0]

    example_data = ['Q2 2024', 'Q3 2024', 'Q4 2024', 'Q1 2025', 'Q2 2025', 'Q3 2025', 'Data raportu10.05.200714.08.200709.11.200730.03.200806.05.200812.08.200804.11.200830.03.200906.05.200912.08.200905.11.200930.03.201006.05.201011.08.201009.11.201030.03.201111.05.201118.08.201109.11.201129.03.201208.05.201209.08.201207.11.201227.02.201308.05.201307.08.201307.11.201327.02.201406.05.201407.08.201406.11.201426.02.201507.05.201506.08.201505.11.201526.02.201612.05.201611.08.201608.11.201628.02.201709.05.201708.08.201707.11.201727.02.201809.05.201808.08.201807.11.201827.02.201909.05.201908.08.201906.11.201927.02.202007.05.202012.08.202005.11.202025.02.202106.05.202112.08.202104.11.202124.02.202205.05.202211.08.202203.11.202223.02.202311.05.202310.08.202309.11.202329.02.202409.05.202408.08.202407.11.202427.02.202508.05.202507.08.202506.11.2025 Liczba akcji55 475 24855 475 24855 475 24855 475 24855 475 24855 475 24855 475 24855 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 00055 500 000', 'Przychody', '768 729792 4441 084 3851 173 152860 710751 713940 4191 038 534822 008756 020849 4211 142 112954 106852 0301 109 6821 394 9761 008 287833 3131 056 7471 543 2521 222 8651 216 4051 435 4981 797 2791 396 9181 493 6721 406 1531 763 8681 046 2221 098 4831 224 2191 544 9941 050 511908 3171 082 9241 428 120985 733961 3491 073 6341 478 9981 177 9441 073 1731 351 4111 948 3611 711 5451 656 4461 970 5272 151 0341 580 8271 413 9541 796 6702 572 3321 963 9701 557 5292 356 2003 273 7232 768 8222 557 8602 775 3943 832 0972 865 8772 251 7753 293 5593 620 2183 168 0782 812 5193 192 1163 672 7142 847 0572 580 2992 818 9063 740 2792 940 1073 569 5153 388 127', 'dynamika kw/kw+3,08%+36,84%+8,19%-26,63%-12,66%+25,10%+10,43%-20,85%-8,03%+12,35%+34,46%-16,46%-10,70%+30,24%+25,71%-27,72%-17,35%+26,81%+46,04%-20,76%-0,53%+18,01%+25,20%-22,28%+6,93%-5,86%+25,44%-40,69%+5,00%+11,45%+26,20%-32,01%-13,54%+19,22%+31,88%-30,98%-2,47%+11,68%+37,76%-20,36%-8,89%+25,93%+44,17%-12,15%-3,22%+18,96%+9,16%-26,51%-10,56%+27,07%+43,17%-23,65%-20,69%+51,28%+38,94%-15,42%-7,62%+8,50%+38,07%-25,21%-21,43%+46,27%+9,92%-12,49%-11,22%+13,50%+15,06%-22,48%-9,37%+9,25%+32,69%-21,39%+21,41%-5,08% dynamika r/r+11,97%-5,14%-13,28%-11,47%-4,50%+0,57%-9,68%+9,97%+16,07%+12,70%+30,64%+22,14%+5,68%-2,20%-4,77%+10,63%+21,28%+45,97%+35,84%+16,46%+14,23%+22,79%-2,04%-1,86%-25,10%-26,46%-12,94%-12,41%+0,41%-17,31%-11,54%-7,56%-6,17%+5,84%-0,86%+3,56%+19,50%+11,63%+25,87%+31,74%+45,30%+54,35%+45,81%+10,40%-7,64%-14,64%-8,82%+19,59%+24,24%+10,15%+31,14%+27,27%+40,98%+64,23%+17,79%+17,06%+3,51%-11,97%+18,67%-5,53%+10,54%+24,90%-3,08%+1,45%-10,13%-8,26%-11,69%+1,84%+3,27%+38,34%+20,19%', 'Zysk brutto na sprzedaży', '34 84133 94751 06164 82451 79842 99746 89141 50024 80138 21142 37955 57344 51537 45053 58463 77156 10240 28552 11796 59964 41354 00769 82489 38282 45182 46190 101109 58267 94560 37870 23678 64025 67030 63550 26670 61052 64354 46465 62385 96061 45057 85572 40995 37077 41572 99594 745110 50079 95680 257105 612134 77699 71389 770137 403207 242178 092177 479204 512288 498218 085210 543263 966327 961272 343225 991255 054305 753235 847205 678215 475300 102205 866238 974238 126', 'dynamika kw/kw-2,57%+50,41%+26,95%-20,09%-16,99%+9,06%-11,50%-40,24%+54,07%+10,91%+31,13%-19,90%-15,87%+43,08%+19,01%-12,03%-28,19%+29,37%+85,35%-33,32%-16,16%+29,29%+28,01%-7,75%+0,01%+9,26%+21,62%-38,00%-11,14%+16,33%+11,97%-67,36%+19,34%+64,08%+40,47%-25,45%+3,46%+20,49%+30,99%-28,51%-5,85%+25,16%+31,71%-18,83%-5,71%+29,80%+16,63%-27,64%+0,38%+31,59%+27,61%-26,02%-9,97%+53,06%+50,83%-14,07%-0,34%+15,23%+41,07%-24,41%-3,46%+25,37%+24,24%-16,96%-17,02%+12,86%+19,88%-22,86%-12,79%+4,76%+39,27%-31,40%+16,08%-0,35% dynamika r/r+48,67%+26,66%-8,17%-35,98%-52,12%-11,13%-9,62%+33,91%+79,49%-1,99%+26,44%+14,75%+26,03%+7,57%-2,74%+51,48%+14,81%+34,06%+33,98%-7,47%+28,00%+52,69%+29,04%+22,60%-17,59%-26,78%-22,05%-28,24%-62,22%-49,26%-28,43%-10,21%+105,08%+77,78%+30,55%+21,74%+16,73%+6,23%+10,34%+10,95%+25,98%+26,17%+30,85%+15,86%+3,28%+9,95%+11,47%+21,97%+24,71%+11,85%+30,10%+53,77%+78,60%+97,70%+48,84%+39,21%+22,46%+18,63%+29,07%+13,68%+24,88%+7,34%-3,38%-6,77%-13,40%-8,99%-15,52%-1,85%-12,71%+16,19%+10,51% Koszty sprzedaży-14 996-14 084-17 024-23 093-16 957-18 605-17 912-31 282-21 135-20 014-20 540-22 276-22 994-23 008-22 865-31 709-27 003-26 616-26 117-41 034-30 325-28 568-34 200-41 283-37 247-39 845-42 867-49 383-34 752-33 191-32 935-32 983-37 054-25 778-23 514-29 127-24 313-25 304-27 435-36 967-27 898-27 763-32 398-42 032-37 594-42 619-42 579-43 556-40 050-36 291-40 836-47 668-43 372-38 750-43 468-62 732-54 846-57 061-58 447-70 733-71 316-75 639-72 577-89 025-81 752-81 587-82 214- 101 471-78 883-84 305-83 836-96 121-82 051-88 052-92 749 dynamika kw/kw+6,08%-20,87%-35,65%+26,57%-9,72%+3,72%-74,64%+32,44%+5,30%-2,63%-8,45%-3,22%-0,06%+0,62%-38,68%+14,84%+1,43%+1,87%-57,12%+26,10%+5,79%-19,71%-20,71%+9,78%-6,98%-7,58%-15,20%+29,63%+4,49%+0,77%-0,15%-12,34%+30,43%+8,78%-23,87%+16,53%-4,08%-8,42%-34,74%+24,53%+0,48%-16,69%-29,74%+10,56%-13,37%+0,09%-2,29%+8,05%+9,39%-12,52%-16,73%+9,01%+10,66%-12,18%-44,32%+12,57%-4,04%-2,43%-21,02%-0,82%-6,06%+4,05%-22,66%+8,17%+0,20%-0,77%-23,42%+22,26%-6,87%+0,56%-14,65%+14,64%-7,31%-5,33% dynamika r/r-13,08%-32,10%-5,22%-35,46%-24,64%-7,57%-14,67%+28,79%-8,80%-14,96%-11,32%-42,35%-17,43%-15,68%-14,22%-29,41%-12,30%-7,33%-30,95%-0,61%-22,83%-39,47%-25,34%-19,62%+6,70%+16,70%+23,17%+33,21%-6,62%+22,33%+28,60%+11,69%+34,38%+1,84%-16,68%-26,92%-14,75%-9,72%-18,09%-13,70%-34,76%-53,51%-31,42%-3,63%-6,53%+14,85%+4,09%-9,44%-8,29%-6,78%-6,45%-31,60%-26,45%-47,25%-34,46%-12,75%-30,03%-32,56%-24,18%-25,86%-14,63%-7,86%-13,28%-13,98%+3,51%-3,33%-1,97%+5,27%-4,02%-4,44%-10,63% Koszty ogólnego zarządu-10 231-13 085-11 545-11 554-13 675-14 501-17 452-19 655-19 241-17 510-15 694-18 897-16 229-17 773-17 938-18 816-18 281-17 559-18 132-20 614-19 234-18 395-18 873-21 327-21 670-23 788-23 493-25 746-24 121-22 180-22 383-22 394-20 708-18 681-15 652-16 802-15 390-15 420-16 704-16 940-17 373-15 098-16 099-17 700-21 665-16 866-21 095-22 111-22 470-23 872-28 635-33 237-31 353-28 724-31 319-37 161-36 584-35 552-39 889-52 761-46 457-50 035-53 655-62 645-64 674-55 416-57 791-61 820-59 419-60 097-57 499-60 594-58 466-62 472-60 381 dynamika kw/kw-27,90%+11,77%-0,08%-18,36%-6,04%-20,35%-12,62%+2,11%+9,00%+10,37%-20,41%+14,12%-9,51%-0,93%-4,89%+2,84%+3,95%-3,26%-13,69%+6,69%+4,36%-2,60%-13,00%-1,61%-9,77%+1,24%-9,59%+6,31%+8,05%-0,92%-0,05%+7,53%+9,79%+16,21%-7,35%+8,40%-0,19%-8,33%-1,41%-2,56%+13,10%-6,63%-9,94%-22,40%+22,15%-25,07%-4,82%-1,62%-6,24%-19,95%-16,07%+5,67%+8,39%-9,03%-18,65%+1,55%+2,82%-12,20%-32,27%+11,95%-7,70%-7,23%-16,76%-3,24%+14,31%-4,29%-6,97%+3,88%-1,14%+4,32%-5,38%+3,51%-6,85%+3,35% dynamika r/r-33,66%-10,82%-51,17%-70,11%-40,70%-20,75%+10,07%+3,86%+15,65%-1,50%-14,30%+0,43%-12,64%+1,20%-1,08%-9,56%-5,21%-4,76%-4,09%-3,46%-12,67%-29,32%-24,48%-20,72%-11,31%+6,76%+4,72%+13,02%+14,15%+15,78%+30,07%+24,97%+25,68%+17,46%-6,72%-0,82%-12,88%+2,09%+3,62%-4,49%-24,71%-11,71%-31,03%-24,92%-3,72%-41,54%-35,74%-50,32%-39,53%-20,33%-9,37%-11,81%-16,68%-23,77%-27,36%-41,98%-26,99%-40,74%-34,51%-18,73%-39,21%-10,75%-7,71%+1,32%+8,13%-8,45%+0,51%+1,98%+1,60%-3,95%-5,01%']


    idxes = find_pattern_indexes(data)
    periods = [data[i] for i in idxes]

    report_date_idx = [i for i, val in enumerate(data) if DATA_RAPORTU in val][0]
    data_without_periods = data[report_date_idx + 1:]

    named_data = dict()
    name = ""
    values = []
    dynamic = []
    for i, val in enumerate(data_without_periods):
        if i % 3 == 0:
            name = val
        elif i % 3 == 1:
            values = div_to_float(val)
        elif i % 3 == 2:
            dynamic = val  # TODO: hande dynamic values properly
            named_data[name] = {"values": values, "dynamic": dynamic}
            name = ""
            values = []
            dynamic = []



    #TODO handle dynamic values properly
    named_data = {key: val["values"] for key, val in named_data.items()}
    df = pd.DataFrame(named_data, index=periods)
    df.reset_index(drop=False, inplace=True)
    df.rename(columns={"index": "Okres"}, inplace=True)

    return df

def get_financial_data_br(company_name: str) -> list:
    br_url = f"https://www.biznesradar.pl/raporty-finansowe-rachunek-zyskow-i-strat/{company_name.upper()},Q"

    txt = fetch_website_text(br_url)

    if not txt:
        raise RuntimeError(f"Failed to fetch data from {br_url}")

    rows = txt.split("\n\n\n\n\n")
    data = []

    for row in rows:
        # Split each row into columns
        columns = row.split("\n")
        # Clean and filter empty strings
        columns = [col.strip() for col in columns if col.strip()]
        if columns:
            data.append(columns)

    return data

import json
import re
import pandas as pd
from pathlib import Path

def load_financial_table(data: list) -> pd.DataFrame:
    # data = json.loads(Path(path).read_text(encoding="utf-8"))
    header_row, value_rows_raw = data[9], data[10]

    value_rows = []
    for row in value_rows_raw:
        if row.startswith("EBITDA"):
            value_rows.append(row)
            break
        else:
            value_rows.append(row)

    # Keep only the "YYYY/Qx" tokens, drop bracketed month tags
    periods = [h for h in header_row if not h.startswith("(")]

    def div_to_float(val: str) -> list:

        formatted_val = []

        if isinstance(val, str):
            val = val.replace(",", ".")
            vals = val.split(" ")

            val_joined = ""
            for i, v in enumerate(vals):
                if len(v) > 3:
                    val_joined += v[:3]
                    formatted_val.append(val_joined)
                    val_joined = v[3:]
                elif i == len(vals) - 1:
                    val_joined += v
                    formatted_val.append(val_joined)
                else:
                    val_joined += v

        return formatted_val

    def parse_row(row_text: str):
        # split into name + remainder (first digit starts data)
        m = re.match(r"([^\d]+)(.*)", row_text.strip())
        if not m:
            return None, [], [], []
        name, tail = m.group(1).strip(), m.group(2).strip()

        vals, dyn_kk, dyn_rr = [], [], []
        idx = 0

        if name == "Data publikacji":
            for i in range(len(periods)):
                vals.append(tail[i*10:i*10+10])
        elif len(tail) == len(periods):
            for val in tail:
                vals.append(val)
        else:

            while idx < len(tail):
                # value
                val_m = re.match(r"\s*(-?[\d\s]+)", tail[idx:])
                if not val_m:
                    break
                val = val_m.group(1).strip()
                if idx == 0:
                    vals.extend(div_to_float(val))
                else:
                    vals.append(val.replace(" ", ""))
                # vals.append(val.replace(" ", ""))
                idx += val_m.end()

                # subsequent k/k or r/r blocks (order may vary)
                while True:
                    kk_m = re.match(r"\s*k/k\s+([+-]?\d+(?:\.\d+)?%)~branża\s+[+-]?\d+(?:\.\d+)?%", tail[idx:])
                    rr_m = re.match(r"\s*r/r\s+([+-]?\d+(?:\.\d+)?%)~branża\s+[+-]?\d+(?:\.\d+)?%", tail[idx:])
                    if kk_m:
                        dyn_kk.append(kk_m.group(1))
                        idx += kk_m.end()
                        continue
                    if rr_m:
                        dyn_rr.append(rr_m.group(1))
                        idx += rr_m.end()
                        continue
                    break

        # pad/truncate to period count; apply missing cells rules
        n = len(periods)
        vals = (vals + [""] * n)[:n]

        dyn_kk = ([""] + dyn_kk + [""] * n)[:n]       # no k/k for first column
        dyn_rr = ([""] * 4 + dyn_rr + [""] * n)[:n]   # no r/r for first four columns

        return name, vals, dyn_kk, dyn_rr

    table = {}
    for row in value_rows:
        name, vals, dyn_kk, dyn_rr = parse_row(row)
        if not name:
            continue
        table[name] = vals
        # attach dynamics as separate rows
        table[f"{name} k/k"] = dyn_kk
        table[f"{name} r/r"] = dyn_rr

    df = pd.DataFrame(table, index=periods)
    df = df.replace('', np.nan).dropna(axis=1, how='all')
    # df = df.replace(np.nan, "")
    df.index.name = "Okres"

    #TODO split Okres into Year and Quarter
    return df.reset_index()

# Example usage:
# df = load_financial_table("financial_data_br.json")
# print(df.head())