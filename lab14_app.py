"""Interactive Lab 14 portfolio-search app.

Run: python -m streamlit run lab14_app.py
"""

import streamlit as st

from portfolio import (
    CORRELATIONS,
    OBJECTIVE_RETURN,
    RESERVE_ELIGIBLE,
    SLEEVES,
    estimate_from_price_csv,
    find_lowest_risk_mix,
)


DEFAULT_RESERVE_MINIMUM = 0.03


def clone_sleeves(sleeves):
    """Return editable copies without changing the engine's imported inputs."""
    return {asset: assumptions.copy() for asset, assumptions in sleeves.items()}


def clone_correlations(correlations):
    """Return editable copies without changing the engine's imported inputs."""
    return {asset: row.copy() for asset, row in correlations.items()}


def display_mix(mix):
    """Render either a feasible mix or the required no-solution message."""
    if mix is None:
        st.warning("No mix meets the objective and reserve minimum.")
        return
    st.dataframe(
        [
            {"Asset": asset, "Weight": f"{weight:.1%}"}
            for asset, weight in mix["weights"].items()
        ],
        hide_index=True,
        width="stretch",
    )
    first, second = st.columns(2)
    first.metric("Expected return", f"{mix['expected_return']:.2%}")
    second.metric("Volatility", f"{mix['volatility']:.2%}")
    st.metric("Reserve-eligible weight", f"{mix['reserve_eligible_weight']:.2%}")


def largest_weight_change(current_mix, loaded_mix):
    """Return the largest absolute allocation movement in percentage points."""
    if current_mix is None or loaded_mix is None:
        return None
    changes = {
        asset: abs(current_mix["weights"][asset] - loaded_mix["weights"][asset])
        for asset in current_mix["weights"]
    }
    asset = max(changes, key=changes.get)
    return asset, changes[asset]


def main():
    """Render an editable portfolio search using functions from portfolio.py."""
    st.set_page_config(page_title="Lab 14 Portfolio Search", layout="wide")
    st.title("Lowest-risk portfolio search")
    st.caption("Built with AI help, a learning demonstration, not investment advice.")

    with st.sidebar:
        st.header("Mandate inputs")
        objective = st.number_input(
            "Objective return", min_value=-0.50, max_value=1.00,
            value=OBJECTIVE_RETURN, step=0.005, format="%.3f",
            help="Enter as a decimal: 0.065 means 6.5%.",
        )
        reserve_minimum = st.number_input(
            "Minimum reserve-eligible weight", min_value=0.0, max_value=1.0,
            value=DEFAULT_RESERVE_MINIMUM, step=0.005, format="%.3f",
            help="Enter as a decimal: 0.03 means 3.0%.",
        )
        price_upload = st.file_uploader("Upload prices.csv", type="csv")
        last_36_months = st.checkbox("Use only the last 36 monthly returns")

    # The comparison answer always uses CSV estimates over all available months.
    if price_upload is None:
        loaded_sleeves = clone_sleeves(SLEEVES)
        loaded_correlations = clone_correlations(CORRELATIONS)
        loaded_label = "Meridian inputs"
    else:
        try:
            loaded_sleeves, loaded_correlations = estimate_from_price_csv(
                price_upload.getvalue(), last_36_months=False
            )
            if not 3 <= len(loaded_sleeves) <= 6:
                st.error("Your prices.csv must contain prices for three to six funds.")
                st.stop()
            loaded_label = "CSV estimates using all available monthly returns"
        except ValueError as error:
            st.error(f"Could not estimate from prices.csv: {error}")
            st.stop()

    if price_upload is not None and last_36_months:
        try:
            active_sleeves, active_correlations = estimate_from_price_csv(
                price_upload.getvalue(), last_36_months=True
            )
            active_label = "CSV estimates using the last 36 monthly returns"
        except ValueError as error:
            st.error(f"Could not estimate from the last 36 months: {error}")
            st.stop()
    else:
        active_sleeves = clone_sleeves(loaded_sleeves)
        active_correlations = clone_correlations(loaded_correlations)
        active_label = loaded_label

    st.subheader("Expected-return estimates")
    st.caption("Historical annualized average returns are estimates, not forecasts.")
    editable_returns = st.columns(min(3, len(active_sleeves)))
    for index, asset in enumerate(active_sleeves):
        with editable_returns[index % len(editable_returns)]:
            active_sleeves[asset]["expected_return"] = st.number_input(
                asset, min_value=-1.0, max_value=2.0,
                value=float(active_sleeves[asset]["expected_return"]), step=0.005,
                format="%.3f", key=f"return_{asset}",
            )

    st.subheader("Reserve eligibility")
    reserve_eligible = set()
    reserve_columns = st.columns(min(3, len(active_sleeves)))
    for index, asset in enumerate(active_sleeves):
        with reserve_columns[index % len(reserve_columns)]:
            if st.checkbox(
                asset, value=asset in RESERVE_ELIGIBLE, key=f"reserve_{asset}"
            ):
                reserve_eligible.add(asset)

    try:
        loaded_mix = find_lowest_risk_mix(
            loaded_sleeves, loaded_correlations, objective, reserve_eligible,
            reserve_minimum,
        )
        current_mix = find_lowest_risk_mix(
            active_sleeves, active_correlations, objective, reserve_eligible,
            reserve_minimum,
        )
    except ValueError as error:
        st.error(f"Portfolio search could not run: {error}")
        st.stop()

    current_column, loaded_column = st.columns(2)
    with current_column:
        st.subheader(f"Lowest-risk mix: {active_label}")
        display_mix(current_mix)
    with loaded_column:
        st.subheader(f"Inputs as loaded: {loaded_label}")
        display_mix(loaded_mix)

    change = largest_weight_change(current_mix, loaded_mix)
    if change is not None:
        st.info(f"Largest weight change: {change[0]} by {change[1]:.1%} ({change[1] * 100:.1f} points).")
    elif current_mix is not None or loaded_mix is not None:
        st.info("Largest weight change is unavailable because one search has no feasible mix.")

    st.caption("Search grid: every long-only portfolio in 5-percentage-point increments.")


if __name__ == "__main__":
    main()
