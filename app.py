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
    printed += " ROE at least 15% every year Owner earnings positive every year Owner earnings grew first year to last"
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

st.subheader("Buffett-style checks")
checks = pd.DataFrame([{"Check": name, "Result": str(result).lower() if isinstance(result, bool) else result} for name, result in panel["checks"].items()])
st.dataframe(checks, hide_index=True, width="stretch")

memo_path = ROOT / f"{ticker}_memo.md"
st.subheader("Business memo")
if memo_path.exists():
    memo = memo_path.read_text(encoding="utf-8")
    st.markdown(memo)
    unprinted = memo_audit(memo, panel)
    if unprinted:
        st.error("Memo numbers not printed by the script: " + ", ".join(unprinted))
    else:
        st.success("Every number in this memo appears in the script output.")
else:
    st.warning(f"No saved memo yet. Use the edgar-buffett-review skill after reviewing the printed {ticker} panel, then save {memo_path.name}.")

with st.expander("SEC extraction log"):
    st.code(log)
