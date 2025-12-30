from typing import Tuple, List

def calculate_compound_interest(principal: float, rate: float, time: float, n: int) -> Tuple[float, float]:
    """
    Calculate compound interest.

    Parameters:
    - principal: The initial amount of money (P).
    - rate: The annual interest rate (as a decimal, e.g., 0.05 for 5%).
    - time: The time the money is invested for (in years).
    - n: The number of times interest is compounded per year.

    Returns:
    - The total amount after interest.
    - The compound interest earned.
    """
    # Total amount after interest
    total_amount = principal * (1 + rate / n) ** (n * time)
    # Compound interest earned
    compound_interest = total_amount - principal
    return total_amount, compound_interest

def calculate_compound_interest_yearly(principal: float, rate: float, time: float, n: int) -> Tuple[List, List]:
    """
    Calculate compound interest.

    Parameters:
    - principal: The initial amount of money (P).
    - rate: The annual interest rate (as a decimal, e.g., 0.05 for 5%).
    - time: The time the money is invested for (in years).
    - n: The number of times interest is compounded per year.

    Returns:
    - The total amount after interest per year
    - The compound interest earned per year
    """

    if time < 1:
        raise ValueError("Time must be at least 1 year for yearly calculations.")

    total_amounts = []
    compound_interests = []

    for year in range(1, int(time) + 1):
        total_amount, compound_interest = calculate_compound_interest(principal, rate, year, n)
        total_amounts.append(total_amount)
        compound_interests.append(compound_interest)

    return total_amounts, compound_interests