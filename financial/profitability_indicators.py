import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re

from utils.html_utils import fetch_website_text
from utils.setup import ProjectConfig
from utils.utils_data import get_br_name_mapping
from financial.gain_loss_tools import YEARS_RANGE

# Patterns for packed value rows
_VALUE_RE = re.compile(r"\s*(-?[\d\s]*(?:,\d{2})?%)")
_DYN_RE = re.compile(r"\s*(k/k|r/r)\s+([+-]?\d+(?:[.,]\d{2})?%)")
_BRANZA_RE = re.compile(r"\s*~branża\s+([+-]?\d+(?:[.,]\d{2})?%)")



def get_profitability_indicators_br(company_name: str) -> list:
    br_name = get_br_name_mapping(company_name)
    br_url = f"https://www.biznesradar.pl/wskazniki-rentownosci/{br_name.upper()}"

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

def get_profitability_indicators_table(data: list) -> pd.DataFrame:
    #TODO add some checks if data format is not changed on the website

    header_row, value_rows_raw = data[9], data[10]

    value_rows = []
    for row in value_rows_raw:
        if row.startswith("ROIC"):
            value_rows.append(row)
            break
        else:
            value_rows.append(row)

    # Keep only the "YYYY/Qx" tokens, drop bracketed month tags
    periods = [h for h in header_row if not h.startswith("(")]


    # TODO: quite similar to parse_percentage() from utils_data
    def _get_percentage(val: str) -> float:
        if isinstance(val, str):
            val = val.replace("%", "").replace(",", ".").strip()
            try:
                val = float(val) / 100.0
            except ValueError:
                return np.nan
            return val

    def _parse_row(row_text: str, periods_count: int):
        # split into name + remainder (first digit starts data)
        m = re.match(r"([^\d+-]+)(.*)", row_text.strip())
        if not m:
            return None, [], [], []
        name, tail = m.group(1).strip(), m.group(2).strip()

        values, dyn_kk, dyn_rr, sector_vals = [], [], [], []
        idx = 0

        while idx < len(tail) and len(values) < periods_count:
            v_match = _VALUE_RE.match(tail, idx)
            if not v_match or not v_match.group(1):
                break
            raw_val = v_match.group(1)
            perc = _get_percentage(raw_val)
            values.append(perc)
            idx = v_match.end()

            kk_val, rr_val, sector_val = "", "", ""
            while True:
                b_match = _BRANZA_RE.match(tail, idx)
                if b_match:
                    idx = b_match.end()
                    sector_val = b_match.group(1)

                d_match = _DYN_RE.match(tail, idx)
                if d_match:
                    typ, pct = d_match.groups()
                    if typ == "k/k":
                        kk_val = _get_percentage(pct)
                    else:
                        rr_val = _get_percentage(pct)
                    idx = d_match.end()

                if not d_match and not b_match:
                    break

            sector_vals.append(_get_percentage(sector_val))
            dyn_kk.append(kk_val)
            dyn_rr.append(rr_val)


        n = periods_count
        values = (values + [""] * n)[:n]
        dyn_kk = (dyn_kk + [""] * n)[:n]
        dyn_rr = (dyn_rr + [""] * n)[:n]
        sector_vals = (sector_vals + [""] * n)[:n]
        return name, values, dyn_kk, dyn_rr # not returning sector_vals, there can be 3 values per period (for val,
        # kk, rr)

    table = {}
    n = len(periods)
    for row in value_rows:
        name, vals, dyn_kk, dyn_rr = _parse_row(row, n)
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

def save_profitability_indicators_plots(company: str, df_profitability):

    #TODO: create yearly version

    rok = "rok"
    okres = "okres"

    df_profitability = df_profitability.copy()

    output = os.path.join(ProjectConfig.base_data_path, "plots")
    os.makedirs(output, exist_ok=True)

    max_year = max(df_profitability[rok].max(), df_profitability[rok].max())
    df_profitability = df_profitability[df_profitability[rok] >= max_year - YEARS_RANGE]

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1:
    main_name = "ROIC"
    axs[0, 0].plot(df_profitability[okres], df_profitability['roic'], label=main_name,
                   marker='o', color='tab:blue')
    ax2_00 = axs[0, 0].twinx()
    ax2_00.plot(df_profitability[okres], df_profitability['roic_k/k'], label=f'{main_name} k/k',
                marker='o', color='black')
    axs[0, 0].set_title(main_name)
    axs[0, 0].set_xlabel(okres)
    axs[0, 0].set_ylabel('Współczynnik')
    ax2_00.set_ylabel(f'{main_name} k/k', color='black')
    axs[0, 0].tick_params(axis='x', rotation=90)
    axs[0, 0].grid(True)
    axs[0, 0].legend(loc='upper left')
    ax2_00.legend(loc='upper right')

    # Plot 2:
    main_name = "ROE"
    axs[0, 1].plot(df_profitability[okres], df_profitability['roe'], label=main_name,
                   marker='o', color='tab:orange')
    ax2_01 = axs[0, 1].twinx()
    ax2_01.plot(df_profitability[okres], df_profitability['roe_k/k'], label=f'{main_name} k/k',
                marker='o', color='black')
    axs[0, 1].set_title(main_name)
    axs[0, 1].set_xlabel(okres)
    axs[0, 1].set_ylabel('Współczynnik')
    ax2_01.set_ylabel(f'{main_name} k/k', color='black')
    axs[0, 1].tick_params(axis='x', rotation=90)
    axs[0, 1].grid(True)
    axs[0, 1].legend(loc='upper left')
    ax2_01.legend(loc='upper right')

    # Plot 3:
    main_name = "ROA"
    axs[1, 0].plot(df_profitability[okres], df_profitability['roa'], label=main_name, marker='o', color='tab:green')
    ax2_10 = axs[1, 0].twinx()
    ax2_10.plot(df_profitability[okres], df_profitability['roa_k/k'], label=f'{main_name} k/k', marker='o',
                color='black')
    axs[1, 0].set_title(main_name)
    axs[1, 0].set_xlabel(okres)
    axs[1, 0].set_ylabel('Współczynnik')
    ax2_10.set_ylabel(f'{main_name} k/k', color='black')
    axs[1, 0].tick_params(axis='x', rotation=90)
    axs[1, 0].grid(True)
    axs[1, 0].legend(loc='upper left')
    ax2_10.legend(loc='upper right')

    # Plot 4:
    main_name = "marża zysku netto"
    axs[1, 1].plot(df_profitability[okres], df_profitability['marza_zysku_netto'], label=main_name, marker='o',
                   color='tab:red')
    ax2_11 = axs[1, 1].twinx()
    ax2_11.plot(df_profitability[okres], df_profitability['marza_zysku_netto_k/k'], label=f'{main_name} k/k', marker='o',
                color='black')
    axs[1, 1].set_title(main_name)
    axs[1, 1].set_xlabel(okres)
    axs[1, 1].set_ylabel('Współczynnik')
    ax2_11.set_ylabel(f'{main_name} k/k', color='black')
    axs[1, 1].tick_params(axis='x', rotation=90)
    axs[1, 1].grid(True)
    axs[1, 1].legend(loc='upper left')
    ax2_11.legend(loc='upper right')

    fig.suptitle(f'Wskaźniki rentowności dla {company.lower()}', fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    out_fig_path = os.path.join(output, f'{company}_profitability_indicators.png')
    plt.savefig(out_fig_path)
    print(f"Saved profitability indicators plot at {out_fig_path}")
    plt.close()