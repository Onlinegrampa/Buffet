"""FinSight web app — enter financial statements in the browser, get instant analysis."""
from __future__ import annotations

import os

from flask import Flask, render_template, request

from analyzers.buffett import compute as buffett_compute
from analyzers.saas import compute as saas_compute
from analyzers.statements import (
    BALANCE_SHEET,
    CASH_FLOW,
    INCOME_STATEMENT,
    compute as stmt_compute,
)
from utils.profile import CompanyProfile

app = Flask(__name__)

MAX_PERIODS = 8
DEFAULT_PERIOD_LABELS = ["FY2024", "FY2023", "FY2022", "FY2021",
                         "FY2020", "FY2019", "FY2018", "FY2017"]

HIGHLIGHT = {
    "Total Assets", "Total Liabilities", "Total Shareholders' Equity",
    "Revenue", "Gross Profit", "Operating Income (EBIT)", "Net Income",
    "Operating Cash Flow (OCF)", "Free Cash Flow (FCF)",
}


@app.template_filter("money")
def money_filter(v: float | None) -> str:
    if v is None:
        return "n/a"
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.1f}M"


@app.template_filter("pct")
def pct_filter(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:+.1f}%"


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        balance_sheet=BALANCE_SHEET,
        income_statement=INCOME_STATEMENT,
        cash_flow=CASH_FLOW,
        highlight=HIGHLIGHT,
        max_periods=MAX_PERIODS,
        default_period_labels=DEFAULT_PERIOD_LABELS,
    )


@app.route("/analyze", methods=["POST"])
def analyze() -> str:
    n = min(MAX_PERIODS, max(2, int(request.form.get("n_periods") or 2)))
    periods = [
        (request.form.get(f"period_{i}") or DEFAULT_PERIOD_LABELS[i]).strip()
        for i in range(n)
    ]
    name = request.form.get("company_name", "").strip() or "Target Company"

    def parse_stmt(prefix: str, items: list[str]) -> dict:
        stmt: dict = {}
        for item_idx, item in enumerate(items):
            stmt[item] = {}
            for p_idx in range(n):
                try:
                    val = float(request.form.get(f"{prefix}_{item_idx}_{p_idx}") or 0)
                except ValueError:
                    val = 0.0
                stmt[item][p_idx] = val
        return stmt

    profile = CompanyProfile(name, periods)
    profile.balance_sheet    = parse_stmt("bs",  BALANCE_SHEET)
    profile.income_statement = parse_stmt("inc", INCOME_STATEMENT)
    profile.cash_flow        = parse_stmt("cf",  CASH_FLOW)

    stmt = stmt_compute(profile)
    buft = buffett_compute(profile.name, profile.buffett_inputs())

    r40 = profile.rule_of_40_inputs()
    growth = r40["growth"] if r40["growth"] is not None else 0.0
    saas_results = {
        label: saas_compute(profile.name, growth, (m if m is not None else 0.0), label)
        for label, m in r40["margins"].items()
    }

    return render_template(
        "results.html",
        company=name,
        periods=periods,
        stmt=stmt,
        buft=buft,
        saas_results=saas_results,
        growth=growth,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
