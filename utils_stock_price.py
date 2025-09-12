import matplotlib.pyplot as plt
import pandas as pd
import os

from utils_data import change_column_names

STOCK_PRICES= os.path.join("data", "stock_prices")

def draw_stock_price_graph(company_name: str, data_path: str=STOCK_PRICES) -> None:
    """
    Draws a graph of the stock price data.
    :param company_name: Name of the company
    """

    df = pd.read_excel(os.path.join(data_path, f"{company_name}_stock_price.xls"))
    df.columns = change_column_names(df.columns)

    df['data'] = pd.to_datetime(df['data'])
    df.set_index('data', inplace=True)
    df['kurs_zamkniecia'] = pd.to_numeric(df['kurs_zamkniecia'], errors='coerce')

    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df['kurs_zamkniecia'], label=company_name)
    plt.xlabel('Date')
    plt.ylabel('Stock Price')
    plt.title(f'Stock Price of {company_name}')
    # plt.legend()
    plt.grid()
    # plt.show()

def get_stock_prices_yearly(company_name, data_path: str=STOCK_PRICES) -> pd.DataFrame:
    """
    Fetches the stock prices of a company for each year.
    :param company_name: Name of the company
    :param data_path: Path to the directory where stock prices are stored
    :return: DataFrame containing the stock prices for each year
    """
    df = pd.read_excel(os.path.join(data_path, f"{company_name}_stock_price.xls"))
    df.columns = change_column_names(df.columns)

    df['data'] = pd.to_datetime(df['data'])
    df.set_index('data', inplace=True)
    df['kurs_zamkniecia'] = pd.to_numeric(df['kurs_zamkniecia'], errors='coerce')

    yearly_prices = df.resample('YE').last()  # Get the last price of each year
    return yearly_prices