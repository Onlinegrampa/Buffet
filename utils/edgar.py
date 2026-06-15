"""SEC EDGAR XBRL API — search companies and pull financial statement data.

Uses only the free public SEC APIs (data.sec.gov). No API key required.
Rate-limited to 10 requests/second per SEC guidelines.
"""
from __future__ import annotations

import time
from functools import lru_cache

import requests

HEADERS = {
    "User-Agent": "FinSight financial-analysis-tool attschris1995@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}
_BASE_FACTS = "https://data.sec.gov/api/xbrl/companyfacts"
_BASE_SUBS  = "https://data.sec.gov/submissions"


# ── XBRL concept → our statement line item mapping ────────────────────────────
# Lists are priority-ordered: first matching concept with a value wins.

BS_CONCEPTS: dict[str, list[str]] = {
    "Cash & Marketable Securities": [
        "CashCashEquivalentsAndShortTermInvestments",
        "CashAndCashEquivalentsAtCarryingValue",
        "CashAndCashEquivalents",
    ],
    "Accounts Receivable": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
        "AccountsReceivableNet",
    ],
    "Inventory": [
        "InventoryNet",
        "InventoryNetOfAllowancesCustomersAdvancesAndProgressBillings",
    ],
    "Total Current Assets": ["AssetsCurrent"],
    "Property, Plant & Equipment (PP&E)": ["PropertyPlantAndEquipmentNet"],
    "Goodwill": ["Goodwill"],
    "Intangible Assets": [
        "IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
    ],
    "Total Assets": ["Assets"],
    "Accounts Payable": ["AccountsPayableCurrent", "AccountsPayable"],
    "Accrued Expenses": [
        "AccruedLiabilitiesCurrent",
        "OtherAccruedLiabilitiesCurrent",
        "EmployeeRelatedLiabilitiesCurrent",
    ],
    "Short-term Debt": ["DebtCurrent", "ShortTermBorrowings", "NotesPayableCurrent"],
    "Operating Lease Liabilities": [
        "OperatingLeaseLiabilityCurrent",
        "CapitalLeaseObligationsCurrent",
    ],
    "Total Current Liabilities": ["LiabilitiesCurrent"],
    "Long-term Debt": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermNotesPayable"],
    "Total Liabilities": ["Liabilities"],
    "Preferred Stock": ["PreferredStockValue"],
    "Retained Earnings": ["RetainedEarningsAccumulatedDeficit"],
    "Treasury Stock (cumulative buybacks)": [
        "TreasuryStockValue",
        "TreasuryStockCommonValue",
    ],
    "Total Shareholders' Equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
}

IS_CONCEPTS: dict[str, list[str]] = {
    "Revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet",
        "RevenueFromContractsWithCustomers",
    ],
    "Cost of Goods Sold (COGS)": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfSales",
    ],
    "Gross Profit": ["GrossProfit"],
    "Research & Development (R&D)": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ],
    "Sales & Marketing (S&M)": [
        "SellingAndMarketingExpense",
        "SellingExpense",
        "MarketingExpense",
    ],
    "General & Administrative (G&A)": ["GeneralAndAdministrativeExpense"],
    "Total Operating Expenses": ["OperatingExpenses", "CostsAndExpenses"],
    "Operating Income (EBIT)": ["OperatingIncomeLoss"],
    "Interest Expense": [
        "InterestExpense",
        "InterestAndDebtExpense",
        "InterestExpenseDebt",
    ],
    "Earnings Before Taxes (EBT)": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "Income Tax Expense": ["IncomeTaxExpenseBenefit"],
    "Net Income": ["NetIncomeLoss", "ProfitLoss"],
    "Shares Outstanding": [
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
    "Diluted EPS": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
}

CF_CONCEPTS: dict[str, list[str]] = {
    "Net Income": ["NetIncomeLoss", "ProfitLoss"],
    "Depreciation & Amortization (D&A)": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ],
    "Stock-Based Compensation (SBC)": [
        "ShareBasedCompensation",
        "AllocatedShareBasedCompensationExpense",
        "StockBasedCompensation",
    ],
    "Changes in Working Capital": [
        "IncreaseDecreaseInOperatingCapital",
        "IncreaseDecreaseInOperatingLiabilities",
    ],
    "Operating Cash Flow (OCF)": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "Capital Expenditures (CapEx)": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForCapitalImprovements",
    ],
    "Free Cash Flow (FCF)": [],  # computed: OCF − CapEx
    "Cash from Investing": [
        "NetCashProvidedByUsedInInvestingActivities",
        "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations",
    ],
    "Cash from Financing": [
        "NetCashProvidedByUsedInFinancingActivities",
        "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
    ],
    "Net Change in Cash": [
        "CashCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        "CashAndCashEquivalentsPeriodIncreaseDecrease",
        "NetIncreaseDecreaseInCashAndCashEquivalents",
    ],
}

_SHARE_ITEMS = {"Shares Outstanding"}
_EPS_ITEMS   = {"Diluted EPS"}


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url: str) -> dict:
    time.sleep(0.11)  # SEC guideline: max 10 req/sec
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


# ── Company search ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _ticker_map() -> dict:
    """Download SEC's full ticker→CIK map and cache it in memory."""
    data = _get("https://www.sec.gov/files/company_tickers.json")
    return {v["ticker"].upper(): v for v in data.values()}


def search_companies(query: str) -> list[dict]:
    """Search by ticker (exact) or company name (substring). Returns up to 12 results."""
    query = query.strip()
    if not query:
        return []
    qu = query.upper()
    ql = query.lower()
    tmap = _ticker_map()
    results: list[dict] = []
    seen: set[str] = set()

    def _add(v: dict) -> None:
        cik = str(v["cik_str"]).zfill(10)
        if cik not in seen:
            seen.add(cik)
            results.append({"cik": cik, "ticker": v["ticker"], "name": v["title"]})

    # Exact ticker match first
    if qu in tmap:
        _add(tmap[qu])

    # Substring match on ticker or company name
    for v in tmap.values():
        if len(results) >= 12:
            break
        if ql in v["title"].lower() or ql in v["ticker"].lower():
            _add(v)

    return results


# ── Filings list ──────────────────────────────────────────────────────────────

def get_filings(cik: str, form_types: list[str]) -> list[dict]:
    """Return the most recent filings of the requested types for a CIK."""
    data   = _get(f"{_BASE_SUBS}/CIK{cik}.json")
    recent = data.get("filings", {}).get("recent", {})
    forms   = recent.get("form", [])
    filed   = recent.get("filingDate", [])
    periods = recent.get("reportDate", [])

    results = []
    for i, form in enumerate(forms):
        if form in form_types:
            period = periods[i] if i < len(periods) else ""
            results.append({
                "form":   form,
                "filed":  filed[i] if i < len(filed) else "",
                "period": period,
                "label":  _period_label(form, period),
            })

    results.sort(key=lambda x: x["period"], reverse=True)
    return results[:20]


def _period_label(form: str, period: str) -> str:
    """Turn '2024-09-28' + '10-K' into a readable label like 'FY2024 (Sep 28)'."""
    if not period:
        return form
    try:
        from datetime import date
        d = date.fromisoformat(period)
        if form == "10-K":
            return f"FY{d.year} (10-K)"
        else:
            month = d.strftime("%b %Y")
            return f"{month} (10-Q)"
    except ValueError:
        return f"{form} — {period}"


# ── Data extraction ───────────────────────────────────────────────────────────

def _pick(usgaap: dict, concepts: list[str], period_end: str,
          form: str, unit: str) -> float | None:
    """Return the first matching XBRL value for a concept/period/form combination."""
    for concept in concepts:
        entries = usgaap.get(concept, {}).get("units", {}).get(unit, [])
        # Exact match: period + form
        for e in entries:
            if e.get("end") == period_end and e.get("form") in (form, form + "/A"):
                if e.get("val") is not None:
                    return float(e["val"])
        # Fallback: match period only (handles amended filings, etc.)
        for e in entries:
            if e.get("end") == period_end:
                if e.get("val") is not None:
                    return float(e["val"])
    return None


def build_statements(
    cik: str,
    filings: list[dict],
) -> tuple[str, list[str], dict, dict, dict]:
    """
    Fetch XBRL facts for `cik` and build the three financial statements
    for the selected `filings` (most-recent-first order).

    Returns:
        company_name  — entity name from SEC
        period_labels — human-readable period labels (most recent first)
        balance_sheet, income_statement, cash_flow — integer-indexed dicts
    """
    facts_raw    = _get(f"{_BASE_FACTS}/CIK{cik}.json")
    company_name = facts_raw.get("entityName", "Unknown Company")
    usgaap       = facts_raw.get("facts", {}).get("us-gaap", {})

    period_labels = [f["label"] for f in filings]

    def extract(concept_map: dict[str, list[str]]) -> dict:
        stmt: dict = {}
        for line_item, concepts in concept_map.items():
            stmt[line_item] = {}
            if not concepts:
                continue
            if line_item in _EPS_ITEMS:
                unit = "USD/shares"
            elif line_item in _SHARE_ITEMS:
                unit = "shares"
            else:
                unit = "USD"

            for idx, filing in enumerate(filings):
                val = _pick(usgaap, concepts, filing["period"], filing["form"], unit)
                if val is not None:
                    if unit == "USD":
                        stmt[line_item][idx] = val / 1_000_000       # → $M
                    elif unit == "shares":
                        stmt[line_item][idx] = val / 1_000_000       # → M shares
                    else:
                        stmt[line_item][idx] = val                   # EPS: $/share
                else:
                    stmt[line_item][idx] = 0.0
        return stmt

    bs  = extract(BS_CONCEPTS)
    inc = extract(IS_CONCEPTS)
    cf  = extract(CF_CONCEPTS)

    # Compute FCF and normalise CapEx to positive
    for idx in range(len(filings)):
        ocf   = cf.get("Operating Cash Flow (OCF)", {}).get(idx, 0.0)
        capex = abs(cf.get("Capital Expenditures (CapEx)", {}).get(idx, 0.0))
        cf.setdefault("Free Cash Flow (FCF)", {})[idx] = ocf - capex
        if "Capital Expenditures (CapEx)" in cf:
            cf["Capital Expenditures (CapEx)"][idx] = capex

    return company_name, period_labels, bs, inc, cf
