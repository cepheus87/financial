import os
import pandas as pd
from typing import List


from utils.html_utils import fetch_website_text, get_binary_response


class FXData:
    BASE_FILENAME = "archiwum_tab_a_YYYY.csv"
    BASE_NBP_URL = f"https://static.nbp.pl/dane/kursy/Archiwum/"
    CACHED_DATA_PATH = os.path.join( "..", "data", "fx_data")


    def __init__(self, years: List[str]):
        self.years = years
        self.year_urls = {year: f"{self.BASE_NBP_URL}{self.get_filename(year)}" for year in self.years}

        if not os.path.exists(self.CACHED_DATA_PATH):
            os.makedirs(self.CACHED_DATA_PATH)

        self.cached_years = self.get_cached_years()
        self.download_data(list(set(years).difference(self.cached_years)))


    def get_filename(self, year: str) -> str:
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

            df =  pd.read_csv(os.path.join(self.CACHED_DATA_PATH, self.get_filename(year)), sep=";",
                               encoding="cp1250", skiprows=[1],)
                               # parse_dates=True, infer_datetime_format=True)
            return self.process_data(df)
        else:
            raise ValueError(f"Data for year {year} is not available. Sth went wrong.")

    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:

        return_df = df.copy()
        #TODO change , to .
        return_df = return_df.iloc[:-3]
        return_df["data"] = pd.to_datetime(return_df["data"], format="%Y%m%d")
        return return_df


def main():
    url2 = "https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_2025.csv"

    url = "https://nbp.pl/statystyka-i-sprawozdawczosc/kursy/archiwum-tabela-a-csv-xls/"

    # text = fetch_website_text(url)

    # get_binary_response(url2, "./archiwum_tab_a_2025.csv")

    fx = FXData(["2023", "2025"])
    print(fx.year_urls)

    df = fx.get_data("2023")

    a = 1


if __name__ == "__main__":
    main()