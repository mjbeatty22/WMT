"""Interactive Meridian portfolio comparison app.

Run locally with: python -m streamlit run portfolio_app.py
"""

import streamlit as st

from portfolio import (
    CORRELATIONS,
    OBJECTIVE_RETURN,
    RESERVE_ELIGIBLE,
    SLEEVES,
    benchmark_weights,
    build_covariance_matrix,
    equal_weight_weights,
    inverse_volatility_weights,
    meets_objective,
    portfolio_expected_return,
    portfolio_volatility,
    reserve_eligible_weight,
    validate_correlation_table,
)


MINIMUM_RESERVE_WEIGHT = 0.03
SLEEVE_ORDER = list(SLEEVES)


def copy_inputs():
    """Return editable copies of the base sleeve and correlation inputs."""
    sleeves = {name: values.copy() for name, values in SLEEVES.items()}
    correlations = {name: values.copy() for name, values in CORRELATIONS.items()}
    return sleeves, correlations


def portfolio_rows(sleeves, correlations, objective_return):
    """Calculate rows for the three baseline portfolio rules."""
    validate_correlation_table(sleeves, correlations)
    covariance = build_covariance_matrix(sleeves, correlations)
    portfolios = {
        "Benchmark": benchmark_weights(sleeves),
        "Equal weight": equal_weight_weights(sleeves),
        "Inverse volatility": inverse_volatility_weights(sleeves),
    }
    rows = []
    for name, weights in portfolios.items():
        expected_return = portfolio_expected_return(weights, sleeves)
        volatility = portfolio_volatility(weights, covariance)
        reserve_weight = reserve_eligible_weight(weights, RESERVE_ELIGIBLE)
        return_pass = meets_objective(expected_return, objective_return)
        reserve_pass = reserve_weight >= MINIMUM_RESERVE_WEIGHT
        rows.append(
            {
                "Portfolio": name,
                "Bills": weights["Treasury bills"],
                "10-year": weights["Treasury 10-year note"],
                "IG bonds": weights["Investment-grade bond fund"],
                "Equity": weights["Global equity index fund"],
                "Expected return": expected_return,
                "Volatility": volatility,
                "Reserve-eligible": reserve_weight,
                "Meets return objective": return_pass,
                "Meets reserve rule": reserve_pass,
                "Meets mandate": return_pass and reserve_pass,
            }
        )
    return rows


def choose_lowest_risk_compliant(rows):
    """Return the lowest-volatility portfolio that meets the screenable mandate."""
    compliant = [row for row in rows if row["Meets mandate"]]
    return min(compliant, key=lambda row: row["Volatility"]) if compliant else None


def format_percent(value, decimals=2):
    """Format a decimal as a percentage."""
    return f"{value:.{decimals}%}"


def main():
    """Render the client-facing portfolio comparison and stress test."""
    st.set_page_config(page_title="Meridian Portfolio Lab", layout="wide")
    st.title("Meridian portfolio comparison")
    st.caption("Expected returns are estimates, not promises. CPI is assumed to be 2.5%, making the return objective 6.5%.")

    sleeves, correlations = copy_inputs()

    with st.sidebar:
        st.header("Controls")
        objective = st.slider(
            "Objective return", min_value=0.03, max_value=0.10,
            value=OBJECTIVE_RETURN, step=0.001, format="%.1f%%",
        )
        st.subheader("Sleeve assumptions")
        for sleeve in SLEEVE_ORDER:
            sleeves[sleeve]["expected_return"] = st.slider(
                f"{sleeve} expected return", 0.00, 0.15,
                sleeves[sleeve]["expected_return"], 0.001, format="%.1f%%",
            )
            sleeves[sleeve]["volatility"] = st.slider(
                f"{sleeve} volatility", 0.001, 0.30,
                sleeves[sleeve]["volatility"], 0.001, format="%.1f%%",
            )

        st.subheader("Key correlation")
        ig_equity_correlation = st.slider(
            "IG bonds ↔ equity correlation", -1.00, 1.00,
            correlations["Investment-grade bond fund"]["Global equity index fund"], 0.01,
        )
        correlations["Investment-grade bond fund"]["Global equity index fund"] = ig_equity_correlation
        correlations["Global equity index fund"]["Investment-grade bond fund"] = ig_equity_correlation

    try:
        rows = portfolio_rows(sleeves, correlations, objective)
    except ValueError as error:
        st.error(f"Input validation failed: {error}")
        st.stop()

    winner = choose_lowest_risk_compliant(rows)
    if winner:
        st.success(
            f"Lowest-risk compliant mix: {winner['Portfolio']} "
            f"at {format_percent(winner['Volatility'])} volatility."
        )
    else:
        st.warning(
            "No baseline mix meets both the return objective and the 3.0% reserve-eligible minimum. "
            "The benchmark meets return but has no reserve allocation; the other two meet the reserve rule but miss return."
        )

    st.subheader("Baseline comparison")
    st.dataframe(
        [
            {
                "Portfolio": row["Portfolio"],
                "Weights: bills / 10-year / IG / equity": " / ".join(
                    format_percent(row[column], 1)
                    for column in ("Bills", "10-year", "IG bonds", "Equity")
                ),
                "Expected return": format_percent(row["Expected return"]),
                "Volatility": format_percent(row["Volatility"]),
                "Reserve-eligible": format_percent(row["Reserve-eligible"], 1),
                "Meets 6.5%?": "Yes" if row["Meets return objective"] else "No",
                "Meets mandate?": "Yes" if row["Meets mandate"] else "No",
            }
            for row in rows
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("One-point estimate stress test")
    stress_sleeve = st.selectbox("Increase one sleeve's expected return by 1.0 percentage point", SLEEVE_ORDER)
    stressed_sleeves = {name: values.copy() for name, values in sleeves.items()}
    stressed_sleeves[stress_sleeve]["expected_return"] += 0.01
    stressed_rows = portfolio_rows(stressed_sleeves, correlations, objective)
    stressed_winner = choose_lowest_risk_compliant(stressed_rows)

    if stressed_winner:
        st.success(
            f"After the stress, {stressed_winner['Portfolio']} is the lowest-risk compliant mix "
            f"at {format_percent(stressed_winner['Volatility'])} volatility."
        )
    else:
        st.info(
            "The conclusion survives this one-point return-estimate change: no baseline mix meets both requirements."
        )

    st.dataframe(
        [
            {
                "Portfolio": row["Portfolio"],
                "Stressed expected return": format_percent(row["Expected return"]),
                "Volatility": format_percent(row["Volatility"]),
                "Meets mandate?": "Yes" if row["Meets mandate"] else "No",
            }
            for row in stressed_rows
        ],
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "Screened requirements: expected return at or above the objective and at least 3.0% in Treasury bills plus the 10-year note. "
        "This does not replace the mandate's liquidity, issuer concentration, turnover, or loss-limit review."
    )


if __name__ == "__main__":
    main()
