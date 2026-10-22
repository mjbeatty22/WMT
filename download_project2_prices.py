"""Download five completed years of monthly Yahoo Finance adjusted closes."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


TICKERS = ("SGOV", "IEI", "SPIB", "IVV")
# Oct. 2021 through Sep. 2026: 60 completed monthly observations.
PERIOD_START = 1633046400
PERIOD_END = 1790812800
OUTPUT_PATH = Path(__file__).resolve().parent / "prices.csv"


def fetch_adjusted_closes(ticker):
    """Return YYYY-MM-DD to adjusted-close mappings from Yahoo Finance."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={PERIOD_START}&period2={PERIOD_END}"
        "&interval=1mo&events=history&includeAdjustedClose=true"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    adjusted_closes = result["indicators"]["adjclose"][0]["adjclose"]
    prices = {}
    for timestamp, price in zip(timestamps, adjusted_closes):
        if price is not None:
            date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
            prices[date] = float(price)
    return prices


def main():
    """Fetch each selected fund and write a date-aligned monthly price file."""
    by_ticker = {ticker: fetch_adjusted_closes(ticker) for ticker in TICKERS}
    common_dates = sorted(set.intersection(*(set(prices) for prices in by_ticker.values())))
    if len(common_dates) != 60:
        raise ValueError(f"Expected 60 monthly observations; received {len(common_dates)}.")
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("date", *TICKERS))
        for date in common_dates:
            writer.writerow((date, *(f"{by_ticker[ticker][date]:.6f}" for ticker in TICKERS)))
    print(f"Wrote {len(common_dates)} monthly observations to {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
