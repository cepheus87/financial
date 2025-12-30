import numpy as np
from typing import Tuple, List


from utils import calculate_compound_interest_yearly, calculate_compound_interest



def anti_inflation_bond(principal: float, first_year_rate: float, coupon: float, assumed_inflation : float, time: float,
    n: int = 1, penalty: float = 0 ) -> Tuple[List, List]:
    """
    Calculate compound interest.

    Parameters:
    - principal: The initial amount of money (P).
    - first_year_rate: The interest rate (as a decimal e.g., 0.05 for 5%) for the first year.
    - coupon: The coupon rate (as a decimal e.g., 0.05 for 5%) for following years.
    - time: The time the money is invested for (in years).
    - assumed_inflation: The assumed inflation rate (as a decimal e.g., 0.05 for 5%) for following years.
    - n: The number of times interest is compounded per year.
    - penalty: The penalty for early withdrawal.

    Returns:
    - The total amount after interest per year
    - The compound interest earned per year
    """

    total_amounts, compound_interests = [], []

    # first year
    total_amount, compound_interest = calculate_compound_interest(principal, first_year_rate, 1, n)

    total_amounts.append(total_amount)
    compound_interests.append(compound_interest)

    if time > 1:
        #following years
        following_total_amounts, following_compound_interests = calculate_compound_interest_yearly(total_amount,
                                                                                      coupon + assumed_inflation,
                                                                                                   time - 1, n)

        following_compound_interests = np.array(following_compound_interests) + compound_interest

        total_amounts.extend(following_total_amounts)
        compound_interests.extend(following_compound_interests.tolist())

    if penalty:
        total_amounts[-1] -= penalty
        compound_interests[-1] -= penalty

    return total_amounts, compound_interests