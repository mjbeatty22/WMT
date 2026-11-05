"""Filing-only rule checks and memo text for the three-investor panel."""
from __future__ import annotations


PASS, FAIL, UNKNOWN = "pass", "fail", "not known"


def status(value: bool | str) -> str:
    if value == "not known":
        return UNKNOWN
    return PASS if value else FAIL


def all_years(rows: list[dict], test) -> str:
    outcomes = [test(row) for row in rows]
    if not outcomes or any(outcome is None for outcome in outcomes):
        return UNKNOWN
    return PASS if all(outcomes) else FAIL


def cathie_checks(panel: dict) -> dict[str, str]:
    derived = panel.get("derived", {})
    growth = derived.get("Revenue growth per year, first year to last", UNKNOWN)
    r_and_d = derived.get("R&D as a share of latest-year revenue", UNKNOWN)
    return {
        "Revenue growth per year at least 5%": UNKNOWN if growth == UNKNOWN else status(growth >= .05),
        "Latest-year R&D at least 5% of revenue": UNKNOWN if r_and_d == UNKNOWN else status(r_and_d >= .05),
    }


def burry_checks(panel: dict) -> dict[str, str]:
    cash_conversion = all_years(
        panel["rows"],
        lambda row: None if row["values"].get("operating_cash_flow") is None or row["values"].get("net_income") is None
        else row["values"]["operating_cash_flow"]["value"] >= row["values"]["net_income"]["value"],
    )
    latest = panel["rows"][-1] if panel["rows"] else None
    balance_sheet = UNKNOWN
    if latest:
        liabilities = latest["values"].get("liabilities")
        equity = latest["values"]["equity"]
        if liabilities is not None and equity is not None and equity["value"] > 0:
            balance_sheet = status(liabilities["value"] <= 2 * equity["value"])
    return {
        "Operating cash flow at least net income every year": cash_conversion,
        "Latest-year liabilities no more than twice equity": balance_sheet,
    }


def panel_checks(panel: dict) -> dict[str, dict[str, str]]:
    return {
        "Buffett": {label: status(result) for label, result in panel["checks"].items()},
        "Cathie Wood": cathie_checks(panel),
        "Michael Burry": burry_checks(panel),
    }


def verdict(checks: dict[str, str]) -> str:
    """A transparent screen result, not a valuation or expected-return conclusion."""
    if FAIL in checks.values():
        return "pass"
    if UNKNOWN in checks.values():
        return "watch it"
    return "own the business"


def printable(item: dict | None) -> str:
    return "not found" if item is None else f"{item['value']:,}"


def investor_memo(investor: str, panel: dict, checks: dict[str, str]) -> str:
    first, latest = panel["rows"][0], panel["rows"][-1]
    first_revenue = printable(first["values"]["revenue"])
    latest_revenue = printable(latest["values"]["revenue"])
    growth = panel.get("derived", {}).get("Revenue growth per year, first year to last", UNKNOWN)
    growth_text = "not known" if growth == UNKNOWN else f"{growth:.2%}"
    check_text = "; ".join(f"{label}: {result}" for label, result in checks.items())
    memo = (
        f"## {investor} memo\n\n"
        f"Revenue moved from {first_revenue} in the first displayed fiscal year to {latest_revenue} "
        f"in the latest displayed fiscal year. The printed annual revenue-growth calculation is {growth_text}.\n\n"
        f"Coded checks: {check_text}. This is a filing-only business-quality screen, not a price or return forecast.\n\n"
    )
    if investor == "Cathie Wood":
        memo += "Threshold retained: 5% annual revenue growth, to recognize sustained expansion without requiring a hypergrowth business.\n\n"
    return memo + f"## Conclusion: {verdict(checks)}\n"
