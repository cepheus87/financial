import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re

from utils.html_utils import fetch_website_text
from utils.setup import ProjectConfig
from utils.utils_data import get_br_name_mapping, find_date_element_index
from financial.gain_loss_tools import YEARS_RANGE

# Patterns for packed value rows
_VALUE_RE = re.compile(r"\s*(-?[\d\s]*(?:,\d+)?)")
_FIRST_VALUE_RE = re.compile(r"\s*(-?[\d\s]*(?:,\d{2})?)")
_DYN_RE = re.compile(r"\s*(k/k|r/r)\s+([+-]?\d+(?:\.\d+)?%)")
_BRANZA_RE = re.compile(r"\s*~branża\s+[+-]?\d+(?:\.\d+)?%")

COLS_TO_SKIP = ["Płatności z tytułu umów leasingu"]

def get_cash_flow_br(company_name: str) -> list:
    br_name = get_br_name_mapping(company_name)
    br_url = f"https://www.biznesradar.pl/raporty-finansowe-przeplywy-pieniezne/{br_name.upper()},Q"

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

def get_cash_flow_table(data: list) -> pd.DataFrame:
    #TODO add some checks if data format is not changed on the website
    date_idx = find_date_element_index(data)
    if date_idx == -1:
        raise ValueError("Could not find date element in data")

    header_row, value_rows_raw = data[date_idx], data[date_idx + 1]

    value_rows = []
    for row in value_rows_raw:
        if row.startswith("Free Cash Flow"):
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

            prices.append(val[:dot_indexes[0] + float_shift])
            for i, idx in enumerate(dot_indexes[:-1]):
                prices.append(val[idx + float_shift:dot_indexes[i + 1] + float_shift])

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

        if name == "Data publikacji":
            for i in range(len(periods)):
                values.append(tail[i*10:i*10+10])
        elif name == "Dywidenda":
            #TODO:
            values.extend([] * periods_count)
            # prices = _div_to_prices(tail)
            # values.extend(prices)

        elif name == "Skup akcji":
            # TODO:
            values.extend([] * periods_count)
            # shares_num = _div_to_float(tail)
            # values.extend(shares_num)
        elif name == "Emisja akcji":
            #TODO:
            values.extend([] * periods_count)
        else:
            while idx < len(tail) and len(values) < periods_count:
                if idx == 0:
                    v_match = _FIRST_VALUE_RE.match(tail, idx)
                else:
                    v_match = _VALUE_RE.match(tail, idx)
                if not v_match or not v_match.group(1):
                    break
                raw_val = v_match.group(1)
                clean_val = raw_val.replace(" ", "").replace(",", ".")
                # float_vals = _div_to_float(clean_val)
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
        if not name or name in COLS_TO_SKIP:
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