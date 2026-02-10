import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re

from utils.html_utils import fetch_website_text
from utils.setup import ProjectConfig

YEARS_RANGE = 10

def get_financial_quarter_data_br(company_name: str) -> list:
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

def get_financial_gain_loss_table(data: list) -> pd.DataFrame:
    #TODO add some checks if data format is not changed on the website

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
    df.reset_index(inplace=True, drop=False)
    year_quarter = pd.DataFrame(df["Okres"].apply(lambda x: x.split("/")).tolist(), columns=["Rok", "Kwartał"])
    df = pd.concat([year_quarter, df], axis=1)
    return df


def save_financial_gl_plots(company: str, df_financial):

    #TODO: create yearly version

    rok = "rok"
    okres = "okres"

    df_financial = df_financial.copy()

    output = os.path.join(ProjectConfig.base_data_path, "plots")
    os.makedirs(output, exist_ok=True)

    max_year = max(df_financial[rok].max(), df_financial[rok].max())
    df_financial = df_financial[df_financial[rok] >= max_year - YEARS_RANGE]

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Przychody ze sprzedaży
    axs[0, 0].plot(df_financial[okres], df_financial['przychody_ze_sprzedazy'], label='Przychody ze sprzedaży',
                   marker='o', color='tab:blue')
    ax2_00 = axs[0, 0].twinx()
    ax2_00.plot(df_financial[okres], df_financial['przychody_ze_sprzedazy_k/k'], label='Przychody ze sprzedaży k/k',
                marker='o', color='black')
    axs[0, 0].set_title('Przychody ze sprzedaży')
    axs[0, 0].set_xlabel(okres)
    axs[0, 0].set_ylabel('Wartosc (k PLN)')
    ax2_00.set_ylabel('Przychody ze sprzedaży k/k', color='black')
    axs[0, 0].tick_params(axis='x', rotation=90)
    axs[0, 0].grid(True)

    # Plot 2: Zysk operacyjny (EBIT)
    axs[0, 1].plot(df_financial[okres], df_financial['zysk_operacyjny_(ebit)'], label='Zysk operacyjny (EBIT)',
                   marker='o', color='tab:orange')
    ax2_01 = axs[0, 1].twinx()
    ax2_01.plot(df_financial[okres], df_financial['zysk_operacyjny_(ebit)_k/k'], label='Zysk operacyjny (EBIT) k/k',
                marker='o', color='black')
    axs[0, 1].set_title('Zysk operacyjny (EBIT)')
    axs[0, 1].set_xlabel(okres)
    axs[0, 1].set_ylabel('Wartosc (k PLN)')
    ax2_01.set_ylabel('Zysk operacyjny (EBIT) k/k', color='black')
    axs[0, 1].tick_params(axis='x', rotation=90)
    axs[0, 1].grid(True)

    # Plot 3: Zysk netto
    axs[1, 0].plot(df_financial[okres], df_financial['zysk_netto'], label='Zysk netto', marker='o', color='tab:green')
    ax2_10 = axs[1, 0].twinx()
    ax2_10.plot(df_financial[okres], df_financial['zysk_netto_k/k'], label='Zysk netto k/k', marker='o', color='black')
    axs[1, 0].set_title('Zysk netto')
    axs[1, 0].set_xlabel(okres)
    axs[1, 0].set_ylabel('Wartosc (k PLN)')
    ax2_10.set_ylabel('Zysk netto k/k', color='black')
    axs[1, 0].tick_params(axis='x', rotation=90)
    axs[1, 0].grid(True)

    # Plot 4: EBITDA
    axs[1, 1].plot(df_financial[okres], df_financial['ebitda'], label='EBITDA', marker='o', color='tab:red')
    ax2_11 = axs[1, 1].twinx()
    ax2_11.plot(df_financial[okres], df_financial['ebitda_k/k'], label='EBITDA k/k', marker='o', color='black')
    axs[1, 1].set_title('EBITDA')
    axs[1, 1].set_xlabel(okres)
    axs[1, 1].set_ylabel('Wartosc (k PLN)')
    ax2_11.set_ylabel('EBITDA k/k', color='black')
    axs[1, 1].tick_params(axis='x', rotation=90)
    axs[1, 1].grid(True)

    # version without k/k plots

    # # Plot 1: Przychody ze sprzedaży
    # axs[0, 0].plot(df_profitability[okres], df_profitability['przychody_ze_sprzedazy'], label='Przychody ze sprzedaży',
    #                marker='o', color='tab:blue')
    # axs[0, 0].set_title('Przychody ze sprzedaży')
    # axs[0, 0].set_xlabel(okres)
    # axs[0, 0].set_ylabel('Wartosc (k PLN)')
    # axs[0, 0].tick_params(axis='x', rotation=90)
    # axs[0, 0].grid(True)
    #
    # # Plot 2: Zysk operacyjny (EBIT)
    # axs[0, 1].plot(df_profitability[okres], df_profitability['zysk_operacyjny_(ebit)'], label='Zysk operacyjny (EBIT)',
    #                marker='o', color='tab:orange')
    # axs[0, 1].set_title('Zysk operacyjny (EBIT)')
    # axs[0, 1].set_xlabel(okres)
    # axs[0, 1].set_ylabel('Wartosc (k PLN)')
    # axs[0, 1].tick_params(axis='x', rotation=90)
    # axs[0, 1].grid(True)
    #
    # # Plot 3: Zysk netto
    # axs[1, 0].plot(df_profitability[okres], df_profitability['zysk_netto'], label='Zysk netto', marker='o', color='tab:green')
    # axs[1, 0].set_title('Zysk netto')
    # axs[1, 0].set_xlabel(okres)
    # axs[1, 0].set_ylabel('Wartosc (k PLN)')
    # axs[1, 0].tick_params(axis='x', rotation=90)
    # axs[1, 0].grid(True)
    #
    # # Plot 4: EBITDA
    # axs[1, 1].plot(df_profitability[okres], df_profitability['ebitda'], label='EBITDA', marker='o', color='tab:red')
    # axs[1, 1].set_title('EBITDA')
    # axs[1, 1].set_xlabel(okres)
    # axs[1, 1].set_ylabel('Wartosc (k PLN)')
    # axs[1, 1].tick_params(axis='x', rotation=90)
    # axs[1, 1].grid(True)

    fig.suptitle(f'Przychody/Straty dla {company.lower()}', fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    out_fig_path = os.path.join(output, f'{company}_financial_gain_loss.png')
    plt.savefig(out_fig_path)
    print(f"Saved financial gain/loss plot at {out_fig_path}")
    plt.close()