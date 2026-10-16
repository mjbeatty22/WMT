"""Screen candidate portfolios against the Meridian Foundation reserve mandate.

All editable inputs are grouped at the top of this file. Dollar amounts are in
USD millions; candidate weights are percentages of the portfolio.
"""

# --- Editable inputs -------------------------------------------------------

holdings = [
    {"holding": "Cash", "issuer": "none", "business_days_to_redeem": 0, "reserve_eligible": True},
    {"holding": "Treasury bills", "issuer": "U.S. Treasury", "business_days_to_redeem": 1, "reserve_eligible": True},
    {"holding": "Treasury 10-year note", "issuer": "U.S. Treasury", "business_days_to_redeem": 1, "reserve_eligible": True},
    {"holding": "Global equity index fund", "issuer": "diversified fund", "business_days_to_redeem": 2, "reserve_eligible": False},
    {"holding": "Investment-grade bond fund", "issuer": "diversified fund", "business_days_to_redeem": 3, "reserve_eligible": False},
    {"holding": "Private real estate fund", "issuer": "diversified fund", "business_days_to_redeem": 90, "reserve_eligible": False},
    {"holding": "Acme Corp bonds", "issuer": "Acme Corp", "business_days_to_redeem": 4, "reserve_eligible": False},
    {"holding": "Acme Corp stock", "issuer": "Acme Corp", "business_days_to_redeem": 1, "reserve_eligible": False},
]

candidates = {
    "A": {
        "Cash": 2, "Treasury bills": 2, "Treasury 10-year note": 10,
        "Global equity index fund": 60, "Investment-grade bond fund": 26,
        "Private real estate fund": 0, "Acme Corp bonds": 0, "Acme Corp stock": 0,
    },
    "B": {
        "Cash": 1, "Treasury bills": 0, "Treasury 10-year note": 0,
        "Global equity index fund": 55, "Investment-grade bond fund": 20,
        "Private real estate fund": 15, "Acme Corp bonds": 5, "Acme Corp stock": 4,
    },
    "C": {
        "Cash": 1, "Treasury bills": 1, "Treasury 10-year note": 0,
        "Global equity index fund": 70, "Investment-grade bond fund": 20,
        "Private real estate fund": 0, "Acme Corp bonds": 0, "Acme Corp stock": 8,
    },
    "D": {
        "Cash": 3, "Treasury bills": 87, "Treasury 10-year note": 0,
        "Global equity index fund": 10, "Investment-grade bond fund": 0,
        "Private real estate fund": 0, "Acme Corp bonds": 0, "Acme Corp stock": 0,
    },
}

reserve_size = 100.0
quarterly_distribution = 0.75
quarters_to_cover = 4
liquidity_window = 5
minimum_liquid_share = 90.0
issuer_limit = 8.0

# Cash, the U.S. Treasury, and diversified funds are exempt from the issuer limit.
exempt_issuers = {"none", "U.S. Treasury", "diversified fund"}


def label(result):
    return "pass" if result else "FAIL"


def main():
    holding_by_name = {item["holding"]: item for item in holdings}
    reserve_minimum = quarters_to_cover * quarterly_distribution / reserve_size * 100
    print(f"Reserve minimum: {reserve_minimum:.1f}% of the portfolio")

    for name, weights in candidates.items():
        weight_sum = sum(weights.get(item["holding"], 0.0) for item in holdings)
        lowest_weight = min(weights.get(item["holding"], 0.0) for item in holdings)
        reserve_weight = sum(
            weights.get(item["holding"], 0.0) for item in holdings if item["reserve_eligible"]
        )
        liquid_weight = sum(
            weights.get(item["holding"], 0.0)
            for item in holdings
            if item["business_days_to_redeem"] <= liquidity_window
        )

        company_weights = {}
        for holding_name, weight in weights.items():
            issuer = holding_by_name[holding_name]["issuer"]
            if issuer not in exempt_issuers:
                company_weights[issuer] = company_weights.get(issuer, 0.0) + weight
        largest_company = max(company_weights.values(), default=0.0)

        checks = [
            ("Weights sum to 100", weight_sum, abs(weight_sum - 100.0) < 1e-9),
            ("Long-only (lowest weight)", lowest_weight, lowest_weight >= 0.0),
            (f"Reserve >= {reserve_minimum:.1f}%", reserve_weight, reserve_weight >= reserve_minimum),
            (f"Redeemable in {liquidity_window} days >= {minimum_liquid_share:.1f}%", liquid_weight, liquid_weight >= minimum_liquid_share),
            (f"Largest single company <= {issuer_limit:.1f}%", largest_company, largest_company <= issuer_limit),
        ]

        print(f"\nCandidate {name}")
        failures = 0
        for rule, value, result in checks:
            print(f"{rule}: {value:.1f} {label(result)}")
            failures += not result
        print("Calendar-year loss: requires CIO clarification")
        if failures:
            print(f"Verdict: fails {failures} rule(s)")
        else:
            print("Verdict: passes every checkable rule")


if __name__ == "__main__":
    main()
