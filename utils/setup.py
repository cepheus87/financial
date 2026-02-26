from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class ProjectConfig:
    base_path: str = str(Path(os.path.abspath(__file__)).parents[1])
    base_data_path: str = os.path.join(base_path, "data")
    base_companies_dividends_path: str = os.path.join(base_data_path, "dividends")
    isin_path: str = os.path.join(base_data_path, "isin.json")
    base_companies_results_path: str = os.path.join(base_data_path, "results")
    br_names_mapping_path: str = os.path.join(base_data_path, "br_mapping.json")
    financial_path: str = os.path.join(base_data_path, "financial")

data_categories_paths = {
    "financial": ProjectConfig.financial_path,
}