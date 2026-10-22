"""Compute simple Meridian portfolio return, volatility, and reserve exposure.

Uses only Python's standard library.  Inputs are grouped below so the file can
be reused with different sleeve assumptions.
"""

import csv
from io import StringIO
from math import sqrt
import sys


# --- Editable inputs -------------------------------------------------------

SLEEVES = {
    "Treasury bills": {"expected_return": 0.035, "volatility": 0.005},
    "Treasury 10-year note": {"expected_return": 0.043, "volatility": 0.070},
    "Investment-grade bond fund": {"expected_return": 0.050, "volatility": 0.060},
    "Global equity index fund": {"expected_return": 0.080, "volatility": 0.160},
}

CORRELATIONS = {
    "Treasury bills": {
        "Treasury bills": 1.00,
        "Treasury 10-year note": 0.10,
        "Investment-grade bond fund": 0.05,
        "Global equity index fund": 0.00,
    },
    "Treasury 10-year note": {
        "Treasury bills": 0.10,
        "Treasury 10-year note": 1.00,
        "Investment-grade bond fund": 0.80,
        "Global equity index fund": -0.10,
    },
    "Investment-grade bond fund": {
        "Treasury bills": 0.05,
        "Treasury 10-year note": 0.80,
        "Investment-grade bond fund": 1.00,
        "Global equity index fund": 0.25,
    },
    "Global equity index fund": {
        "Treasury bills": 0.00,
        "Treasury 10-year note": -0.10,
        "Investment-grade bond fund": 0.25,
        "Global equity index fund": 1.00,
    },
}

# CPI is a labelled estimate of 2.5%; the objective is CPI + 4.0%.
OBJECTIVE_RETURN = 0.065
RESERVE_ELIGIBLE = {"Treasury bills", "Treasury 10-year note"}


def validate_correlation_table(sleeves, correlations):
    """Raise ValueError when a correlation table is incomplete, invalid, or asymmetric."""
    names = set(sleeves)
    if set(correlations) != names:
        raise ValueError("Correlation table must have exactly one row for every sleeve.")

    for left in names:
        if set(correlations[left]) != names:
            raise ValueError(f"Correlation row for '{left}' must contain every sleeve.")
        for right in names:
            correlation = correlations[left][right]
            if not -1.0 <= correlation <= 1.0:
                raise ValueError(
                    f"Correlation between '{left}' and '{right}' is {correlation}; "
                    "correlations must be between -1 and 1."
                )
            if correlation != correlations[right][left]:
                raise ValueError(
                    f"Correlation table is not symmetric: '{left}'/'{right}' differs "
                    f"from '{right}'/'{left}'."
                )


def build_covariance_matrix(sleeves, correlations):
    """Return a nested covariance dictionary: correlation × vol_i × vol_j."""
    return {
        left: {
            right: correlations[left][right]
            * sleeves[left]["volatility"]
            * sleeves[right]["volatility"]
            for right in sleeves
        }
        for left in sleeves
    }


def benchmark_weights(sleeves):
    """Return the Lab 13 60/40 benchmark weights."""
    return {
        sleeve: 0.60 if sleeve == "Global equity index fund"
        else 0.40 if sleeve == "Investment-grade bond fund"
        else 0.0
        for sleeve in sleeves
    }


def equal_weight_weights(sleeves):
    """Return equal weights across all sleeves."""
    return {sleeve: 1.0 / len(sleeves) for sleeve in sleeves}


def inverse_volatility_weights(sleeves):
    """Return weights proportional to one divided by each sleeve's volatility."""
    inverse_volatilities = {
        sleeve: 1.0 / inputs["volatility"] for sleeve, inputs in sleeves.items()
    }
    total_inverse_volatility = sum(inverse_volatilities.values())
    return {
        sleeve: inverse_volatility / total_inverse_volatility
        for sleeve, inverse_volatility in inverse_volatilities.items()
    }


def portfolio_expected_return(weights, sleeves):
    """Return the weighted expected return."""
    return sum(weights[sleeve] * sleeves[sleeve]["expected_return"] for sleeve in sleeves)


def portfolio_volatility(weights, covariance_matrix):
    """Return portfolio volatility as sqrt(w' covariance w)."""
    variance = sum(
        weights[left] * weights[right] * covariance_matrix[left][right]
        for left in weights
        for right in weights
    )
    if variance < 0:
        raise ValueError("Portfolio variance cannot be negative.")
    return sqrt(variance)


def reserve_eligible_weight(weights, reserve_eligible):
    """Return the total portfolio weight in the mandate's reserve-eligible sleeves."""
    return sum(weights[sleeve] for sleeve in reserve_eligible)


def meets_objective(expected_return, objective_return):
    """Return whether expected return meets or exceeds the objective."""
    return expected_return >= objective_return


def generate_long_only_weights(asset_names, step=0.05):
    """Yield every long-only weight vector whose weights sum to 100%."""
    if not asset_names:
        raise ValueError("At least one asset is required.")
    units = round(1.0 / step)
    if abs(units * step - 1.0) > 1e-9:
        raise ValueError("Step size must divide evenly into 100%.")

    def allocate(position, remaining, current):
        if position == len(asset_names) - 1:
            yield dict(current, **{asset_names[position]: remaining * step})
            return
        for units_for_asset in range(remaining + 1):
            next_current = dict(current)
            next_current[asset_names[position]] = units_for_asset * step
            yield from allocate(position + 1, remaining - units_for_asset, next_current)

    yield from allocate(0, units, {})


def find_lowest_risk_mix(
    sleeves,
    correlations,
    objective_return,
    reserve_eligible,
    minimum_reserve_weight,
    step=0.05,
):
    """Return the lowest-volatility feasible mix, or None when none is feasible."""
    validate_correlation_table(sleeves, correlations)
    covariance_matrix = build_covariance_matrix(sleeves, correlations)
    best = None
    for weights in generate_long_only_weights(list(sleeves), step):
        expected_return = portfolio_expected_return(weights, sleeves)
        reserve_weight = reserve_eligible_weight(weights, reserve_eligible)
        if expected_return < objective_return or reserve_weight < minimum_reserve_weight:
            continue
        volatility = portfolio_volatility(weights, covariance_matrix)
        if best is None or volatility < best["volatility"]:
            best = {
                "weights": weights,
                "expected_return": expected_return,
                "volatility": volatility,
                "reserve_eligible_weight": reserve_weight,
            }
    return best


def estimate_from_price_csv(csv_source, last_36_months=False):
    """Estimate annualized statistics from oldest-first monthly adjusted closes.

    Return estimates are historical annualized arithmetic means, not forecasts.
    ``csv_source`` may be CSV text, a path, or a text file-like object.
    """
    if hasattr(csv_source, "read"):
        text = csv_source.read()
    elif "\n" in str(csv_source):
        text = str(csv_source)
    else:
        with open(csv_source, "r", newline="", encoding="utf-8") as price_file:
            text = price_file.read()
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        raise ValueError("CSV needs a date column followed by at least one ticker column.")
    if reader.fieldnames[0].strip().lower() != "date":
        raise ValueError("The first CSV column must be named 'date'.")
    tickers = reader.fieldnames[1:]
    prices = {ticker: [] for ticker in tickers}
    row_count = 0
    for row in reader:
        row_count += 1
        for ticker in tickers:
            try:
                price = float(row[ticker])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid price for {ticker} in row {row_count + 1}.") from error
            if price <= 0:
                raise ValueError(f"Prices must be positive; found {price} for {ticker}.")
            prices[ticker].append(price)
    if row_count < 3:
        raise ValueError("CSV needs at least three monthly price rows.")

    monthly_returns = {
        ticker: [
            prices[ticker][index] / prices[ticker][index - 1] - 1.0
            for index in range(1, len(prices[ticker]))
        ]
        for ticker in tickers
    }
    if last_36_months:
        monthly_returns = {ticker: returns[-36:] for ticker, returns in monthly_returns.items()}
    periods = len(next(iter(monthly_returns.values())))
    if periods < 2:
        raise ValueError("At least three monthly returns are needed to estimate volatility.")

    means = {ticker: sum(returns) / periods for ticker, returns in monthly_returns.items()}
    standard_deviations = {
        ticker: sqrt(sum((value - means[ticker]) ** 2 for value in returns) / (periods - 1))
        for ticker, returns in monthly_returns.items()
    }
    if any(deviation == 0 for deviation in standard_deviations.values()):
        raise ValueError("Cannot calculate correlation when a ticker has zero return volatility.")

    correlations = {}
    for left in tickers:
        correlations[left] = {}
        for right in tickers:
            covariance = sum(
                (monthly_returns[left][index] - means[left])
                * (monthly_returns[right][index] - means[right])
                for index in range(periods)
            ) / (periods - 1)
            correlation = covariance / (
                standard_deviations[left] * standard_deviations[right]
            )
            # Numerical rounding can put a mathematically valid correlation a
            # tiny amount above 1 or below -1.
            correlations[left][right] = 1.0 if left == right else max(-1.0, min(1.0, correlation))
    sleeves = {
        ticker: {
            "expected_return": means[ticker] * 12,
            "volatility": standard_deviations[ticker] * sqrt(12),
        }
        for ticker in tickers
    }
    validate_correlation_table(sleeves, correlations)
    return sleeves, correlations


def format_weights(weights):
    """Return a one-line, one-decimal-percent rendering of sleeve weights."""
    return ", ".join(f"{sleeve}: {weight:.1%}" for sleeve, weight in weights.items())


def print_portfolio(name, weights, sleeves, covariance_matrix):
    """Calculate and print a portfolio's required Lab 13 metrics."""
    expected_return = portfolio_expected_return(weights, sleeves)
    volatility = portfolio_volatility(weights, covariance_matrix)
    reserve_weight = reserve_eligible_weight(weights, RESERVE_ELIGIBLE)

    print(f"\n{name}")
    print(f"  Weights: {format_weights(weights)}")
    print(f"  Expected return: {expected_return:.2%}")
    print(f"  Volatility: {volatility:.2%}")
    print(f"  Reserve-eligible weight: {reserve_weight:.1%}")
    print(f"  Meets {OBJECTIVE_RETURN:.1%} objective: {'Yes' if meets_objective(expected_return, OBJECTIVE_RETURN) else 'No'}")


def main():
    """Validate inputs, build covariance, and print the three portfolio baselines."""
    validate_correlation_table(SLEEVES, CORRELATIONS)
    covariance_matrix = build_covariance_matrix(SLEEVES, CORRELATIONS)
    portfolios = {
        "Benchmark (40% IG bonds / 60% equity)": benchmark_weights(SLEEVES),
        "Equal weight": equal_weight_weights(SLEEVES),
        "Inverse volatility": inverse_volatility_weights(SLEEVES),
    }

    print(f"Objective return: {OBJECTIVE_RETURN:.2%} (CPI estimate of 2.5% + 4.0%)")
    for name, weights in portfolios.items():
        print_portfolio(name, weights, SLEEVES, covariance_matrix)


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"Input validation failed: {error}")
        sys.exit(1)
