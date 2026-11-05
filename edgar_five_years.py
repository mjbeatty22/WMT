"""Extract a reproducible five-year 10-K panel from public SEC EDGAR facts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_spending": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "equity": ["StockholdersEquity"],
    "liabilities": ["Liabilities"],
    "research_and_development_expense": ["ResearchAndDevelopmentExpense"],
}
FLOWS = set(TAGS) - {"equity", "liabilities"}


def get_json(url: str, user_agent: str) -> dict:
    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"SEC EDGAR returned HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach SEC EDGAR: {exc.reason}") from exc


def annual_flow(fact: dict) -> bool:
    if fact.get("form") != "10-K" or not fact.get("start") or not fact.get("end"):
        return False
    try:
        days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days
    except ValueError:
        return False
    return 350 <= days <= 380


def point_fact(fact: dict) -> bool:
    return fact.get("form") == "10-K" and bool(fact.get("end")) and not fact.get("start")


def latest_by_end(facts: list[dict], valid) -> dict[str, dict]:
    """The newest filed 10-K wins when it repeats an end date."""
    chosen = {}
    for fact in facts:
        if not valid(fact):
            continue
        prior = chosen.get(fact["end"])
        if prior is None or (fact.get("filed", ""), fact.get("accn", "")) > (prior.get("filed", ""), prior.get("accn", "")):
            chosen[fact["end"]] = fact
    return chosen


def facts_for(company_facts: dict, tag: str, flow: bool) -> dict[str, dict]:
    concept = company_facts.get("facts", {}).get("us-gaap", {}).get(tag, {})
    facts = concept.get("units", {}).get("USD", [])
    return latest_by_end(facts, annual_flow if flow else point_fact)


def value_for(company_facts: dict, metric: str, fiscal_end: str) -> dict | None:
    for tag in TAGS[metric]:
        item = facts_for(company_facts, tag, metric in FLOWS).get(fiscal_end)
        if item:
            return {"value": item["val"], "tag": tag, "filed": item.get("filed"), "accession": item.get("accn")}
    return None


def fiscal_ends(company_facts: dict) -> list[str]:
    ends = set()
    for metric in FLOWS:
        for tag in TAGS[metric]:
            ends.update(facts_for(company_facts, tag, True))
    return sorted(ends)[-5:]


def build_panel(ticker: str, company_facts: dict) -> dict:
    rows = []
    for end in fiscal_ends(company_facts):
        values = {metric: value_for(company_facts, metric, end) for metric in TAGS}
        equity, income = values["equity"], values["net_income"]
        ocf, capex = values["operating_cash_flow"], values["capital_spending"]
        roe = income["value"] / equity["value"] if income and equity and equity["value"] > 0 else None
        owner_earnings = ocf["value"] - capex["value"] if ocf and capex else None
        rows.append({"fiscal_year_end": end, "values": values, "roe": roe, "owner_earnings": owner_earnings})

    def each(test):
        results = [test(row) for row in rows]
        return "not known" if not results or any(result is None for result in results) else all(results)

    growth = "not known"
    if len(rows) == 5 and rows[0]["owner_earnings"] is not None and rows[-1]["owner_earnings"] is not None:
        growth = rows[-1]["owner_earnings"] > rows[0]["owner_earnings"]
    revenue_growth = "not known"
    if len(rows) == 5 and rows[0]["values"]["revenue"] and rows[-1]["values"]["revenue"]:
        first_revenue = rows[0]["values"]["revenue"]["value"]
        last_revenue = rows[-1]["values"]["revenue"]["value"]
        if first_revenue > 0 and last_revenue >= 0:
            revenue_growth = (last_revenue / first_revenue) ** (1 / 4) - 1

    latest = rows[-1] if rows else None
    r_and_d_ratio = "not known"
    if latest and latest["values"]["research_and_development_expense"] and latest["values"]["revenue"]:
        latest_revenue = latest["values"]["revenue"]["value"]
        if latest_revenue > 0:
            r_and_d_ratio = latest["values"]["research_and_development_expense"]["value"] / latest_revenue

    liabilities_to_equity = "not known"
    if latest and latest["values"]["liabilities"] and latest["values"]["equity"]:
        latest_equity = latest["values"]["equity"]["value"]
        if latest_equity > 0:
            liabilities_to_equity = latest["values"]["liabilities"]["value"] / latest_equity

    return {
        "ticker": ticker, "company": company_facts.get("entityName", "not found"),
        "download_date": date.today().isoformat(), "rows": rows,
        "checks": {
            "ROE at least 15% every year": each(lambda row: None if row["roe"] is None else row["roe"] >= .15),
            "Owner earnings positive every year": each(lambda row: None if row["owner_earnings"] is None else row["owner_earnings"] > 0),
            "Owner earnings grew, first year to last": growth,
        },
        "derived": {
            "Revenue growth per year, first year to last": revenue_growth,
            "R&D as a share of latest-year revenue": r_and_d_ratio,
            "Liabilities to latest-year equity": liabilities_to_equity,
        },
    }


def printable(item: dict | None) -> str:
    return "not found" if item is None else f"{item['value']:,} [{item['tag']}]"


def print_panel(panel: dict) -> None:
    print(f"{panel['company']} ({panel['ticker']}) - SEC EDGAR 10-K facts")
    for row in panel["rows"]:
        print(f"\nFiscal year end: {row['fiscal_year_end']}")
        for metric in TAGS:
            print(f"  {metric.replace('_', ' ')}: {printable(row['values'][metric])}")
        print("  ROE: " + ("not known" if row["roe"] is None else f"{row['roe']:.2%}"))
        print("  owner earnings: " + ("not known" if row["owner_earnings"] is None else f"{row['owner_earnings']:,}"))
    print("\nChecks:")
    for label, result in panel["checks"].items():
        print(f"  {label}: {str(result).lower() if isinstance(result, bool) else result}")
    print("\nDerived values:")
    for label, value in panel["derived"].items():
        if value == "not known":
            display = "not known"
        elif label == "Liabilities to latest-year equity":
            display = f"{value:.2f}"
        else:
            display = f"{value:.2%}"
        print(f"  {label}: {display}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--contact-email", required=True, help="A real contact email for the SEC User-Agent.")
    parser.add_argument("--analyst-name", default="Mark Beatty")
    parser.add_argument("--write-json", type=Path)
    args = parser.parse_args()
    if "@" not in args.contact_email:
        parser.error("--contact-email must be a real contact email address.")
    user_agent = f"EDGAR Buffett Review/1.0 {args.analyst_name} {args.contact_email}"
    ticker = args.ticker.upper()
    cik = next((int(v["cik_str"]) for v in get_json(TICKERS_URL, user_agent).values() if v["ticker"].upper() == ticker), None)
    if cik is None:
        raise RuntimeError(f"Ticker {ticker} was not found in SEC's ticker-to-CIK file.")
    panel = build_panel(ticker, get_json(FACTS_URL.format(cik=cik), user_agent))
    panel["cik"] = f"{cik:010d}"
    print_panel(panel)
    if args.write_json:
        args.write_json.write_text(json.dumps(panel, indent=2), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
