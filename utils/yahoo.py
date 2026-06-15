"""Yahoo Finance wrapper — pulls financial statements via yfinance.

Covers global equities (US, EU, Asia, etc.). No API key required.
Values returned in $M (divided by 1,000,000).
"""
from __future__ import annotations

import requests
import yfinance as yf

_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FinSight/1.0)"}

# ── Field name maps: our line item → yfinance DataFrame index names ──────────
# Lists are priority-ordered: first matching row wins.

BS_MAP: dict[str, list[str]] = {
    "Cash & Marketable Securities": [
        "Cash Cash Equivalents And Short Term Investments",
        "Cash And Cash Equivalents",
        "Cash And Short Term Investments",
    ],
    "Accounts Receivable": ["Receivables", "Accounts Receivable", "Net Receivables"],
    "Inventory": ["Inventory", "Inventories"],
    "Total Current Assets": ["Current Assets"],
    "Property, Plant & Equipment (PP&E)": ["Net PPE", "Property Plant And Equipment Net"],
    "Goodwill": ["Goodwill"],
    "Intangible Assets": ["Other Intangible Assets", "Intangible Assets"],
    "Total Assets": ["Total Assets"],
    "Accounts Payable": ["Accounts Payable", "Payables And Accrued Expenses"],
    "Accrued Expenses": ["Current Accrued Expenses", "Payables"],
    "Short-term Debt": ["Current Debt", "Short Term Debt", "Current Debt And Capital Lease Obligation"],
    "Operating Lease Liabilities": ["Current Deferred Liabilities", "Operating Lease Liabilities Current"],
    "Total Current Liabilities": ["Current Liabilities"],
    "Long-term Debt": [
        "Long Term Debt",
        "Long Term Debt And Capital Lease Obligation",
        "Long Term Debt Non Current",
    ],
    "Total Liabilities": ["Total Liabilities Net Minority Interest"],
    "Preferred Stock": ["Preferred Stock"],
    "Retained Earnings": ["Retained Earnings"],
    "Treasury Stock (cumulative buybacks)": ["Treasury Stock"],
    "Total Shareholders' Equity": [
        "Stockholders Equity",
        "Total Equity Gross Minority Interest",
    ],
}

IS_MAP: dict[str, list[str]] = {
    "Revenue": ["Total Revenue", "Operating Revenue"],
    "Cost of Goods Sold (COGS)": ["Cost Of Revenue", "Reconciled Cost Of Revenue"],
    "Gross Profit": ["Gross Profit"],
    "Research & Development (R&D)": ["Research And Development"],
    "Sales & Marketing (S&M)": ["Selling And Marketing Expense"],
    "General & Administrative (G&A)": [
        "General And Administrative Expense",
        "Selling General And Administration",
    ],
    "Total Operating Expenses": ["Operating Expense", "Total Operating Expenses"],
    "Operating Income (EBIT)": ["Operating Income", "EBIT"],
    "Interest Expense": [
        "Interest Expense",
        "Interest Expense Non Operating",
        "Net Interest Income",
    ],
    "Earnings Before Taxes (EBT)": ["Pretax Income"],
    "Income Tax Expense": ["Tax Provision"],
    "Net Income": ["Net Income", "Net Income Common Stockholders"],
    "Shares Outstanding": [
        "Diluted Average Shares",
        "Basic Average Shares",
        "Weighted Average Diluted Shares",
    ],
    "Diluted EPS": ["Diluted EPS", "Basic EPS"],
}

CF_MAP: dict[str, list[str]] = {
    "Net Income": ["Net Income From Continuing Operations", "Net Income"],
    "Depreciation & Amortization (D&A)": [
        "Depreciation And Amortization",
        "Depreciation Depletion And Amortization",
        "Depreciation",
    ],
    "Stock-Based Compensation (SBC)": ["Stock Based Compensation"],
    "Changes in Working Capital": ["Change In Working Capital"],
    "Operating Cash Flow (OCF)": ["Operating Cash Flow"],
    "Capital Expenditures (CapEx)": ["Capital Expenditure"],
    "Free Cash Flow (FCF)": ["Free Cash Flow"],
    "Cash from Investing": ["Investing Cash Flow"],
    "Cash from Financing": ["Financing Cash Flow"],
    "Net Change in Cash": ["Changes In Cash", "End Cash Position"],
}

_EPS_ITEMS   = {"Diluted EPS"}
_SHARE_ITEMS = {"Shares Outstanding"}


# ── Search ────────────────────────────────────────────────────────────────────

def search_tickers(query: str) -> list[dict]:
    """Search Yahoo Finance for tickers matching query. Returns up to 12 results."""
    try:
        r = requests.get(
            _SEARCH_URL,
            params={"q": query, "quotesCount": 12, "newsCount": 0, "listsCount": 0},
            headers=_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        quotes = r.json().get("quotes", [])
        results = []
        for q in quotes:
            if q.get("quoteType") not in ("EQUITY", "ETF"):
                continue
            results.append({
                "ticker":   q.get("symbol", ""),
                "name":     q.get("longname") or q.get("shortname", ""),
                "exchange": q.get("exchDisp") or q.get("exchange", ""),
            })
        return results
    except Exception:
        return []


# ── Data helpers ──────────────────────────────────────────────────────────────

def _pick(df, names: list[str]):
    """Return first matching row from a DataFrame, or None."""
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _get(series, col_idx: int, raw: bool = False) -> float:
    """Safely extract a value from a pandas Series at column position."""
    if series is None:
        return 0.0
    try:
        import pandas as pd
        v = series.iloc[col_idx]
        if pd.isna(v):
            return 0.0
        v = float(v)
        return v if raw else v / 1_000_000   # → $M
    except (IndexError, TypeError, ValueError):
        return 0.0


# ── Main builder ──────────────────────────────────────────────────────────────

def build_statements(
    ticker_sym: str,
    period_type: str = "annual",
    n_periods: int = 4,
) -> tuple[str, list[str], dict, dict, dict]:
    """
    Pull financial statements from Yahoo Finance.

    Args:
        ticker_sym   — Yahoo Finance ticker (e.g. "AAPL", "7203.T", "ASML.AS")
        period_type  — "annual" or "quarterly"
        n_periods    — how many periods to return (1–8)

    Returns:
        company_name, period_labels, balance_sheet, income_statement, cash_flow
    """
    t    = yf.Ticker(ticker_sym)
    info = t.fast_info or {}

    # Prefer longName from info dict (may require a separate call)
    try:
        full_info    = t.info or {}
        company_name = full_info.get("longName") or full_info.get("shortName") or ticker_sym.upper()
    except Exception:
        company_name = ticker_sym.upper()

    if period_type == "quarterly":
        inc_df = t.quarterly_income_stmt
        bs_df  = t.quarterly_balance_sheet
        cf_df  = t.quarterly_cash_flow
    else:
        inc_df = t.income_stmt
        bs_df  = t.balance_sheet
        cf_df  = t.cash_flow

    if inc_df is None or inc_df.empty:
        raise ValueError(
            f"No {period_type} financial data found for '{ticker_sym}'. "
            "Check the ticker symbol and try again."
        )

    n = min(n_periods, len(inc_df.columns))

    # Build period labels from column dates
    cols = list(inc_df.columns[:n])
    if period_type == "annual":
        period_labels = [f"FY{c.year}" for c in cols]
    else:
        _qmap = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
        period_labels = [f"{_qmap.get((c.month - 1) // 3 + 1, 'Q?')} {c.year}" for c in cols]

    def extract(stmt_map: dict, df) -> dict:
        stmt: dict = {}
        for line_item, names in stmt_map.items():
            stmt[line_item] = {}
            row = _pick(df, names)
            raw = line_item in _EPS_ITEMS or line_item in _SHARE_ITEMS
            for idx in range(n):
                stmt[line_item][idx] = _get(row, idx, raw=raw)
        return stmt

    bs  = extract(BS_MAP,  bs_df)
    inc = extract(IS_MAP,  inc_df)
    cf  = extract(CF_MAP,  cf_df)

    # CapEx: yfinance reports as negative — normalise to positive
    for idx in range(n):
        capex = abs(cf.get("Capital Expenditures (CapEx)", {}).get(idx, 0.0))
        cf["Capital Expenditures (CapEx)"][idx] = capex

        # If FCF not supplied by yfinance, compute OCF − CapEx
        if cf.get("Free Cash Flow (FCF)", {}).get(idx, 0.0) == 0.0:
            ocf = cf.get("Operating Cash Flow (OCF)", {}).get(idx, 0.0)
            cf.setdefault("Free Cash Flow (FCF)", {})[idx] = ocf - capex

    return company_name, period_labels, bs, inc, cf
