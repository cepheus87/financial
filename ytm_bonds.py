import argparse

def calculate_ytm(face_value: float, price: float, coupon_rate: float, years_to_maturity: int, accrued_interest:
float, payments_per_year: int = 1):
    """
    Calculate the Yield to Maturity (YTM) of a bond.

    Parameters:
    - face_value: The bond's face value (par value).
    - price: The current market price of the bond as decimal value.
    - coupon_rate: The annual coupon rate (as a decimal, e.g., 0.05 for 5%).
    - years_to_maturity: The number of years until the bond matures.
    - accrued_interest: The accrued interest since the last coupon payment.
    - payments_per_year: The number of coupon payments per year (default is 1).
    

    Returns:
    - ytm: The Yield to Maturity (as a decimal).
    """

    price = price * face_value + accrued_interest

    # Total number of payments
    total_payments = int(years_to_maturity * payments_per_year)
    # Periodic coupon payment
    coupon_payment = (coupon_rate * face_value) / payments_per_year

    # Initial guess for YTM
    ytm_guess = coupon_rate

    # Newton-Raphson method
    for _ in range(100):  # Limit iterations to 100
        # Calculate the bond price using the current YTM guess
        price_guess = sum(
            coupon_payment / (1 + ytm_guess / payments_per_year) ** (t + 1)
            for t in range(total_payments)
        ) + face_value / (1 + ytm_guess / payments_per_year) ** total_payments

        # Calculate the derivative of the price with respect to YTM
        price_derivative = sum(
            -t * coupon_payment / payments_per_year / (1 + ytm_guess / payments_per_year) ** (t + 2)
            for t in range(total_payments)
        ) - total_payments * face_value / payments_per_year / (1 + ytm_guess / payments_per_year) ** (total_payments + 1)

        # Update the YTM guess
        ytm_guess -= (price_guess - price) / price_derivative

        # Check for convergence
        if abs(price_guess - price) < 1e-6:
            return ytm_guess * payments_per_year

    raise ValueError("YTM calculation did not converge")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate Yield to Maturity (YTM) of a bond.")
    parser.add_argument("-fv", "--face-value", type=float, help="Bond face value")
    parser.add_argument("-p", "--price", type=float, help="Current market price of the bond (as a decimal value)")
    parser.add_argument("-cr", "--coupon_rate", type=float, help="Annual coupon rate (as a decimal)")
    parser.add_argument("-ytm", "--years_to_maturity", type=int, help="Years to maturity")
    parser.add_argument("-ai", "--accrued_interest", type=float, default=0, help="Accrued interest since last coupon payment")
    parser.add_argument("-ppr", "--payments_per_year", type=int, default=1, help="Number of coupon payments per year")

    args = parser.parse_args()

    ytm = calculate_ytm(args.face_value, args.price, args.coupon_rate, args.years_to_maturity,
                        args.accrued_interest,  args.payments_per_year)
    print(f"Yield to Maturity (YTM): {ytm:.4%}")


# Example parameters:
# face_value = 1000  # Bond face value
# price = 0.95        # Current market price
# coupon_rate = 0.05 # Annual coupon rate (5%)
# years_to_maturity = 5  # Years to maturity

