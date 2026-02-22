import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re

from utils.html_utils import fetch_website_text
from utils.utils_data import get_br_name_mapping, find_date_element_index
from utils.setup import ProjectConfig
from financial.gain_loss_tools import YEARS_RANGE

# Patterns for packed value rows
_VALUE_RE = re.compile(r"\s*(-?[\d\s]*(?:,\d+)?)")
_FIRST_VALUE_RE = re.compile(r"\s*(-?[\d\s]*(?:,\d{2})?)")
_DYN_RE = re.compile(r"\s*(k/k|r/r)\s+([+-]?\d+(?:\.\d+)?%)")
_BRANZA_RE = re.compile(r"\s*~branża\s+[+-]?\d+(?:\.\d+)?%")

COLS_TO_SAVE = ["Kurs", "Liczba akcji", "Wartość księgowa na akcję", "Wartość księgowa Grahama na akcję",
                "Przychody ze sprzedaży na akcję", "Zysk na akcję", "Zysk operacyjny na akcję"]


def get_assets_value_indicators_br(company_name: str) -> list:
    br_name = get_br_name_mapping(company_name)

    br_url = f"https://www.biznesradar.pl/wskazniki-wartosci-rynkowej/{br_name.upper()}"

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

def get_assets_value_indicators_table(data: list) -> pd.DataFrame:
    #TODO add some checks if data format is not changed on the website

    date_idx = find_date_element_index(data)
    if date_idx == -1:
        raise ValueError("Could not find date element in data")

    header_row, value_rows_raw = data[date_idx], data[date_idx + 1]

    value_rows = []
    for row in value_rows_raw:
        if row.startswith("EV / EBITDA"):
            value_rows.append(row)
            break
        else:
            value_rows.append(row)

    # Keep only the "YYYY/Qx" tokens, drop bracketed month tags
    periods = [h for h in header_row if not h.startswith("(")]

    def _div_to_float(val: str) -> list:

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

    def _div_to_prices(val: str) -> list:

        prices = []
        float_shift = 3

        if isinstance(val, str):
            val = val.replace(",", ".")
            dot_indexes = [i for i, c in enumerate(val) if c == "."]

            prices.append(val[:dot_indexes[0]+float_shift])
            for i, idx in enumerate(dot_indexes[:-1]):
                prices.append(val[idx+float_shift:dot_indexes[i+1]+float_shift])

            return prices
        else:
            raise RuntimeError("Value for prices is not string")

    def _parse_row(row_text: str, periods_count: int):
        # split into name + remainder (first digit starts data)
        m = re.match(r"([^\d+-]+)(.*)", row_text.strip())
        if not m:
            return None, [], [], []
        name, tail = m.group(1).strip(), m.group(2).strip()

        values, dyn_kk, dyn_rr = [], [], []
        idx = 0

        if name == "Kurs":
            prices = _div_to_prices(tail)
            values.extend(prices)
        elif name == "Liczba akcji":
            shares_num = _div_to_float(tail)
            values.extend(shares_num)
        else:
            while idx < len(tail) and len(values) < periods_count:
                if idx ==0:
                    v_match = _FIRST_VALUE_RE.match(tail, idx)
                else:
                    v_match = _VALUE_RE.match(tail, idx)
                if not v_match or not v_match.group(1):
                    break
                raw_val = v_match.group(1)
                clean_val = raw_val.replace(" ", "").replace(",", ".")
                values.append(clean_val)
                idx = v_match.end()

                kk_val, rr_val = "", ""
                while True:
                    d_match = _DYN_RE.match(tail, idx)
                    if not d_match:
                        break
                    typ, pct = d_match.groups()
                    if typ == "k/k":
                        kk_val = pct
                    else:
                        rr_val = pct
                    idx = d_match.end()
                    b_match = _BRANZA_RE.match(tail, idx)
                    if b_match:
                        idx = b_match.end()
                dyn_kk.append(kk_val)
                dyn_rr.append(rr_val)

        n = periods_count
        values = (values + [""] * n)[:n]
        dyn_kk = (dyn_kk + [""] * n)[:n]
        dyn_rr = (dyn_rr + [""] * n)[:n]
        return name, values, dyn_kk, dyn_rr

    table = {}
    n = len(periods)
    for row in value_rows:
        name, vals, dyn_kk, dyn_rr = _parse_row(row, n)
        if not name or name not in COLS_TO_SAVE:
            continue
        table[name] = vals
        table[f"{name} k/k"] = dyn_kk
        table[f"{name} r/r"] = dyn_rr

    df = pd.DataFrame(table, index=periods)
    df = df.replace("", np.nan).dropna(axis=1, how="all")
    df.index.name = "Okres"
    df.reset_index(inplace=True, drop=False)
    year_quarter = df["Okres"].apply(lambda x: x.split("/") if isinstance(x, str) else ["", ""]).tolist()
    df_yq = pd.DataFrame(year_quarter, columns=["Rok", "Kwartał"])
    df = pd.concat([df_yq, df], axis=1)
    return df


def save_assets_value_indicators_plots(company: str, df_financial):

    #TODO: create yearly version

    rok = "rok"
    okres = "okres"

    df_financial = df_financial.copy()
    df_financial["C/Z"] = df_financial["kurs"] / df_financial["zysk_na_akcje"]
    df_financial["C/WK"] = df_financial["kurs"] / df_financial["wartosc_ksiegowa_na_akcje"]

    output = os.path.join(ProjectConfig.base_data_path, "plots")
    os.makedirs(output, exist_ok=True)

    max_year = max(df_financial[rok].max(), df_financial[rok].max())
    df_financial = df_financial[df_financial[rok] >= max_year - YEARS_RANGE]

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Zysk na akcje
    axs[0, 0].plot(df_financial[okres], df_financial['zysk_na_akcje'], label='Zysk na akcję',
                   marker='o', color='tab:blue')
    ax2_00 = axs[0, 0].twinx()
    ax2_00.plot(df_financial[okres], df_financial['zysk_na_akcje_k/k'], label='Zysk na akcję k/k',
                marker='o', color='black')
    axs[0, 0].set_title('Zysk na akcję')
    axs[0, 0].set_xlabel(okres)
    axs[0, 0].set_ylabel('Wartosc (PLN)')
    ax2_00.set_ylabel('Zysk na akcję k/k', color='black')
    axs[0, 0].tick_params(axis='x', rotation=90)
    axs[0, 0].grid(True)
    axs[0, 0].legend(loc='upper left')
    ax2_00.legend(loc='lower left')

    # Plot 2: C/Z
    axs[0, 1].plot(df_financial[okres], df_financial['C/Z'], label='C/Z',
                   marker='o', color='tab:orange')
    ax2_01 = axs[0, 1].twinx()
    # ax2_01.plot(df_financial[okres], df_financial['zysk_operacyjny_(ebit)_k/k'], label='Zysk operacyjny (EBIT) k/k',
    #             marker='o', color='black')
    ax2_01.plot(df_financial[okres], df_financial['kurs'], label='Kurs',
                marker='o', color='black')
    axs[0, 1].set_title('C/Z')
    axs[0, 1].set_xlabel(okres)
    axs[0, 1].set_ylabel('Wartosc')
    ax2_01.set_ylabel('Kurs', color='black')
    axs[0, 1].tick_params(axis='x', rotation=90)
    axs[0, 1].grid(True)
    axs[0, 1].legend(loc='upper left')
    ax2_01.legend(loc='lower left')

    # Plot 3: Wartość księgowa na akcję
    axs[1, 0].plot(df_financial[okres], df_financial['wartosc_ksiegowa_na_akcje'], label='Wartość księgowa na akcję',
                   marker='o',
                   color='tab:green')
    ax2_10 = axs[1, 0].twinx()
    ax2_10.plot(df_financial[okres], df_financial['wartosc_ksiegowa_na_akcje_k/k'], label='Wartość księgowa na akcję '
                                                                                          'k/k',
                marker='o', color='black')
    axs[1, 0].set_title('Zysk netto')
    axs[1, 0].set_xlabel(okres)
    axs[1, 0].set_ylabel('Wartosc (PLN)')
    ax2_10.set_ylabel('Wartość księgowa na akcję k/k', color='black')
    axs[1, 0].tick_params(axis='x', rotation=90)
    axs[1, 0].grid(True)
    axs[1, 0].legend(loc='upper left')
    ax2_10.legend(loc='lower left')

    # Plot 4: C/WK
    axs[1, 1].plot(df_financial[okres], df_financial['C/WK'], label='C/WK', marker='o', color='tab:red')
    # ax2_11 = axs[1, 1].twinx()
    # ax2_11.plot(df_financial[okres], df_financial['ebitda_k/k'], label='EBITDA k/k', marker='o', color='black')
    axs[1, 1].set_title('C/WK')
    axs[1, 1].set_xlabel(okres)
    axs[1, 1].set_ylabel('Wartosc')
    # ax2_11.set_ylabel('EBITDA k/k', color='black')
    axs[1, 1].tick_params(axis='x', rotation=90)
    axs[1, 1].grid(True)
    axs[1, 1].legend(loc='upper left')
    # ax2_11.legend(loc='lower left')

    fig.suptitle(f'Wskaźniki wartości rynkowej dla {company.lower()}', fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    out_fig_path = os.path.join(output, f'{company}_assets_value_indicators.png')
    plt.savefig(out_fig_path)
    print(f"Saved assets value indicators plot at {out_fig_path}")
    plt.close()