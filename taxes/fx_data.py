import os
import pandas as pd
import re
from typing import List, Dict



from utils.html_utils import get_binary_response

class FXData:
    BASE_FILENAME = "archiwum_tab_a_YYYY.csv"
    BASE_NBP_URL = f"https://static.nbp.pl/dane/kursy/Archiwum/"
    CACHED_DATA_PATH = os.path.join( "..", "data", "fx_data")
    DATE_OLD_NAME = "data"
    DATE_NEW_NAME = "date"


    def __init__(self, years: List[str]):
        if not isinstance(years, list):
            raise TypeError("Years must be a list.")
        self.years = years
        self.year_urls = self._get_urls(years)

        if not os.path.exists(self.CACHED_DATA_PATH):
            os.makedirs(self.CACHED_DATA_PATH)

        self.cached_years = self.get_cached_years()
        # TODO add checking current year if ranged data is already downloaded
        self.download_data(list(set(years).difference(self.cached_years)))
        self._full_data = None

    @property
    def data(self) -> pd.DataFrame:
        if self._full_data is None:
            self._load_all_data()
        return self._full_data.copy()

    def _get_urls(self, years: List[str]) -> Dict:
        return {year: f"{self.BASE_NBP_URL}{self._get_filename(year)}" for year in years}

    def add_year(self, year: str):
        if year not in self.years:
            self.years.append(year)
            self.year_urls.update(self._get_urls([year]))
            self.download_data(list({year}.difference(self.cached_years)))

    def _load_all_data(self):
        dfs = []
        for year in self.years:
            dfs.append(self.get_data(year))
        self._full_data = pd.concat(dfs, ignore_index=True)

    def _get_filename(self, year: str) -> str:
        return self.BASE_FILENAME.replace("YYYY", str(year))

    def get_cached_years(self) -> List[str]:
        filenames = os.listdir(self.CACHED_DATA_PATH)
        return [os.path.splitext(filename)[0].split("_")[-1] for filename in filenames]

    def download_data(self, years: List[str]):
        for year in years:
            url = self.year_urls[year]
            target_filename = os.path.join(self.CACHED_DATA_PATH, url.split("/")[-1])
            print(f"Downloading {year}...")
            get_binary_response(url, target_filename)

        self.cached_years = self.get_cached_years()

    def get_data(self, year: str) -> pd.DataFrame:
        if year in self.cached_years:

            df =  pd.read_csv(os.path.join(self.CACHED_DATA_PATH, self._get_filename(year)), sep=";",
                              encoding="cp1250", skiprows=[1], )

            return self._process_data(df)
        else:
            raise ValueError(f"Data for year {year} is not available. Sth went wrong.")

    def get_fx_value(self, date: str, currency: str) -> float:

        def find_currency_column_index(columns, currency):
            for idx, col in enumerate(columns):
                match = re.search(r'^\d*([A-Za-z]+)$', col)
                if match and match.group(1) == currency:
                    return idx
            return -1  # Not found

        df = self.data.copy()
        date = pd.to_datetime(date) #, format="%Y%m%d")

        row = df[df[self.DATE_NEW_NAME] == date]
        if row.empty:
            raise ValueError(f"No data available for date {date}")

        idx = find_currency_column_index(df.columns, currency)
        if idx == -1:
            raise ValueError(f"Currency {currency} is not available for date {date}")

        return float(row.iloc[0,idx])

    @classmethod
    def _process_data(cls, df: pd.DataFrame) -> pd.DataFrame:

        new_df = df.copy()
        new_df = new_df.iloc[:-3]
        new_df = new_df.iloc[:, :-3]

        new_df = new_df.astype(str).apply(lambda col: col.map(lambda x: x.strip().replace(",", ".")))

        new_df.rename(columns={cls.DATE_OLD_NAME: cls.DATE_NEW_NAME}, inplace=True)
        new_df[cls.DATE_NEW_NAME] = pd.to_datetime(new_df[cls.DATE_NEW_NAME], format="%Y%m%d")

        currencies = list(set(new_df.columns) - set([cls.DATE_NEW_NAME]))
        new_df[currencies] = new_df[currencies].astype(float)

        return new_df