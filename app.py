"""Streamlit review surface for SEC-only five-year business-quality panels."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from investor_panel import investor_memo, panel_checks, verdict

ROOT = Path(__file__).parent
SCRIPT = ROOT / "scripts" / "edgar_five_years.py"


def run_analysis(ticker: str, email: str, analyst: str) -> tuple[dict | None, str]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
        output = Path(temp.name)
    command = [sys.executable, str(SCRIPT), ticker, "--contact-email", email, "--analyst-name", analyst, "--write-json", str(output)]
    result = subprocess.run(command, text=True, capture_output=True, timeout=90)
    try:
        panel = json.loads(output.read_text(encoding="utf-8")) if result.returncode == 0 else None
    finally:
        output.unlink(missing_ok=True)
    return panel, result.stdout + result.stderr


def text_value(item: dict | None) -> str:
    return "not found" if item is None else f"{item['value']:,} [{item['tag']}]"


def allowed_numbers(panel: dict) -> set[str]:
    """Only digits printed by the script's panel or check labels may appear in the memo."""
    printed = json.dumps(panel)
    for row in panel["rows"]:
        if row["roe"] is not None:
            printed += f" {row['roe']:.2%}"
    for value in panel.get("derived", {}).values():
        if value != "not known":
            printed += f" {value:.2%}"
    liabilities_to_equity = panel.get("derived", {}).get("Liabilities to latest-year equity")
    if liabilities_to_equity not in (None, "not known"):
        printed += f" {liabilities_to_equity:.2f}"
    printed += (
        " ROE at least 15% every year Owner earnings positive every year "
        "Owner earnings grew first year to last Revenue growth per year at least 5% "
        "Latest-year R&D at least 5% of revenue Operating cash flow at least net income every year "
        "Latest-year liabilities no more than twice equity"
    )
    return set(re.findall(r"\d+(?:\.\d+)?", printed))


def memo_audit(memo: str, panel: dict) -> list[str]:
    allowed = allowed_numbers(panel)
    found = re.findall(r"\d+(?:\.\d+)?", memo.replace(",", ""))
    return sorted(set(number for number in found if number not in allowed), key=float)


st.set_page_config(page_title="SEC EDGAR Buffett review", layout="wide")
st.title("SEC EDGAR Buffett-style business review")
st.caption("Data from SEC EDGAR; built with AI help, a learning demonstration, not investment advice.")

with st.sidebar:
    ticker = st.text_input("Ticker", value="WMT").strip().upper()
    contact_email = st.text_input("SEC contact email", type="default", help="Required in the SEC User-Agent; use a real contact email.").strip()
    analyst_name = st.text_input("Analyst name", value="Mark Beatty").strip() or "Mark Beatty"
    run = st.button("Download 10-K facts", type="primary")

if not run:
    st.info("Enter a real SEC contact email, then download the filing facts.")
    st.stop()
if not ticker or "@" not in contact_email:
    st.error("Enter a ticker and a real contact email before downloading SEC EDGAR data.")
    st.stop()

with st.spinner(f"Downloading 10-K facts for {ticker} from SEC EDGAR..."):
    panel, log = run_analysis(ticker, contact_email, analyst_name)
if panel is None:
    st.error("The SEC extraction failed. Details follow.")
    st.code(log)
    st.stop()

rows = []
for row in panel["rows"]:
    values = row["values"]
    rows.append({
        "Fiscal year end": row["fiscal_year_end"],
        "Revenue": text_value(values["revenue"]),
        "Net income": text_value(values["net_income"]),
        "Operating cash flow": text_value(values["operating_cash_flow"]),
        "Capital spending": text_value(values["capital_spending"]),
        "Equity": text_value(values["equity"]),
        "Liabilities": text_value(values.get("liabilities")),
        "R&D expense": text_value(values.get("research_and_development_expense")),
        "ROE": "not known" if row["roe"] is None else f"{row['roe']:.2%}",
        "Owner earnings": "not known" if row["owner_earnings"] is None else f"{row['owner_earnings']:,}",
        "_net_income": None if values["net_income"] is None else values["net_income"]["value"],
        "_owner_earnings": row["owner_earnings"],
    })
table = pd.DataFrame(rows)
st.subheader(f"{panel['company']} ({panel['ticker']})")
chart = table.set_index("Fiscal year end")[["_owner_earnings", "_net_income"]].rename(columns={"_owner_earnings": "Owner earnings", "_net_income": "Net income"})
st.line_chart(chart, width="stretch")
st.dataframe(table.drop(columns=["_net_income", "_owner_earnings"]), hide_index=True, width="stretch")

st.subheader("Three-investor panel")
all_checks = panel_checks(panel)
panel_rows = []
derived = panel.get("derived", {})
for investor, checks in all_checks.items():
    for name, result in checks.items():
        evidence = ""
        if name.startswith("Revenue growth per year"):
            value = derived.get("Revenue growth per year, first year to last")
            evidence = "not known" if value in (None, "not known") else f"{value:.2%}"
        elif name.startswith("Latest-year liabilities"):
            value = derived.get("Liabilities to latest-year equity")
            evidence = "not known" if value in (None, "not known") else f"{value:.2f}"
        panel_rows.append({"Investor": investor, "Check": name, "Result": result, "Evidence": evidence, "Verdict": verdict(checks)})
st.dataframe(pd.DataFrame(panel_rows), hide_index=True, width="stretch")

st.subheader("Business memos")
memos = {investor: investor_memo(investor, panel, checks) for investor, checks in all_checks.items()}
columns = st.columns(3)
for column, (investor, memo) in zip(columns, memos.items()):
    with column:
        st.markdown(memo)

unprinted = {investor: memo_audit(memo, panel) for investor, memo in memos.items()}
flagged = {investor: values for investor, values in unprinted.items() if values}
if flagged:
    details = "; ".join(f"{investor}: {', '.join(values)}" for investor, values in flagged.items())
    st.error("Unprinted-number flag: " + details)
else:
    st.success("Unprinted-number flag: clear across all three memos.")

with st.expander("SEC extraction log"):
    st.code(log)
