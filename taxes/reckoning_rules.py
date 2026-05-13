from dataclasses import dataclass
from datetime import date, timedelta
from workalendar.europe import Poland

POLAND_EXTRA_HOLIDAYS = [
    date(2020, 12, 24),
]

class PolandCalFix(Poland):
    def is_working_day(self, day,
                           extra_working_days=None, extra_holidays=None):
        if day.month == 12 and day.day == 24: # 24.12 is not a working day
            return False
        return super().is_working_day(day, extra_working_days, extra_holidays)

@dataclass
class ReckoningRulesConfig:
    days_of_reckoning_by_stock: int = 2 # number of days after transaction in which stock proceeded transaction
    fx_calculation_day: int = 1  # number of days before proceeded transaction to take average fx value


class ReckoningRules:
    def __init__(self, config: ReckoningRulesConfig = ReckoningRulesConfig()):
        self.config = config
        self.cal = PolandCalFix()

    def get_day_of_fx_calculation(self, transaction_date: date) -> date:
        fx_calc_date = (transaction_date + timedelta(days=self.config.days_of_reckoning_by_stock) -
                        timedelta(days=self.config.fx_calculation_day))
        while not self.cal.is_working_day(fx_calc_date, extra_holidays=POLAND_EXTRA_HOLIDAYS): # looking for first workday for fx
            # calculation
            fx_calc_date = fx_calc_date - timedelta(days=1)
        return fx_calc_date