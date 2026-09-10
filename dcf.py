"""Five-year discounted cash flow valuation using only the standard library.

Run with: python dcf.py
The terminal value is measured at the end of Year 5, when Year 6 FCFF is
used to calculate it, so it is discounted back five periods, not six.
"""

# Editable inputs (USD millions unless stated otherwise).
# TRAINING CASE: Walmart WACC and terminal-growth assumptions are unresolved.
STARTING_FCFF = 100.0
GROWTH_RATES = [0.08, 0.06, 0.05, 0.04, 0.03]
WACC = 0.10
TERMINAL_GROWTH = 0.03
NON_OPERATING_CASH = 50.0
DEBT = 300.0
DILUTED_SHARES = 50.0

# Sensitivity inputs.
SENSITIVITY_WACCS = [0.09, 0.10, 0.11]
SENSITIVITY_TERMINAL_GROWTHS = [0.02, 0.03, 0.04]

# Reverse-DCF inputs.
TARGET_SHARE_PRICE = 30.00
LOWER_GROWTH_SHIFT = -0.05
UPPER_GROWTH_SHIFT = 0.10


def calculate_values(wacc, terminal_growth, growth_rates):
    """Return DCF values using the supplied discount and growth assumptions."""
    fcff = []
    current_fcff = STARTING_FCFF

    for growth in growth_rates:
        current_fcff *= 1 + growth
        fcff.append(current_fcff)

    present_value_fcff = sum(
        amount / (1 + wacc) ** year
        for year, amount in enumerate(fcff, start=1)
    )
    terminal_value = fcff[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    present_value_terminal = terminal_value / (1 + wacc) ** len(fcff)
    enterprise_value = present_value_fcff + present_value_terminal
    equity_value = enterprise_value + NON_OPERATING_CASH - DEBT
    value_per_share = equity_value / DILUTED_SHARES
    terminal_value_share = present_value_terminal / enterprise_value

    return {
        "fcff": fcff,
        "present_value_fcff": present_value_fcff,
        "terminal_value": terminal_value,
        "present_value_terminal": present_value_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
        "terminal_value_share": terminal_value_share,
    }


def print_sensitivity_grid():
    print("\nSensitivity: Value per Diluted Share")
    header = "WACC \\ Terminal Growth"
    for growth in SENSITIVITY_TERMINAL_GROWTHS:
        header += f" | {growth:.1%}"
    print(header)
    print("-" * len(header))

    for wacc in SENSITIVITY_WACCS:
        row = f"{wacc:.1%}"

        for terminal_growth in SENSITIVITY_TERMINAL_GROWTHS:
            if terminal_growth >= wacc:
                row += " | invalid"
            else:
                value = calculate_values(
                    wacc,
                    terminal_growth,
                    GROWTH_RATES,
                )["value_per_share"]
                row += f" | {value:.2f}"

        print(row)


def reverse_dcf_value(shift):
    shifted_growth_rates = [growth + shift for growth in GROWTH_RATES]

    if any(growth <= -1.0 for growth in shifted_growth_rates):
        return None

    return calculate_values(
        WACC,
        TERMINAL_GROWTH,
        shifted_growth_rates,
    )["value_per_share"]


def print_reverse_dcf():
    print("\nReverse DCF")

    shifted_lower_rates = [growth + LOWER_GROWTH_SHIFT for growth in GROWTH_RATES]
    shifted_upper_rates = [growth + UPPER_GROWTH_SHIFT for growth in GROWTH_RATES]

    if any(growth <= -1.0 for growth in shifted_lower_rates):
        print("No solution: lower bound pushes an annual growth rate to -100% or below.")
        return

    if any(growth <= -1.0 for growth in shifted_upper_rates):
        print("No solution: upper bound pushes an annual growth rate to -100% or below.")
        return

    lower_value = reverse_dcf_value(LOWER_GROWTH_SHIFT)
    upper_value = reverse_dcf_value(UPPER_GROWTH_SHIFT)
    target_is_bracketed = (
        lower_value <= TARGET_SHARE_PRICE <= upper_value
        or upper_value <= TARGET_SHARE_PRICE <= lower_value
    )

    if not target_is_bracketed:
        print("No solution in this bracket.")
        print(f"Target price: {TARGET_SHARE_PRICE:.4f}")
        print(f"Bracket values: {lower_value:.4f} to {upper_value:.4f}")
        return

    lower_shift = LOWER_GROWTH_SHIFT
    upper_shift = UPPER_GROWTH_SHIFT

    for _ in range(100):
        middle_shift = (lower_shift + upper_shift) / 2
        middle_value = reverse_dcf_value(middle_shift)

        if abs(middle_value - TARGET_SHARE_PRICE) < 0.0001:
            break

        if (
            lower_value <= TARGET_SHARE_PRICE <= middle_value
            or middle_value <= TARGET_SHARE_PRICE <= lower_value
        ):
            upper_shift = middle_shift
            upper_value = middle_value
        else:
            lower_shift = middle_shift
            lower_value = middle_value

    print(f"Solved uniform growth shift: {middle_shift:+.4%}")
    print(f"Target price: {TARGET_SHARE_PRICE:.4f}")
    print(f"DCF value per share: {middle_value:.4f}")
    print(f"Held fixed WACC: {WACC:.4%}")
    print(f"Held fixed terminal growth: {TERMINAL_GROWTH:.4%}")
    print(f"Held fixed starting FCFF: {STARTING_FCFF:.4f}")
    print(f"Held fixed cash: {NON_OPERATING_CASH:.4f}")
    print(f"Held fixed debt: {DEBT:.4f}")
    print(f"Held fixed diluted shares: {DILUTED_SHARES:.4f}")
    print(f"Base growth rates: {GROWTH_RATES}")


def main():
    if TERMINAL_GROWTH >= WACC:
        print("Error: terminal growth must be less than WACC.")
        return

    values = calculate_values(WACC, TERMINAL_GROWTH, GROWTH_RATES)

    for year, amount in enumerate(values["fcff"], start=1):
        print(f"FCFF Year {year}: {amount:.4f}")
    print(f"Present value of explicit FCFF: {values['present_value_fcff']:.4f}")
    print(f"Terminal value at Year 5: {values['terminal_value']:.4f}")
    print(f"Present value of terminal value: {values['present_value_terminal']:.4f}")
    print(f"Enterprise value: {values['enterprise_value']:.4f}")
    print(f"Equity value: {values['equity_value']:.4f}")
    print(f"Value per diluted share: {values['value_per_share']:.4f}")
    print(f"PV of terminal value as share of enterprise value: {values['terminal_value_share']:.4f}")

    print_sensitivity_grid()
    print_reverse_dcf()
    print("\nEducational use only: this is not financial advice.")
    print("This model is a classroom exercise for learning DCF and reverse-DCF valuation.")


if __name__ == "__main__":
    main()
