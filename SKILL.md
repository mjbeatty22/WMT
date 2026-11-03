---
name: edgar-buffett-review
description: Analyze a U.S. public-company ticker from SEC EDGAR 10-K facts using Buffett-style business-quality checks; use when a filing-only, reproducible five-year review is requested.
---

# SEC EDGAR Buffett Review

Use this skill for a business-quality review based only on SEC EDGAR 10-K XBRL company facts. Do not install or use FAskills, paid-data services, market-price data, or estimates.

1. Run `scripts/edgar_five_years.py TICKER --contact-email EMAIL --write-json OUTPUT.json`. The email must be a real contact email supplied by the user; do not invent one. The script sends a keyless SEC EDGAR request with a User-Agent containing the analyst's name and contact email.
2. Use only the script's printed or JSON values. Preserve `not found` and `not known`; do not fill a gap with an estimate or a number from another source.
3. The script considers 10-K facts only, labels rows by fiscal-year-end date, uses annual flow facts, and retains the latest filed fact for a repeated period. Its tag priority and calculation rules are the project data contract.
4. Write `TICKER_memo.md`, based only on script output, with one conclusion: **own the business**, **watch it**, or **pass**. Judge the business rather than its price. State the supporting printed trends and checks, the material missing data, and no unprinted numerical claims. Do not imitate Buffett's distinctive writing style; use a concise, plain-language business-owner lens.
5. Run `streamlit run app.py` from the skill folder, enter the same real contact email, and inspect the chart, table, checks, memo, and memo-number audit. Fix a demonstrated extraction, period-selection, or display error before reporting completion.

## Project data contract

- Use only the last five fiscal years from 10-K filings. A later filing wins for the same fiscal-year-end date.
- Flows must span one year. Revenue tags: `RevenueFromContractWithCustomerExcludingAssessedTax`, then `Revenues`. Net income: `NetIncomeLoss`. Operating cash flow: `NetCashProvidedByUsedInOperatingActivities`. Capital spending: `PaymentsToAcquirePropertyPlantAndEquipment`, then `PaymentsToAcquireProductiveAssets`. Equity: `StockholdersEquity`.
- ROE = net income / year-end equity. Owner earnings = operating cash flow - capital spending. With missing inputs, output `not known`; a missing source value is `not found`. With equity <= 0, ROE is `not known`.
- Compute in code: ROE >= 15% in every year; positive owner earnings in every year; owner earnings grew from first year to last. A check with missing inputs is `not known`.

## Sources

- SEC tickers: <https://www.sec.gov/files/company_tickers.json>
- SEC company facts: <https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json>
- [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Buffett's 1986 shareholder letter](https://www.berkshirehathaway.com/letters/1986.html)
- [Streamlit documentation](https://docs.streamlit.io/)
