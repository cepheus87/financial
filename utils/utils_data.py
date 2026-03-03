import json
import os
from typing import List, Optional, Union, Callable
import pandas as pd
import re
import warnings

from numpy.ma.extras import apply_along_axis

from utils.setup import ProjectConfig, data_categories_paths

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

def process_assets_value_indicators_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = change_column_names(df.columns.tolist())
    kk_rr_columns = [col for col in df.columns if "k/k" in col or "r/r" in col]

    for col in kk_rr_columns:
        df[col] = df[col].apply(parse_percentage)

    float_cols = [col for col in df.columns[3:] if col not in kk_rr_columns]
    df[float_cols] = df[float_cols].apply(pd.to_numeric)
    df["rok"] = df["rok"].astype(int)

    return df

def process_profitability_indicators_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = change_column_names(df.columns.tolist())
    df["rok"] = df["rok"].astype(int)

    return df

def process_cash_flow_df(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError()

    df = df.copy()

    df.columns = change_column_names(df.columns.tolist())
    df["rok"] = df["rok"].astype(int)

    return df

def find_date_element_index(data: list) -> int:
    for i, item in enumerate(data):
        if re.match(r"\d{4}/Q\d+", item[0]):
            return i

    return -1

class DataCacher:
    def __init__(self, company: str, variable_name: str, data_category: str, download: bool,
                 getter: Callable[[str], list], processor: Callable[[list], pd.DataFrame]):
        self.company_name = company
        self.variable_name = variable_name
        self.data_category = data_category
        self.files_data_path = data_categories_paths.get(data_category)
        if not self.files_data_path:
            raise ValueError(f"Invalid data category: {data_category}")
        self.file_name = f"{self.company_name}_{self.variable_name}.csv"
        self.download = download
        self.getter = getter
        self.processor = processor

    def check_if_cached(self) -> bool:
        file_path = os.path.join(self.files_data_path, f"{self.company_name}_{self.variable_name}.csv")
        return os.path.exists(file_path)

    def save_df_data(self, df: pd.DataFrame):
        if not os.path.exists(self.files_data_path):
            os.makedirs(self.files_data_path)
        df.to_csv(os.path.join(self.files_data_path, self.file_name), index=False)

    def download_data(self) -> pd.DataFrame:
        data = self.getter(self.company_name)
        df = self.processor(data)
        self.save_df_data(df)
        return df

    def load_df_data(self) -> pd.DataFrame:
        if self.download:
            return self.download_data()
        else:
            if self.check_if_cached():
                return pd.read_csv(os.path.join(self.files_data_path, self.file_name))
            else:
                raise RuntimeError(f"Data for {self.company_name} and variable {self.variable_name} not found in cache, and download is disabled.")
