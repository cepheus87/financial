

from fx_data import FXData
from taxes import trades

from trades import Statements



def main():
    url2 = "https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_2025.csv"

    url = "https://nbp.pl/statystyka-i-sprawozdawczosc/kursy/archiwum-tabela-a-csv-xls/"

    # text = fetch_website_text(url)

    # get_binary_response(url2, "./archiwum_tab_a_2025.csv")

    statements = Statements("statements.csv")
    trades = statements.split_statement_into_trade_entries()

    fx = FXData(["2023", "2025"])
    print(fx.year_urls)

    # df = fx.get_data("2023")

    data = fx.data

    fx_val = fx.get_fx_value("2025-12-02", "USD")

    a = 1


if __name__ == "__main__":
    main()