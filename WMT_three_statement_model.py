"""Walmart (WMT) five-year three-statement model and DCF.

All dollar figures are USD millions except per-share data.  FY2026 is the
opening year (year ended January 31, 2026); FY2027-FY2031 are forecasts.
Run: python WMT_three_statement_model.py

This is a classroom, screen-grade model.  Filing-derived history is separated
from analyst judgments below so that a user can replace assumptions without
mistaking them for reported facts.
"""

# ---------------------------------------------------------------------------
# Assumptions: values from history are tagged HISTORY; forecasts are JUDGMENT.
# ---------------------------------------------------------------------------
REVENUE_GROWTH = [0.045, 0.040, 0.035, 0.035, 0.030]  # JUDGMENT
GROSS_MARGIN = 0.250  # JUDGMENT; FY24-FY26 range was 24.4%-24.9%
SGA_AS_PERCENT_OF_GROSS_PROFIT = 0.830  # JUDGMENT; recent history ~83%
INVENTORY_DAYS = 39.5  # HISTORY-based assumption
RECEIVABLES_AS_PERCENT_OF_REVENUE = 11_172 / 713_163  # FY2026 HISTORY
PAYABLE_DAYS = 63_061 / 535_395 * 365  # FY2026 HISTORY
DEPRECIATION_AS_PERCENT_OF_OPENING_PPE = 0.105  # HISTORY-based assumption
CAPEX_AS_PERCENT_OF_REVENUE = 0.038  # JUDGMENT; FY2026 was 3.7%
TAX_RATE = 0.240  # JUDGMENT; normalized from FY2025-FY2026
INTEREST_RATE = 0.050  # JUDGMENT; applied to opening debt
ANNUAL_DEBT_REPAYMENT = 0.0  # JUDGMENT; no debt-maturity schedule modeled
ANNUAL_DIVIDENDS = 7_700.0  # JUDGMENT; close to FY2026 cash dividends
ANNUAL_SHARE_BUYBACKS = 8_000.0  # JUDGMENT; close to FY2026 repurchases
MINIMUM_CASH = 5_000.0  # JUDGMENT; liquidity floor for this simplified model
REVOLVER_LIMIT = 25_000.0  # JUDGMENT; not a confirmed Walmart facility amount
WACC = 0.070  # JUDGMENT; valuation input, not company guidance
TERMINAL_GROWTH = 0.025  # JUDGMENT; long-run nominal growth assumption
SHARES_OUTSTANDING = 7_969.0  # FY2026 ending shares, HISTORY (millions)

# Walmart has no disclosed companywide annual square-footage/floor-plan plan
# suitable for forecasting.  Therefore this model uses no floor-plan line.
FLOOR_PLAN = "none"

# ---------------------------------------------------------------------------
# FY2026 opening balance sheet: Walmart FY2026 Form 10-K, USD millions.
# Aggregated lines preserve the reported balance sheet while keeping the model
# simple enough to audit in a first three-statement build.
# ---------------------------------------------------------------------------
OPENING_REVENUE = 713_163.0
OPENING_CASH = 10_727.0
OPENING_RECEIVABLES = 11_172.0
OPENING_INVENTORY = 58_851.0
OPENING_PPE = 136_083.0
OPENING_OTHER_ASSETS = 67_835.0
OPENING_ACCOUNTS_PAYABLE = 63_061.0
OPENING_DEBT = 44_762.0  # short-term borrowings + current and long-term debt
OPENING_LEASE_LIABILITIES = 22_333.0  # operating + finance lease obligations
OPENING_OTHER_LIABILITIES = 48_625.0  # includes accrued and deferred items
OPENING_EQUITY = 105_887.0  # total shareholders' equity
OPENING_REVOLVER = 0.0


def dollars(value):
    return f"${value:,.1f}"


def check_opening_balance_sheet():
    assets = (
        OPENING_CASH + OPENING_RECEIVABLES + OPENING_INVENTORY + OPENING_PPE
        + OPENING_OTHER_ASSETS
    )
    liabilities_and_equity = (
        OPENING_ACCOUNTS_PAYABLE + OPENING_DEBT + OPENING_LEASE_LIABILITIES
        + OPENING_OTHER_LIABILITIES + OPENING_EQUITY
    )
    return assets - liabilities_and_equity


def make_year(year, beginning, growth):
    revenue = beginning["revenue"] * (1 + growth)
    gross_profit = revenue * GROSS_MARGIN
    cost_of_sales = revenue - gross_profit
    sga = gross_profit * SGA_AS_PERCENT_OF_GROSS_PROFIT
    # D&A is already embedded in Walmart's reported SG&A; do not subtract it twice.
    ebit = gross_profit - sga
    depreciation = beginning["ppe"] * DEPRECIATION_AS_PERCENT_OF_OPENING_PPE
    interest_expense = (beginning["debt"] + beginning["revolver"]) * INTEREST_RATE
    pretax_income = ebit - interest_expense
    taxes = max(0.0, pretax_income * TAX_RATE)
    net_income = pretax_income - taxes

    receivables = revenue * RECEIVABLES_AS_PERCENT_OF_REVENUE
    inventory = cost_of_sales * INVENTORY_DAYS / 365
    accounts_payable = cost_of_sales * PAYABLE_DAYS / 365
    change_in_nwc = (
        (receivables - beginning["receivables"])
        + (inventory - beginning["inventory"])
        - (accounts_payable - beginning["accounts_payable"])
    )
    cash_from_operations = net_income + depreciation - change_in_nwc
    capex = revenue * CAPEX_AS_PERCENT_OF_REVENUE
    debt_repayment = min(ANNUAL_DEBT_REPAYMENT, beginning["debt"])
    cash_before_revolver = (
        beginning["cash"] + cash_from_operations - capex - debt_repayment
        - ANNUAL_DIVIDENDS - ANNUAL_SHARE_BUYBACKS
    )
    revolver_change = max(-beginning["revolver"], MINIMUM_CASH - cash_before_revolver)
    revolver = beginning["revolver"] + revolver_change
    if revolver > REVOLVER_LIMIT:
        raise ValueError(f"FY{year}: revolver limit exceeded.")
    cash = cash_before_revolver + revolver_change
    ppe = beginning["ppe"] + capex - depreciation
    debt = beginning["debt"] - debt_repayment
    equity = beginning["equity"] + net_income - ANNUAL_DIVIDENDS - ANNUAL_SHARE_BUYBACKS

    assets = cash + receivables + inventory + ppe + beginning["other_assets"]
    liabilities_and_equity = (
        accounts_payable + debt + revolver + beginning["lease_liabilities"]
        + beginning["other_liabilities"] + equity
    )
    balance_sheet_check = assets - liabilities_and_equity
    fcff = ebit * (1 - TAX_RATE) + depreciation - capex - change_in_nwc

    return {
        "year": year, "revenue": revenue, "gross_profit": gross_profit,
        "cost_of_sales": cost_of_sales, "sga": sga, "depreciation": depreciation,
        "ebit": ebit, "interest_expense": interest_expense,
        "pretax_income": pretax_income, "taxes": taxes, "net_income": net_income,
        "cash": cash, "receivables": receivables, "inventory": inventory,
        "ppe": ppe, "other_assets": beginning["other_assets"],
        "accounts_payable": accounts_payable, "debt": debt, "revolver": revolver,
        "lease_liabilities": beginning["lease_liabilities"],
        "other_liabilities": beginning["other_liabilities"], "equity": equity,
        "cash_from_operations": cash_from_operations, "capex": capex,
        "change_in_nwc": change_in_nwc, "debt_repayment": debt_repayment,
        "revolver_change": revolver_change,
        "dividends": ANNUAL_DIVIDENDS, "share_buybacks": ANNUAL_SHARE_BUYBACKS,
        "fcff": fcff, "balance_sheet_check": balance_sheet_check,
    }


def print_schedule(title, rows, years):
    print(f"\n{title}")
    print("Line item".ljust(30), end="")
    for forecast in years:
        print(f"FY{forecast['year']}".rjust(14), end="")
    print()
    for label, key in rows:
        print(label.ljust(30), end="")
        for forecast in years:
            print(dollars(forecast[key]).rjust(14), end="")
        print()


def dcf_value(forecasts):
    present_value_fcff = sum(
        forecast["fcff"] / (1 + WACC) ** index
        for index, forecast in enumerate(forecasts, start=1)
    )
    terminal_value = forecasts[-1]["fcff"] * (1 + TERMINAL_GROWTH) / (WACC - TERMINAL_GROWTH)
    present_value_terminal = terminal_value / (1 + WACC) ** len(forecasts)
    enterprise_value = present_value_fcff + present_value_terminal
    # Finance leases are treated as debt; operating leases remain in operations.
    net_debt = OPENING_DEBT + 6_761.0 - OPENING_CASH
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / SHARES_OUTSTANDING
    return enterprise_value, equity_value, value_per_share


def main():
    opening_check = check_opening_balance_sheet()
    if abs(opening_check) > 0.01:
        raise ValueError(f"Opening balance sheet does not balance: {opening_check}")

    beginning = {
        "revenue": OPENING_REVENUE, "cash": OPENING_CASH,
        "receivables": OPENING_RECEIVABLES, "inventory": OPENING_INVENTORY,
        "ppe": OPENING_PPE, "other_assets": OPENING_OTHER_ASSETS,
        "accounts_payable": OPENING_ACCOUNTS_PAYABLE, "debt": OPENING_DEBT,
        "revolver": OPENING_REVOLVER,
        "lease_liabilities": OPENING_LEASE_LIABILITIES,
        "other_liabilities": OPENING_OTHER_LIABILITIES, "equity": OPENING_EQUITY,
    }
    forecasts = []
    for year, growth in zip(range(2027, 2032), REVENUE_GROWTH):
        forecast = make_year(year, beginning, growth)
        if abs(forecast["balance_sheet_check"]) > 0.01:
            raise ValueError(f"FY{year} does not balance: {forecast['balance_sheet_check']}")
        forecasts.append(forecast)
        beginning = forecast

    print("Walmart (WMT) five-year three-statement model — screen-grade classroom model")
    print("Opening year: FY2026 | Forecast years: FY2027-FY2031")
    print(f"Floor-plan assumption: {FLOOR_PLAN}")
    print_schedule("Income Statement", [
        ("Revenue", "revenue"), ("Gross profit", "gross_profit"),
        ("SG&A (includes D&A)", "sga"), ("D&A add-back", "depreciation"),
        ("EBIT", "ebit"), ("Interest expense", "interest_expense"),
        ("Pre-tax income", "pretax_income"), ("Taxes", "taxes"),
        ("Net income", "net_income"),
    ], forecasts)
    print_schedule("Balance Sheet", [
        ("Cash", "cash"), ("Receivables", "receivables"),
        ("Inventory", "inventory"), ("PP&E, net", "ppe"),
        ("Other assets", "other_assets"), ("Accounts payable", "accounts_payable"),
        ("Debt", "debt"), ("Lease liabilities", "lease_liabilities"),
        ("Revolver", "revolver"),
        ("Other liabilities", "other_liabilities"), ("Equity", "equity"),
    ], forecasts)
    print_schedule("Cash Flow Statement", [
        ("Net income", "net_income"), ("Cash from operations", "cash_from_operations"),
        ("Capital spending", "capex"), ("Debt repayment", "debt_repayment"),
        ("Revolver change", "revolver_change"),
        ("Dividends", "dividends"), ("Share buybacks", "share_buybacks"),
        ("Free cash flow to firm", "fcff"),
    ], forecasts)
    print_schedule("Model Checks", [
        ("Assets less liabilities & equity", "balance_sheet_check"),
    ], forecasts)
    revolver_draw_years = [str(forecast["year"]) for forecast in forecasts if forecast["revolver_change"] > 0.01]
    if revolver_draw_years:
        print(
            "\nRevolver draw (FY" + ", FY".join(revolver_draw_years)
            + "): operating cash after capex, dividends, and share buybacks "
            + f"would otherwise fall below the ${MINIMUM_CASH:,.0f} minimum-cash floor."
        )
    enterprise_value, equity_value, value_per_share = dcf_value(forecasts)
    print("\nDCF Valuation")
    print(f"Enterprise value: {dollars(enterprise_value)}")
    print(f"Equity value:     {dollars(equity_value)}")
    print(f"Value per share:  ${value_per_share:,.2f}")
    print("\nA zero model-check line means the forecast balance sheets tie.")


if __name__ == "__main__":
    main()
