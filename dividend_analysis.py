import argparse

from dividend_tools import get_data_of_single_company, save_companies_data, get_companies_results, save_div_plots

def main(company: str):
    # comp = "asbis"
    df = get_data_of_single_company(get_company_url(company), ignore_save_errors=True)
    save_companies_data(df, company, ignore_save_errors=True)
    #
    get_companies_results(company, save_results=True)

    save_div_plots(company)


def get_company_url(company: str) -> str:
    return f"https://www.stockwatch.pl/gpw/{company},notowania,dywidendy.aspx"

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Analyze dividends of a company.")
    parser.add_argument("-c", "--company", type=str, required=True, help="Company name")

    args = parser.parse_args()

    main(**vars(args))