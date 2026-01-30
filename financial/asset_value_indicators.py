import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re

from utils.html_utils import fetch_website_text
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
    br_url = f"https://www.biznesradar.pl/wskazniki-wartosci-rynkowej/{company_name.upper()}"

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

    #TODO POPRAWIC WCZYTYWANIE NIEKTORYCH WARTOŚCI - przypadki brzegowe obsluzyc

    header_row, value_rows_raw = data[7], data[8]

    # with open("wskazniki_debug.txt", "w", encoding="utf-8") as f:
    #     f.write(str(value_rows_raw))

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


    # table = {}
    # for row in value_rows:
    #     name, vals, dyn_kk, dyn_rr = parse_row(row)
    #     if not name:
    #         continue
    #     table[name] = vals
    #     # attach dynamics as separate rows
    #     table[f"{name} k/k"] = dyn_kk
    #     table[f"{name} r/r"] = dyn_rr
    #
    # df = pd.DataFrame(table, index=periods)
    # df = df.replace('', np.nan).dropna(axis=1, how='all')
    # # df = df.replace(np.nan, "")
    # df.index.name = "Okres"
    # df.reset_index(inplace=True, drop=False)
    # year_quarter = pd.DataFrame(df["Okres"].apply(lambda x: x.split("/")).tolist(), columns=["Rok", "Kwartał"])
    # df = pd.concat([year_quarter, df], axis=1)
    # return df