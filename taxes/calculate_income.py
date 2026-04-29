from typing import List

from utils.html_utils import fetch_website_text, get_binary_response


class FXData:

    BASE_NBP_URL = "https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_YYYY.csv"

    def __init__(self, years: List[str], cached_data_path: str):
        self.years = years
        self.year_urls = [self.BASE_NBP_URL.replace("YYYY", str(year)) for year in self.years]
        self.cached_data_path = cached_data_path



def main():
    url2 = "https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_2025.csv"

    url = "https://nbp.pl/statystyka-i-sprawozdawczosc/kursy/archiwum-tabela-a-csv-xls/"

    # text = fetch_website_text(url)

    # get_binary_response(url2, "./archiwum_tab_a_2025.csv")

    fx = FXData([2023, 2024])
    print(fx.year_urls)

    a = 1


if __name__ == "__main__":
    main()