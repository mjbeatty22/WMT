"""Walmart (WMT) five-year pro-forma with one-at-a-time sensitivities.

All dollar figures are USD millions except per-share data. FY2026 is opening
history; FY2027-FY2031 are forecasts. Run: python WMT_three_statement_model.py

The sensitivity section uses a fresh copy of BASE_INPUTS for every run. It
changes only the named driver, retains signed FCFF, keeps checks visible, and
reruns the untouched base case at the end.
"""

from copy import deepcopy


# Reported opening balance sheet, Walmart FY2026 Form 10-K, USD millions.
OPENING = {
    "revenue": 713_163.0, "cash": 10_727.0, "receivables": 11_172.0,
    "inventory": 58_851.0, "ppe": 136_083.0, "other_assets": 67_835.0,
    "accounts_payable": 63_061.0, "debt": 44_762.0,
    "lease_liabilities": 22_333.0, "other_liabilities": 48_625.0,
    "equity": 105_887.0, "revolver": 0.0,
}

# Separate base input set. Each model run starts from a deep copy of this set.
BASE_INPUTS = {
    "revenue_growth": [0.045, 0.040, 0.035, 0.035, 0.030],  # judgment
    "gross_margin": 0.250,  # judgment
    "sga_as_percent_of_gross_profit": 0.830,  # judgment
    "inventory_days": 39.5,  # history-based
    "receivables_as_percent_of_revenue": 11_172 / 713_163,  # FY2026 history
    "payable_days": 63_061 / 535_395 * 365,  # FY2026 history
    "depreciation_as_percent_of_opening_ppe": 0.105,  # history-based
    "capex_as_percent_of_revenue": 0.038,  # judgment
    "tax_rate": 0.240,  # judgment
    "interest_rate": 0.050,  # judgment
    "annual_debt_repayment": 0.0,  # judgment
    "annual_dividends": 7_700.0,  # judgment
    "annual_share_buybacks": 8_000.0,  # judgment
    "minimum_cash": 5_000.0,  # judgment
    "revolver_limit": 25_000.0,  # judgment; not a confirmed facility amount
}

# The current model does not bridge forecast revolver debt to equity value and
# holds shares constant despite modeled buybacks. Do not report a value/share.
VALUATION_LIMITATION = (
    "Unavailable: the model does not bridge forecast revolver debt into net "
    "debt and does not update share count for modeled buybacks."
)
FLOOR_PLAN = "none"

# Ranges already specified in the prior analysis; no new ranges are selected.
SENSITIVITY_DRIVERS = [
    {
        "name": "Revenue growth",
        "unit": "% year-over-year revenue growth",
        "years": "FY2027-FY2031",
        "reason": "Judgment range of +/-1.0 percentage point around the base path.",
        "cases": {
            "Lower": {"revenue_growth": [0.035, 0.030, 0.025, 0.025, 0.020]},
            "Base": {"revenue_growth": [0.045, 0.040, 0.035, 0.035, 0.030]},
            "Higher": {"revenue_growth": [0.055, 0.050, 0.045, 0.045, 0.040]},
        },
    },
    {
        "name": "SG&A / gross profit",
        "unit": "% of gross profit",
        "years": "FY2027-FY2031",
        "reason": "Judgment range of +/-0.5 percentage point around the 83.0% base.",
        "cases": {
            "Lower": {"sga_as_percent_of_gross_profit": 0.825},
            "Base": {"sga_as_percent_of_gross_profit": 0.830},
            "Higher": {"sga_as_percent_of_gross_profit": 0.835},
        },
    },
]


def dollars(value):
    return f"${value:,.1f}"


def fresh_base_inputs():
    """Return an independent base input set; never modify BASE_INPUTS."""
    return deepcopy(BASE_INPUTS)


def opening_balance_sheet_check():
    assets = sum(OPENING[key] for key in ("cash", "receivables", "inventory", "ppe", "other_assets"))
    liabilities_and_equity = sum(
        OPENING[key] for key in (
            "accounts_payable", "debt", "lease_liabilities", "other_liabilities", "equity",
        )
    )
    return assets - liabilities_and_equity


def make_year(year, beginning, growth, inputs):
    revenue = beginning["revenue"] * (1 + growth)
    gross_profit = revenue * inputs["gross_margin"]
    cost_of_sales = revenue - gross_profit
    sga = gross_profit * inputs["sga_as_percent_of_gross_profit"]
    # D&A is embedded in reported SG&A. It is added back in the cash-flow bridge.
    ebit = gross_profit - sga
    depreciation = beginning["ppe"] * inputs["depreciation_as_percent_of_opening_ppe"]
    interest_expense = (beginning["debt"] + beginning["revolver"]) * inputs["interest_rate"]
    pretax_income = ebit - interest_expense
    taxes = max(0.0, pretax_income * inputs["tax_rate"])
    net_income = pretax_income - taxes

    receivables = revenue * inputs["receivables_as_percent_of_revenue"]
    inventory = cost_of_sales * inputs["inventory_days"] / 365
    accounts_payable = cost_of_sales * inputs["payable_days"] / 365
    change_in_nwc = (
        receivables - beginning["receivables"]
        + inventory - beginning["inventory"]
        - (accounts_payable - beginning["accounts_payable"])
    )
    cash_from_operations = net_income + depreciation - change_in_nwc
    capex = revenue * inputs["capex_as_percent_of_revenue"]
    debt_repayment = min(inputs["annual_debt_repayment"], beginning["debt"])
    cash_before_revolver = (
        beginning["cash"] + cash_from_operations - capex - debt_repayment
        - inputs["annual_dividends"] - inputs["annual_share_buybacks"]
    )
    revolver_change = max(-beginning["revolver"], inputs["minimum_cash"] - cash_before_revolver)
    revolver = beginning["revolver"] + revolver_change
    if revolver > inputs["revolver_limit"]:
        raise ValueError(
            f"FY{year} invalid: revolver ${revolver:,.1f} exceeds "
            f"the ${inputs['revolver_limit']:,.1f} modeled limit."
        )
    cash = cash_before_revolver + revolver_change
    ppe = beginning["ppe"] + capex - depreciation
    debt = beginning["debt"] - debt_repayment
    equity = beginning["equity"] + net_income - inputs["annual_dividends"] - inputs["annual_share_buybacks"]

    assets = cash + receivables + inventory + ppe + beginning["other_assets"]
    liabilities_and_equity = (
        accounts_payable + debt + revolver + beginning["lease_liabilities"]
        + beginning["other_liabilities"] + equity
    )
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
        "revolver_change": revolver_change, "dividends": inputs["annual_dividends"],
        "share_buybacks": inputs["annual_share_buybacks"],
        # FCFF = EBIT(1-tax) + D&A - capex - change in net working capital.
        "fcff": ebit * (1 - inputs["tax_rate"]) + depreciation - capex - change_in_nwc,
        "balance_sheet_check": assets - liabilities_and_equity,
    }


def run_full_model(inputs):
    """Run one complete linked model from an independent input copy."""
    run_inputs = deepcopy(inputs)
    beginning = deepcopy(OPENING)
    forecasts = []
    for year, growth in zip(range(2027, 2032), run_inputs["revenue_growth"]):
        forecast = make_year(year, beginning, growth, run_inputs)
        forecasts.append(forecast)
        beginning = forecast
    return forecasts


def safe_run(inputs):
    try:
        forecasts = run_full_model(inputs)
        max_check = max(abs(forecast["balance_sheet_check"]) for forecast in forecasts)
        return {"status": "VALID", "forecasts": forecasts, "max_check": max_check, "error": ""}
    except ValueError as error:
        return {"status": "INVALID", "forecasts": [], "max_check": None, "error": str(error)}


def final_outputs(run):
    if run["status"] != "VALID":
        return None
    final_year = run["forecasts"][-1]
    return {"ebit": final_year["ebit"], "fcff": final_year["fcff"]}


def format_path(value):
    if isinstance(value, list):
        return ", ".join(f"{item * 100:.1f}%" for item in value)
    return f"{value * 100:.1f}%"


def print_base_trace(base_run):
    """Retain linked statement lines needed to trace the base result."""
    print("\nBase Case Trace — FY2031 (USD millions)")
    final_year = base_run["forecasts"][-1]
    for label, key in [
        ("Revenue", "revenue"), ("Gross profit", "gross_profit"),
        ("SG&A", "sga"), ("EBIT", "ebit"),
        ("Cash from operations", "cash_from_operations"), ("Capital spending", "capex"),
        ("FCFF", "fcff"), ("Ending cash", "cash"), ("Ending revolver", "revolver"),
        ("Assets less liabilities & equity", "balance_sheet_check"),
    ]:
        print(f"{label.ljust(34)} {dollars(final_year[key])}")


def print_sensitivity(driver, initial_base_run):
    print(f"\n{driver['name']} — one independent input")
    print(f"Units: {driver['unit']} | Affected years: {driver['years']}")
    print(f"Range reason: {driver['reason']}")
    print("Case".ljust(9) + " Actual input values".ljust(42) + " Status".ljust(10)
          + " FY2031 EBIT".rjust(15) + " Change".rjust(14)
          + " FY2031 FCFF".rjust(15) + " Change".rjust(14) + " Max BS check".rjust(15))

    valid_outputs = []
    base_output = final_outputs(initial_base_run)
    for case, overrides in driver["cases"].items():
        inputs = fresh_base_inputs()  # reset every independent input to base
        inputs.update(deepcopy(overrides))  # change only this driver
        run = safe_run(inputs)
        actual_input = format_path(next(iter(overrides.values())))
        if run["status"] == "INVALID":
            print(f"{case.ljust(9)} {actual_input.ljust(42)} INVALID   {run['error']}")
            continue
        output = final_outputs(run)
        valid_outputs.append(output)
        print(
            f"{case.ljust(9)} {actual_input.ljust(42)} VALID"
            f" {dollars(output['ebit']).rjust(14)} {dollars(output['ebit'] - base_output['ebit']).rjust(13)}"
            f" {dollars(output['fcff']).rjust(14)} {dollars(output['fcff'] - base_output['fcff']).rjust(13)}"
            f" {dollars(run['max_check']).rjust(14)}"
        )

    if valid_outputs:
        ebit_span = max(item["ebit"] for item in valid_outputs) - min(item["ebit"] for item in valid_outputs)
        fcff_span = max(item["fcff"] for item in valid_outputs) - min(item["fcff"] for item in valid_outputs)
        print(f"Output span across valid results: EBIT {dollars(ebit_span)}; FCFF {dollars(fcff_span)}.")
    print(f"Value per share: {VALUATION_LIMITATION}")


def same_base_run(first_run, final_run):
    if first_run["status"] != final_run["status"]:
        return False
    if first_run["status"] != "VALID":
        return first_run["error"] == final_run["error"]
    return first_run["forecasts"] == final_run["forecasts"]


def main():
    opening_check = opening_balance_sheet_check()
    if abs(opening_check) > 0.01:
        raise ValueError(f"Opening balance sheet does not balance: {opening_check}")

    print("Walmart (WMT) five-year pro-forma — one-at-a-time sensitivity analysis")
    print("Opening year: FY2026 | Forecast years: FY2027-FY2031")
    print(f"Floor-plan assumption: {FLOOR_PLAN}")
    print(f"Opening balance-sheet check: {dollars(opening_check)}")

    initial_base_run = safe_run(fresh_base_inputs())
    if initial_base_run["status"] != "VALID":
        print(f"Initial base run is INVALID: {initial_base_run['error']}")
        return
    print_base_trace(initial_base_run)

    for driver in SENSITIVITY_DRIVERS:
        print_sensitivity(driver, initial_base_run)

    restored_base_run = safe_run(fresh_base_inputs())
    print("\nRestored Base Run")
    print("PASS: restored base matches the first base run." if same_base_run(initial_base_run, restored_base_run)
          else "FAIL: restored base does not match the first base run.")
    if restored_base_run["status"] == "VALID":
        print(f"Restored base maximum balance-sheet check: {dollars(restored_base_run['max_check'])}")


if __name__ == "__main__":
    main()
