import json
from typing import List, Optional, Union
import pandas as pd
import warnings

from setup import ProjectConfig

polish_to_english = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ"
)


def change_column_names(columns: List[str]) -> List[str]:
    changed = list()
    for col in columns:
        col = col.translate(polish_to_english)
        col = col.strip()
        col = col.replace(" ", "_")
        col = col.replace(".", "")
        col = col.lower()
        changed.append(col)

    return changed

def parse_percentage(value: str) -> Union[float, str]:

    if not pd.isna(value):
        try:
            if "%" in value:
                value = value.replace(",", ".").replace("%", "").strip()
                return float(value) / 100.0
        except ValueError:
            warnings.warn(f"Could not parse percentage value: {value}")
            return value
    else:
        return value

def get_br_name_mapping(company: str) -> str:
    with open(ProjectConfig.br_names_mapping_path, "r") as f:
        mapping = json.load(f)

    if mapping.get(company):
        return mapping[company]
    else:
        raise ValueError(f"No BR name mapping found for company: {company}")

def process_financial_gain_loss_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = change_column_names(df.columns.tolist())
    kk_rr_columns = [col for col in df.columns if "k/k" in col or "r/r" in col]

    for col in kk_rr_columns:
        df[col] = df[col].apply(parse_percentage)

    float_cols = [col for col in df.columns[4:] if col not in kk_rr_columns]
    df[float_cols] = df[float_cols].apply(pd.to_numeric)
    df["rok"] = df["rok"].astype(int)

    return df

def process_profitability_indicators_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = change_column_names(df.columns.tolist())
    df["rok"] = df["rok"].astype(int)

    return df


