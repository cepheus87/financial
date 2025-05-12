import argparse
import requests
from bs4 import BeautifulSoup
import re
import dateutil
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
from datetime import datetime
import os
import json




@dataclass
class Sigmoid:
    x0: float
    k: float = 0.5
    min_val: float = 10
    max_val: float = 90

class HysteresisLoop:
    def __init__(self, x0_rise: float, x0_fall: float, slope: float = 0.5):
        self.rising_sigmoid = Sigmoid(x0=x0_rise, k=slope)
        self.falling_sigmoid = Sigmoid(x0=x0_fall, k=slope)

    @classmethod
    def sigmoid(cls, x: np.ndarray, min_val: float, max_val: float, k: float, x0: float):
        """
        Sigmoid function with parameterized min, max, slope, and crossing zero point.

        Parameters:
            x (float or np.ndarray): Input value(s).
            min_val (float): Minimum value of the sigmoid.
            max_val (float): Maximum value of the sigmoid.
            k (float): Slope (steepness) of the sigmoid.
            x0 (float): x-value where the sigmoid crosses the midpoint.

        Returns:
            float or np.ndarray: Output of the sigmoid function.
        """
        return min_val + (max_val - min_val) / (1 + np.exp(-k * (x - x0)))

#product_dict = asdict(product)

# Pass the dictionary to a function
# def print_product_info(product_info: dict):
#     for key, value in product_info.items():
#         print(f"{key}: {value}")
#
# # Example usage
# print_product_info(product_dict)

    def plot(self, x: np.ndarray):
        rise = asdict(self.rising_sigmoid)
        x_dict = {"x": x}
        rise.update(x_dict)
        y_rise = self.sigmoid(**rise)

        fall = asdict(self.falling_sigmoid)
        fall.update(x_dict)
        y_fall = self.sigmoid(**fall)

        # Plot the sigmoid function
        plt.plot(x, y_rise, label="Rising Sigmoid Function", color="green")
        plt.plot(x, y_fall, label="Falling Sigmoid Function", color="red")
        plt.xlabel("x")
        plt.ylabel("Non stock part")
        plt.title("Parameterized Sigmoid Function")
        plt.grid()
        plt.legend()
        plt.show()



def fetch_website_text(url: str) -> Optional[str]:

    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract and return the text content
        return soup.get_text()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def extract_single_pe_ratio(text: str) -> Tuple[str, datetime]:
    # Regex to extract the number (P/E Ratio)
    number_match = re.search(r'\b\d+\.\d+\b', text)

    # Regex to extract the date
    date_match = re.search(r'\b\d{2} \w{3} \d{4}\b', text)

    pe_ratio = number_match.group() if number_match else None
    if date_match:
        date = date_match.group()
        date = dateutil.parser.parse(date)
    else:
        date = None

    return pe_ratio, date

def extract_multiple_pe_ratios(text: str) -> List[Tuple[datetime, float]]:
    # Regex to extract the date and value
    date_pattern = r"\b\w{3} \d{1,2}, \d{4}\b"
    value_pattern = r"\b\d+\.\d+\b"

    # Extract dates and values
    dates = re.findall(date_pattern, text)
    values = re.findall(value_pattern, text)

    assert len(dates) == len(values)
    # dates = list(map(lambda x: dateutil.parser.parse(x), dates))
    # values = list(map(float, values))

    date_value_pairs = list(zip(dates, values))

    return date_value_pairs


class PERatioGetter:
    SNP500_URL = "https://worldperatio.com/index/sp-500/"
    PE_RATIO_HIST_URL = "https://www.multpl.com/s-p-500-pe-ratio/table/by-month"

    def __init__(self, force_fetch: bool = False, save_data: bool = True):
        self.force_fetch = force_fetch
        self.save_data = save_data
        self.data_dir = "data"
        self.data_hist_file = os.path.join(self.data_dir, "pe_ratio_hist.json")

    def get_pe_ratios(self) -> List[Tuple[str, str]]:
        if os.path.exists(self.data_hist_file) and not self.force_fetch:
            with open(self.data_hist_file, "r") as file:
                data = json.load(file)
                return data
        else:
            text = fetch_website_text(self.PE_RATIO_HIST_URL)
            if text:
                extracted_pe_ratios = extract_multiple_pe_ratios(text)
            else:
                raise ValueError(f"Failed to fetch data from the website {self.PE_RATIO_HIST_URL}")

            if self.save_data:
                os.makedirs(self.data_dir, exist_ok=True)
                with open(self.data_hist_file, "w") as file:
                    json.dump(extracted_pe_ratios, file)

            return extracted_pe_ratios



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch pe of S&P 500 from a website and compare with hysteresis loop")
    args = parser.parse_args()

    # website_text = fetch_website_text(SNP500_URL)
    # if website_text:
    #     print(extract_pe_ratio(website_text))

    rising_sigmoid = Sigmoid(x0=29, k=0.5)
    falling_sigmoid = Sigmoid(x0=21, k=0.5)



    # txt = fetch_website_text(pe_ratio_hist_url)

    # print(extract_multiple_pe_ratios(txt))

    pe_getter = PERatioGetter()
    extracted = pe_getter.get_pe_ratios()
    print(extracted)


# Example usage
    x0_rise = 29
    x0_fall = 21
    x = np.linspace( 10, 40, 500)
    min_val = 10
    max_val = 90
    k = 0.5

    hysteresis_loop = HysteresisLoop(x0_rise, x0_fall, slope=k)
    hysteresis_loop.plot(x)


    # check_values = np.arange(10, 40, 2.5)
    # results = sigmoid(check_values, min_val, max_val, k, x0_rise)
    # for x_, y_ in zip(check_values, results):
    #     print(x_, y_)
    #
    # y_rise = sigmoid(x, min_val, max_val, k, x0_rise)
    # y_fall = sigmoid(x, min_val, max_val, k, x0_fall)


