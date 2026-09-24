"""ABG five-year pro forma and FCFE valuation.  Dollar amounts are USD millions."""

YEARS = [2026, 2027, 2028, 2029, 2030]

# Editable assumptions
ORGANIC_REVENUE_GROWTH = 0.018
GROSS_MARGIN = 0.1705
SGA_AS_PERCENT_OF_GROSS_PROFIT = [0.665, 0.655, 0.645, 0.645, 0.645]
DEPRECIATION_AS_PERCENT_OF_OPENING_PPE = 82.4 / 3_070.4
IMPAIRMENT = 120.0
CAPEX = 250.0
TAX_RATE = 0.255
INVENTORY_DAYS = 2_135.8 / (17_999.0 - 3_071.7) * 365
FLOOR_PLAN_AS_PERCENT_OF_INVENTORY = 2_027.0 / 2_135.8
OTHER_WORKING_CAPITAL_AS_PERCENT_OF_REVENUE_CHANGE = 0.008
MINIMUM_CASH = 25.0
REVOLVER_LIMIT = 850.0
REVOLVER_RATE = 0.06
TERM_DEBT_REPAYMENT = 150.0
SHARE_BUYBACK = 150.0
FLOOR_PLAN_RATE = 0.0467
TERM_DEBT_RATE = 0.0544
COST_OF_EQUITY = 0.10
TERMINAL_GROWTH = 0.025
SHARES_OUTSTANDING = 17.951349  # millions

# Opening balance sheet: FY2025, USD millions
OPENING = {
    "revenue": 17_999.0,
    "inventory": 2_135.8,
    "ppe": 3_070.4,
    "other_assets": 6_371.6,
    "cash": 40.4,
    "floor_plan": 2_027.0,
    "term_debt": 3_572.0,
    "revolver": 0.0,
    "other_liabilities": 2_127.5,
    "equity": 3_891.7,
}


def assert_balanced(year, gap, cash):
    """Raise a clear error if a forecast year does not balance or lacks liquidity."""
    if abs(gap) > 0.05:
        raise ValueError(f"{year} balance sheet does not balance: gap {gap:.1f} million")
    if cash < MINIMUM_CASH - 0.05:
        raise ValueError(f"{year} cash is below the minimum: {cash:.1f} million")


def print_table(title, rows):
    print(f"\n{title} (USD millions)")
    print(f"{'':34}" + "".join(f"{year:>12}" for year in YEARS))
    for label, values in rows:
        print(f"{label:<34}" + "".join(f"{value:>12,.1f}" for value in values))


def main():
    forecast = []
    opening = OPENING.copy()

    for index, year in enumerate(YEARS):
        revenue = opening["revenue"] * (1 + ORGANIC_REVENUE_GROWTH)
        gross_profit = revenue * GROSS_MARGIN
        sga = gross_profit * SGA_AS_PERCENT_OF_GROSS_PROFIT[index]
        depreciation = opening["ppe"] * DEPRECIATION_AS_PERCENT_OF_OPENING_PPE
        impairment = IMPAIRMENT
        operating_income = gross_profit - sga - depreciation - impairment
        interest = (
            opening["floor_plan"] * FLOOR_PLAN_RATE
            + opening["term_debt"] * TERM_DEBT_RATE
            + opening["revolver"] * REVOLVER_RATE
        )
        pretax_income = operating_income - interest
        tax = max(0.0, pretax_income) * TAX_RATE
        net_income = pretax_income - tax

        inventory = (revenue - gross_profit) * INVENTORY_DAYS / 365
        floor_plan = inventory * FLOOR_PLAN_AS_PERCENT_OF_INVENTORY
        ppe = opening["ppe"] + CAPEX - depreciation
        revenue_change = revenue - opening["revenue"]
        other_working_capital_change = (
            OTHER_WORKING_CAPITAL_AS_PERCENT_OF_REVENUE_CHANGE * revenue_change
        )
        other_assets = opening["other_assets"] + other_working_capital_change - impairment
        term_debt = opening["term_debt"] - TERM_DEBT_REPAYMENT
        other_liabilities = opening["other_liabilities"]
        equity = opening["equity"] + net_income - SHARE_BUYBACK

        inventory_change = inventory - opening["inventory"]
        floor_plan_change = floor_plan - opening["floor_plan"]
        fcfe_before_buyback = (
            net_income
            + depreciation
            + impairment
            - CAPEX
            - inventory_change
            - other_working_capital_change
            + floor_plan_change
            - TERM_DEBT_REPAYMENT
        )
        cash_before_revolver = opening["cash"] + fcfe_before_buyback - SHARE_BUYBACK

        # Draw only enough to protect the cash floor.  When cash exceeds the
        # floor, repay existing revolver debt first, limited by the balance.
        revolver = opening["revolver"]
        if cash_before_revolver < MINIMUM_CASH:
            draw = min(MINIMUM_CASH - cash_before_revolver, REVOLVER_LIMIT - revolver)
            revolver += draw
            cash = cash_before_revolver + draw
        else:
            repayment = min(cash_before_revolver - MINIMUM_CASH, revolver)
            revolver -= repayment
            cash = cash_before_revolver - repayment

        assets = inventory + ppe + other_assets + cash
        liabilities_and_equity = floor_plan + term_debt + revolver + other_liabilities + equity
        balance_sheet_gap = assets - liabilities_and_equity
        assert_balanced(year, balance_sheet_gap, cash)

        result = {
            "year": year,
            "revenue": revenue,
            "gross_profit": gross_profit,
            "sga": sga,
            "depreciation": depreciation,
            "impairment": impairment,
            "operating_income": operating_income,
            "interest": interest,
            "pretax_income": pretax_income,
            "tax": tax,
            "net_income": net_income,
            "inventory": inventory,
            "ppe": ppe,
            "other_assets": other_assets,
            "cash": cash,
            "floor_plan": floor_plan,
            "term_debt": term_debt,
            "revolver": revolver,
            "other_liabilities": other_liabilities,
            "equity": equity,
            "fcfe_before_buyback": fcfe_before_buyback,
            "inventory_change": inventory_change,
            "other_working_capital_change": other_working_capital_change,
            "floor_plan_change": floor_plan_change,
            "balance_sheet_gap": balance_sheet_gap,
            "cash_floor_check": cash - MINIMUM_CASH,
        }
        forecast.append(result)
        opening = {
            "revenue": revenue, "inventory": inventory, "ppe": ppe,
            "other_assets": other_assets, "cash": cash, "floor_plan": floor_plan,
            "term_debt": term_debt, "revolver": revolver,
            "other_liabilities": other_liabilities, "equity": equity,
        }

    print_table("Income statement", [
        ("Revenue", [x["revenue"] for x in forecast]),
        ("Gross profit", [x["gross_profit"] for x in forecast]),
        ("SG&A", [x["sga"] for x in forecast]),
        ("Depreciation", [x["depreciation"] for x in forecast]),
        ("Impairment", [x["impairment"] for x in forecast]),
        ("Operating income", [x["operating_income"] for x in forecast]),
        ("Interest", [x["interest"] for x in forecast]),
        ("Pretax income", [x["pretax_income"] for x in forecast]),
        ("Tax", [x["tax"] for x in forecast]),
        ("Net income", [x["net_income"] for x in forecast]),
    ])
    print_table("Balance sheet", [
        ("Inventory", [x["inventory"] for x in forecast]),
        ("PP&E", [x["ppe"] for x in forecast]),
        ("Other assets", [x["other_assets"] for x in forecast]),
        ("Cash", [x["cash"] for x in forecast]),
        ("Total assets", [x["inventory"] + x["ppe"] + x["other_assets"] + x["cash"] for x in forecast]),
        ("Floor-plan loans", [x["floor_plan"] for x in forecast]),
        ("Term debt", [x["term_debt"] for x in forecast]),
        ("Revolver", [x["revolver"] for x in forecast]),
        ("Other liabilities", [x["other_liabilities"] for x in forecast]),
        ("Equity", [x["equity"] for x in forecast]),
    ])
    print_table("Cash flow", [
        ("Net income", [x["net_income"] for x in forecast]),
        ("Depreciation", [x["depreciation"] for x in forecast]),
        ("Impairment", [x["impairment"] for x in forecast]),
        ("Capital spending", [-CAPEX for x in forecast]),
        ("Change in inventory", [-x["inventory_change"] for x in forecast]),
        ("Change in other working capital", [-x["other_working_capital_change"] for x in forecast]),
        ("Change in floor-plan loans", [x["floor_plan_change"] for x in forecast]),
        ("Term-debt repayment", [-TERM_DEBT_REPAYMENT for x in forecast]),
        ("FCFE before buyback", [x["fcfe_before_buyback"] for x in forecast]),
        ("Share buyback", [-SHARE_BUYBACK for x in forecast]),
    ])
    print_table("Checks", [
        ("Assets - liabilities - equity", [x["balance_sheet_gap"] for x in forecast]),
        ("Cash above minimum", [x["cash_floor_check"] for x in forecast]),
    ])

    present_values = [
        item["fcfe_before_buyback"] / (1 + COST_OF_EQUITY) ** (index + 1)
        for index, item in enumerate(forecast)
    ]
    terminal_fcfe = forecast[-1]["fcfe_before_buyback"] + TERM_DEBT_REPAYMENT
    terminal_value_2030 = terminal_fcfe * (1 + TERMINAL_GROWTH) / (COST_OF_EQUITY - TERMINAL_GROWTH)
    present_value_terminal = terminal_value_2030 / (1 + COST_OF_EQUITY) ** len(YEARS)
    equity_value = sum(present_values) + present_value_terminal
    after_2030_share = present_value_terminal / equity_value
    value_per_share = equity_value / SHARES_OUTSTANDING

    print("\nEquity valuation (USD millions, except per-share value)")
    print(f"Equity value:                 ${equity_value:,.1f}")
    print(f"Share of value after 2030:   {after_2030_share:.1%}")
    print(f"Value per share:              ${value_per_share:,.2f}")


if __name__ == "__main__":
    main()
