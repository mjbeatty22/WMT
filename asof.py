"""Point-in-time data gate for the Lab 15 as-of exercise.

Only Python's standard library is used. Edit ROWS and DECISION_DATE below.
"""

from collections import defaultdict
from datetime import date


# Editable inputs -----------------------------------------------------------
DECISION_DATE = "2026-03-31"

ROWS = [
    {"row": 1, "ticker": "AAA", "month": "2026-01", "published": "2026-02-10", "price": 101.0},
    {"row": 2, "ticker": "AAA", "month": "2026-02", "published": "2026-03-10", "price": 104.0},
    {"row": 3, "ticker": "AAA", "month": "2026-03", "published": "2026-04-10", "price": 109.0},
    {"row": 4, "ticker": "AAA", "month": "2026-02", "published": "2026-03-25", "price": 103.0},
    {"row": 5, "ticker": "BBB", "month": "2026-01", "published": "2026-02-10", "price": 98.0},
    {"row": 6, "ticker": "BBB", "month": "2026-02", "published": "2026-03-10", "price": 97.0},
    {"row": 7, "ticker": "BBB", "month": "2026-02", "published": "2026-03-10", "price": 97.0},
    {"row": 8, "ticker": "BBB", "month": "2026-03", "published": "2026-04-10", "price": 92.0},
    {"row": 9, "ticker": "CCC", "month": "2026-01", "published": "2026-02-10", "price": 110.0},
    {"row": 10, "ticker": "CCC", "month": "2026-02", "published": "2026-04-05", "price": 112.0},
    {"row": 11, "ticker": "", "month": "2026-02", "published": "2026-03-10", "price": 99.0},
    {"row": 12, "ticker": "CCC", "month": "2026-02", "published": "2026-03-10", "price": 111.0},
]


def parse_date(text):
    """Convert an ISO date string to a date object."""
    return date.fromisoformat(text)


def quarantine_missing_ticker(rows):
    """Rule 1: quarantine rows without a ticker."""
    removed = [row for row in rows if not row["ticker"].strip()]
    kept = [row for row in rows if row["ticker"].strip()]
    return kept, removed


def remove_exact_duplicates(rows):
    """Rule 2: retain the first copy and remove later exact duplicates."""
    kept = []
    removed = []
    seen = set()
    for row in rows:
        signature = (row["ticker"], row["month"], row["published"], row["price"])
        if signature in seen:
            removed.append(row)
        else:
            seen.add(signature)
            kept.append(row)
    return kept, removed


def remove_late_publications(rows, decision_date):
    """Rule 3: remove rows not knowable on the decision date."""
    cutoff = parse_date(decision_date)
    removed = [row for row in rows if parse_date(row["published"]) > cutoff]
    kept = [row for row in rows if parse_date(row["published"]) <= cutoff]
    return kept, removed


def keep_latest_revision(rows):
    """Rule 4: retain the latest publication for each ticker-month pair."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["ticker"], row["month"])].append(row)

    kept = []
    removed = []
    for candidates in grouped.values():
        latest = max(candidates, key=lambda row: (parse_date(row["published"]), row["row"]))
        kept.append(latest)
        removed.extend(row for row in candidates if row is not latest)
    return kept, removed


def apply_asof_gates(rows, decision_date):
    """Apply the four rules in order and return the panel plus funnel details."""
    rules = [
        ("1. Missing ticker (quarantine)", quarantine_missing_ticker),
        ("2. Exact duplicate", remove_exact_duplicates),
        ("3. Published after decision date", lambda data: remove_late_publications(data, decision_date)),
        ("4. Superseded revision", keep_latest_revision),
    ]
    current = list(rows)
    funnel = []
    for name, rule in rules:
        current, removed = rule(current)
        funnel.append((name, removed))
    return sort_panel(current), funnel


def sort_panel(rows):
    """Return a consistently ordered ticker-month panel."""
    return sorted(rows, key=lambda row: (row["ticker"], row["month"], row["published"], row["row"]))


def latest_publication_panel(rows):
    """Build the deliberately naïve panel: ignore publication dates entirely."""
    without_missing_tickers, _ = quarantine_missing_ticker(rows)
    without_duplicates, _ = remove_exact_duplicates(without_missing_tickers)
    panel, _ = keep_latest_revision(without_duplicates)
    return sort_panel(panel)


def calculate_signals(panel):
    """Return each ticker's latest-month price change from its prior month."""
    grouped = defaultdict(list)
    for row in panel:
        grouped[row["ticker"]].append(row)

    signals = []
    for ticker in sorted(grouped):
        history = sorted(grouped[ticker], key=lambda row: row["month"])
        if len(history) < 2:
            continue
        previous, latest = history[-2], history[-1]
        percent_change = (latest["price"] / previous["price"] - 1) * 100
        signals.append({
            "ticker": ticker,
            "month": latest["month"],
            "percent_change": percent_change,
            "previous_price": previous["price"],
            "latest_price": latest["price"],
        })
    return signals


def print_funnel(funnel):
    """Print how each rule changed the population of rows."""
    print("ROW FUNNEL")
    for name, removed in funnel:
        row_numbers = ", ".join(str(row["row"]) for row in removed) or "none"
        print(f"{name}: removed {len(removed)} row(s): {row_numbers}")


def print_panel(title, panel):
    """Print a row-level panel with provenance."""
    print(f"\n{title}")
    print("Row  Ticker  Month     Published    Price")
    for row in panel:
        print(f"{row['row']:>3}  {row['ticker']:<6}  {row['month']}  {row['published']}  {row['price']:>6.1f}")


def print_signals(title, signals):
    """Print the latest available signal per ticker."""
    print(f"\n{title}")
    for signal in signals:
        print(
            f"{signal['ticker']}: {signal['month']} {signal['percent_change']:+.2f}% "
            f"({signal['previous_price']:.1f} to {signal['latest_price']:.1f})"
        )


def main():
    asof_panel, funnel = apply_asof_gates(ROWS, DECISION_DATE)
    naive_panel = latest_publication_panel(ROWS)
    print(f"Decision date: {DECISION_DATE}")
    print_funnel(funnel)
    print_panel("AS-OF PANEL", asof_panel)
    print_signals("AS-OF SIGNALS", calculate_signals(asof_panel))
    print_signals("NAIVE SIGNALS (ignores publication date)", calculate_signals(naive_panel))


if __name__ == "__main__":
    main()
