import argparse
import re
import dateutil
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
from datetime import datetime
import os
import json

from html_utils import fetch_website_text

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
        self.sigmoids = {"rising": self.rising_sigmoid, "falling": self.falling_sigmoid}
        self._historical_data = None
        self.slope_estim_dates_num = 5
        self.current_sigmoid = None
        self.other_sigmoid = None
        self._min_level = 0
        self._max_level = 0
        self._last_pe_ratio = 0


    @property
    def historical_data(self):
        return self._historical_data

    @historical_data.setter
    def historical_data(self, data: List[Tuple[datetime, float]]):
        if not isinstance(data, list):
            raise ValueError("Historical data must be a list of tuples (datetime, float).")
        for item in data:
            if not (isinstance(item[0], datetime) and isinstance(item[1], float)):
                raise ValueError("Each item in historical data must be a tuple (datetime, float).")

        # Sort the data by date
        sorted_data = sorted(data, key=lambda x: x[0], reverse=False)
        self._historical_data = sorted_data

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

    @classmethod
    def sigmoid_reverse(cls, y: np.ndarray, min_val: float, max_val: float, k: float, x0: float):
        # reversed x = x0 - \frac{1}{k} \cdot \ln\left(\frac{\text{max_val} - \text{min_val}}{y - \text{min_val}} - 1\right)

        x = x0 - (1 / k) * np.log( (max_val - min_val) / (y - min_val) - 1)
        return x

    def check_values(self, x: np.ndarray):

        rise = asdict(self.rising_sigmoid)
        x_dict = {"x": x}
        rise.update(x_dict)
        y_rise = self.sigmoid(**rise)

        print("Rise sigmoid")
        for x_, y_ in zip(x, y_rise):
            print(x_, y_)

        fall = asdict(self.falling_sigmoid)
        fall.update(x_dict)
        y_fall = self.sigmoid(**fall)

        print("Fall sigmoid")
        for x_, y_ in zip(x, y_fall):
            print(x_, y_)

        # results = sigmoid(check_values, min_val, max_val, k, x0_rise)
        # for x_, y_ in zip(check_values, results):
        #     print(x_, y_)
        #
        # y_rise = sigmoid(x, min_val, max_val, k, x0_rise)
        # y_fall = sigmoid(x, min_val, max_val, k, x0_fall)

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

    # def chceck_which_sigmoid(self, date: datetime) -> Sigmoid:
    #     """
    #     Check which sigmoid to use based on the date.
    #     """
    #     if date.month >= 6:
    #         return self.rising_sigmoid
    #     else:
    #         return self.falling_sigmoid

    def evaluate_non_stock_part_old_ver(self, date: datetime, snp500_pe: float) -> float:
        """
        Evaluate the non-stock part based on the date and snp500_pe value.
        """

        month_begin = datetime(date.year, date.month, 1)
        dates = [entry[0] for entry in self._historical_data]
        pes = [entry[1] for entry in self._historical_data]

        idx = dates.index(month_begin)
        if month_begin == date:
            idx = idx - 1

        indexes = list(range(idx - self.slope_estim_dates_num, idx + 1))
        slope, intercept = np.polyfit(np.arange(len(indexes)), np.array(pes)[indexes], 1)

        # case: pe ratio is rising for whole period
        if slope > 0 and snp500_pe > pes[idx]:
            current_sigmoid = asdict(self.rising_sigmoid)
            current_sigmoid["x"] = snp500_pe
            return self.sigmoid(**current_sigmoid)
        # case: pe ratio is rising in previous periods, but now it is falling.
        elif slope > 0 and snp500_pe < pes[idx]:
            current_sigmoid = asdict(self.rising_sigmoid)
            current_sigmoid["x"] = pes[idx]
            non_stock_part = self.sigmoid(**current_sigmoid)
            other_sigmoid_y = asdict(self.falling_sigmoid)
            other_sigmoid_y["y"] = non_stock_part
            pe_to_change_to_other_sigmoid = self.sigmoid_reverse(**other_sigmoid_y)
            # move to another sigmoid
            if pe_to_change_to_other_sigmoid > snp500_pe:
                other_sigmoid_x = asdict(self.falling_sigmoid)
                other_sigmoid_x["x"] = snp500_pe
                return self.sigmoid(**other_sigmoid_x)
            else:
                return non_stock_part
        elif slope < 0 and snp500_pe < pes[idx]:
            current_sigmoid = asdict(self.falling_sigmoid)
            current_sigmoid["x"] = snp500_pe
            return self.sigmoid(**current_sigmoid)
        elif slope < 0 and snp500_pe > pes[idx]:
            current_sigmoid = asdict(self.falling_sigmoid)
            current_sigmoid["x"] = pes[idx]
            non_stock_part = self.sigmoid(**current_sigmoid)
            other_sigmoid_y = asdict(self.rising_sigmoid)
            other_sigmoid_y["y"] = non_stock_part
            pe_to_change_to_other_sigmoid = self.sigmoid_reverse(**other_sigmoid_y)
            # move to another sigmoid
            if pe_to_change_to_other_sigmoid < snp500_pe:
                other_sigmoid_x = asdict(self.rising_sigmoid)
                other_sigmoid_x["x"] = snp500_pe
                return self.sigmoid(**other_sigmoid_x)
            else:
                return non_stock_part
        else:
            raise ValueError("Slope is 0, no change in PE ratio.")

    def init_sigmoid(self, data: list[Tuple[datetime, float]]):
        """
        Determine sigmoid from data
        """

        # month_begin = datetime(date.year, date.month, 1)
        dates = [entry[0] for entry in data]
        pes = [entry[1] for entry in data]

        slope, intercept = np.polyfit(np.arange(len(dates)), np.array(pes), 1)

        self._last_pe_ratio = pes[-1]

        # case: pe ratio is rising for whole period
        if slope > 0:
            self.current_sigmoid = "rising"
            self.other_sigmoid = "falling"
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = pes[-1]
            self._max_level = self.sigmoid(**current_sigmoid)
        elif slope < 0:
            self.current_sigmoid = "falling"
            self.other_sigmoid = "rising"
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = pes[-1]
            self._min_level = self.sigmoid(**current_sigmoid)
        else:
            raise RuntimeError("Cannot determine slope, slope is 0.")

    def _switch_sigmoids(self, current_pe_ratio: float):
        if self.current_sigmoid == "rising":
            self.current_sigmoid = "falling"
            self.other_sigmoid = "rising"
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = current_pe_ratio
            self._min_level = self.sigmoid(**current_sigmoid)
            self._max_level = 0
            self._last_pe_ratio = current_pe_ratio
        else:
            self.current_sigmoid = "rising"
            self.other_sigmoid = "falling"
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = current_pe_ratio
            self._max_level = self.sigmoid(**current_sigmoid)
            self._min_level = 0
            self._last_pe_ratio = current_pe_ratio

    # def determine_sigmoid(self, data: list[Tuple[datetime, float]]):
    #
    #     #TODO: to jest żle, trzeba wprowadzic historie, gdzie byl poziom min/max, bo inaczej cofam poziom w kazdym
    #     # kroku sprawdzenia
    #
    #     # dates = [entry[0] for entry in data]
    #     pes = [entry[1] for entry in data]
    #     snp500_pe = pes.pop(-1)
    #
    #     # slope, intercept = np.polyfit(np.arange(len(pes)), np.array(pes), 1)
    #
    #     if snp500_pe > pes[-1] and self.current_sigmoid == "rising":
    #         return
    #     elif snp500_pe < pes[-1] and self.current_sigmoid == "falling":
    #         return
    #     # case: pe ratio was rising in previous periods, but now it is falling.
    #     elif snp500_pe < pes[-1] and self.current_sigmoid == "rising":
    #         current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
    #         current_sigmoid["x"] = pes[-1]
    #         non_stock_part = self.sigmoid(**current_sigmoid)
    #         other_sigmoid_y = asdict(self.sigmoids[self.other_sigmoid])
    #         other_sigmoid_y["y"] = non_stock_part
    #         pe_to_change_to_other_sigmoid = self.sigmoid_reverse(**other_sigmoid_y)
    #         # move to another sigmoid
    #         if pe_to_change_to_other_sigmoid > snp500_pe:
    #             self._switch_sigmoids()
    #             return
    #         else:
    #             return
    #     # case: pe ratio was falling in previous periods, but now it is rising.
    #     elif snp500_pe > pes[-1] and self.current_sigmoid == "falling":
    #         current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
    #         current_sigmoid["x"] = pes[-1]
    #         non_stock_part = self.sigmoid(**current_sigmoid)
    #         other_sigmoid_y = asdict(self.sigmoids[self.other_sigmoid])
    #         other_sigmoid_y["y"] = non_stock_part
    #         pe_to_change_to_other_sigmoid = self.sigmoid_reverse(**other_sigmoid_y)
    #         # move to another sigmoid
    #         if pe_to_change_to_other_sigmoid < snp500_pe:
    #             self._switch_sigmoids()
    #             return
    #         else:
    #             return
    #     else:
    #         raise RuntimeError("Sth went completely wrong")

    def get_non_stock_part(self, data: Tuple[datetime, float]):

        date = data[0]
        snp500_pe = data[1]

        # TODO: to jest zle zastanowic sie kiedy nalezy robic update last pe vs min/max level, bo to cos mi sie nie
        #  zgadza

        if snp500_pe > self._last_pe_ratio and self.current_sigmoid == "rising":
            self._last_pe_ratio = snp500_pe
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = snp500_pe
            self._max_level = self.sigmoid(**current_sigmoid)
            return
        elif snp500_pe < self._last_pe_ratio and self.current_sigmoid == "falling":
            self._last_pe_ratio = snp500_pe
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = snp500_pe
            self._min_level = self.sigmoid(**current_sigmoid)
            return
        # case: pe ratio was rising in previous periods, but now it is falling.
        elif snp500_pe < self._last_pe_ratio and self.current_sigmoid == "rising":
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = self._last_pe_ratio
            non_stock_part = self.sigmoid(**current_sigmoid)
            other_sigmoid_y = asdict(self.sigmoids[self.other_sigmoid])
            other_sigmoid_y["y"] = non_stock_part
            pe_to_change_to_other_sigmoid = self.sigmoid_reverse(**other_sigmoid_y)
            # move to another sigmoid
            if pe_to_change_to_other_sigmoid > snp500_pe:
                self._switch_sigmoids(snp500_pe)
                return
            else:
                return
        # case: pe ratio was falling in previous periods, but now it is rising.
        elif snp500_pe > self._last_pe_ratio and self.current_sigmoid == "falling":
            current_sigmoid = asdict(self.sigmoids[self.current_sigmoid])
            current_sigmoid["x"] = self._last_pe_ratio
            non_stock_part = self.sigmoid(**current_sigmoid)
            other_sigmoid_y = asdict(self.sigmoids[self.other_sigmoid])
            other_sigmoid_y["y"] = non_stock_part
            pe_to_change_to_other_sigmoid = self.sigmoid_reverse(**other_sigmoid_y)
            # move to another sigmoid
            if pe_to_change_to_other_sigmoid < snp500_pe:
                self._switch_sigmoids(snp500_pe)
                return
            else:
                return
        else:
            raise RuntimeError("Sth went completely wrong")

    def calculate(self, date: datetime, snp500_pe: float, init_sigmoid: bool = False) -> float:
        # TODO: HERE LAST WORK - use it

        """
        Evaluate the non-stock part based on the date and snp500_pe value.
        """

        # month_begin = datetime(date.year, date.month, 1)
        # dates = [entry[0] for entry in self._historical_data]
        # pes = [entry[1] for entry in self._historical_data]

        # idx = dates.index(month_begin)
        # if month_begin == date:
        #     idx = idx - 1

        if init_sigmoid:
            self.init_sigmoid(self._historical_data[:self.slope_estim_dates_num])

        for entry in self._historical_data[self.slope_estim_dates_num:]:
            self.get_non_stock_part(entry) # <- here decide if only determine sigmoid or also calculate non stock
            # part (work inside)


        indexes = list(range(idx - self.slope_estim_dates_num, idx + 1))
        slope, intercept = np.polyfit(np.arange(len(indexes)), np.array(pes)[indexes], 1)

        # case: pe ratio is rising for whole period




    def evaluate_historical_data(self, start_date: datetime = None):
        if not self._historical_data:
            raise ValueError("Historical data is not set.")

        if start_date is not None:
            selected_data = [entry for entry in self._historical_data if entry[0] >= start_date]
        else:
            selected_data = self._historical_data

        for date, snp500_pe in selected_data:


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
                return self.change_to_date_float(data)
        else:
            text = fetch_website_text(self.PE_RATIO_HIST_URL)
            if text:
                extracted_pe_ratios = self.extract_multiple_pe_ratios(text)
            else:
                raise ValueError(f"Failed to fetch data from the website {self.PE_RATIO_HIST_URL}")

            if self.save_data:
                os.makedirs(self.data_dir, exist_ok=True)
                with open(self.data_hist_file, "w") as file:
                    json.dump(extracted_pe_ratios, file)

            return self.change_to_date_float(extracted_pe_ratios)

    @staticmethod
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

    @staticmethod
    def change_to_date_float(data: List[Tuple[str, str]]) -> List[Tuple[datetime, float]]:
        """
        Convert date strings to datetime objects and values to floats.
        """
        date_value_pairs = []
        for date_str, value_str in data:
            date = dateutil.parser.parse(date_str)
            value = float(value_str)
            date_value_pairs.append((date, value))
        return date_value_pairs





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
    check_values_x = np.arange(10, 41, 2.5)
    hysteresis_loop.check_values(check_values_x)



    hysteresis_loop.plot(x)

    hysteresis_loop.historical_data = extracted
    non_stock_part = hysteresis_loop.evaluate_non_stock_part(datetime(2025, 5, 15), 28.2)
    non_stock_part = hysteresis_loop.evaluate_non_stock_part(datetime(2023, 10, 1), 25)
    non_stock_part = hysteresis_loop.evaluate_non_stock_part(datetime(2023, 10, 1), 23)
    non_stock_part = hysteresis_loop.evaluate_non_stock_part(datetime(2023, 10, 1), 16)
    non_stock_part = hysteresis_loop.evaluate_non_stock_part(datetime(2023, 10, 1), 12)



    a = 1
    # results = sigmoid(check_values, min_val, max_val, k, x0_rise)
    # for x_, y_ in zip(check_values, results):
    #     print(x_, y_)
    #
    # y_rise = sigmoid(x, min_val, max_val, k, x0_rise)
    # y_fall = sigmoid(x, min_val, max_val, k, x0_fall)




    # test for sigmoid, reverse
    # rise_base = asdict(hysteresis_loop.rising_sigmoid)
    # x_dict = {"x": check_values_x}
    # from copy import deepcopy
    #
    # rise = deepcopy(rise_base)
    # rise2 = deepcopy(rise_base)
    # rise.update(x_dict)
    #
    #
    # y_rise = hysteresis_loop.sigmoid(**rise)
    # rise2.update({"y": y_rise})
    #
    # for x_, y_, x_rev in zip(check_values_x, y_rise, hysteresis_loop.sigmoid_reverse(**rise2)):
    #     print(x_, y_, x_rev )