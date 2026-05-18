from dataclasses import dataclass
from datetime import date, timedelta
from workalendar.europe import Poland, Germany, UnitedKingdom

POLAND_EXTRA_HOLIDAYS = [
    date(2020, 12, 24),
]

class PolandCalFix(Poland):
    def is_working_day(self, day,
                           extra_working_days=None, extra_holidays=None):
        if day.month == 12 and day.day == 24: # 24.12 is not a working day
            return False
        return super().is_working_day(day, extra_working_days, extra_holidays)

class GermanyCalFix(Germany):
    def is_working_day(self, day,
                           extra_working_days=None, extra_holidays=None):
        if day.month == 10 and day.day == 3: # 03.10 Xetra is working however it is holiday
            return True
        return super().is_working_day(day, extra_working_days, extra_holidays)

@dataclass
class ReckoningRulesConfig:
    days_of_reckoning_by_stock: int = 2 # number of days after transaction in which stock proceeded transaction (
    # settlement date)
    fx_calculation_day: int = 1  # number of days before settlement day to take average fx value


class ReckoningRules:
    def __init__(self, config: ReckoningRulesConfig = ReckoningRulesConfig()):
        self.config = config
        self.pol_cal = PolandCalFix() # GPW
        self.uk_cal = UnitedKingdom() # LSE
        self.ge_cal = GermanyCalFix() # XETRA

    def get_day_of_fx_calculation(self, transaction_date: date, trade_currency: str) -> date:
        if trade_currency == "USD" or trade_currency == "GBP": #assumption that USD only bought on LSE
            cal = self.uk_cal
        elif trade_currency == "EUR":
            cal = self.ge_cal
        elif trade_currency == "PLN":
            cal = self.pol_cal
        else:
            raise ValueError(f"Unsupported trade currency: {trade_currency}")

        settlement_date = transaction_date + timedelta(days=self.config.days_of_reckoning_by_stock)
        while not cal.is_working_day(settlement_date): # looking for first workday after settlement day
            settlement_date = settlement_date + timedelta(days=1)

        fx_calc_date = (settlement_date - timedelta(days=self.config.fx_calculation_day))
        while not self.pol_cal.is_working_day(fx_calc_date, extra_holidays=POLAND_EXTRA_HOLIDAYS):
            # looking for first workday before settlement day for fx calculation
            fx_calc_date = fx_calc_date - timedelta(days=1)
        return fx_calc_date