from dataclasses import dataclass


@dataclass
class ReckoningRules:
    fx_calculation_day: int = 1  # number of days before transaction for average fx value

