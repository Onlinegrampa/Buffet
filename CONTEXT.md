# FinSight — Full Project Context

> Upload this file at the start of a new Claude session to resume exactly where we left off.
> Tell Claude: "Read this CONTEXT.md file and continue building FinSight from where we left off."

---

## What This Project Is

**FinSight** is a Python/Flask financial analysis web app. A user imports a company's financial statements (manually or automatically from SEC EDGAR / Yahoo Finance), and the app runs 10 analysis modules and produces a formatted results page and downloadable HTML report.

**GitHub repo:** `https://github.com/Onlinegrampa/Buffet.git`  
**Branch:** `main`  
**Local path:** `C:\Users\Dell User\finsight-cli`  
**Run command:** `.venv\Scripts\python app.py` → `http://localhost:5000`  
**Python version:** 3.13  
**OS:** Windows 11

---

## Tech Stack

- **Backend:** Python 3.13, Flask 3.x
- **Frontend:** Bootstrap 5.3, Jinja2 templates, vanilla JavaScript
- **Data sources:** SEC EDGAR XBRL API (free, no key), Yahoo Finance via `yfinance` (free, no key)
- **Storage:** `saved_reports/` folder — each report saved as `{uuid}.html` + `{uuid}.json`
- **Key libraries:** `flask`, `requests`, `yfinance`, `rich` (for legacy CLI)

---

## Project File Structure

```
finsight-cli/
├── app.py                        # Main Flask app — all routes
├── main.py                       # Legacy CLI entry point (not used in web app)
├── requirements.txt              # flask, requests, yfinance, rich, anthropic
├── .gitignore                    # excludes .venv/, __pycache__/, saved_reports/
│
├── analyzers/
│   ├── statements.py             # Module 1 — 3-Statement Analyzer + BALANCE_SHEET/INCOME_STATEMENT/CASH_FLOW lists
│   ├── buffett.py                # Module 2 — Buffett Moat Scanner (14 rules)
│   ├── saas.py                   # Module 3 — Rule of 40 (FCF margin, op margin, net margin)
│   ├── stage.py                  # Module 4 — Business Stage Classifier (S1-S5)
│   ├── survival.py               # Module 5 — Survival / Cash Runway Analysis
│   ├── ccc.py                    # Module 6 — Cash Conversion Cycle (DIO/DSO/DPO)
│   ├── leverage.py               # Module 7 — Operating Leverage (margin spread)
│   ├── balance_health.py         # Module 8 — Balance Sheet Health (ratios + flags)
│   ├── income_scan.py            # Module 9 — Income Statement Scanner (flags + margins)
│   └── consistency.py            # Module 10 — Multi-Year Consistency Tracker
│
├── utils/
│   ├── profile.py                # CompanyProfile class — shared data model for all modules
│   ├── edgar.py                  # SEC EDGAR API wrapper (search, filings, XBRL fetch)
│   ├── yahoo.py                  # Yahoo Finance wrapper via yfinance
│   └── helpers.py                # fmt_money, percent_change, safe_pct, etc.
│
├── templates/
│   ├── index.html                # Manual data entry form (8-period, unit toggle)
│   ├── edgar.html                # Import hub — two tabs: SEC EDGAR + Yahoo Finance
│   ├── results.html              # Analysis results page (10 scrollable tabs)
│   ├── report.html               # Self-contained downloadable HTML report
│   └── reports_list.html         # Saved reports dashboard (sortable table)
│
└── saved_reports/                # Auto-created, git-ignored
    ├── {uuid}.html               # Full rendered report
    └── {uuid}.json               # Metadata + 18 key metrics for dashboard
```

---

## Data Model

### CompanyProfile (`utils/profile.py`)

The central data object passed to every analyzer.

```python
profile = CompanyProfile(name="Apple Inc.", periods=["FY2024", "FY2023", "FY2022"])
profile.balance_sheet    = { "Cash & Marketable Securities": {0: 67150.0, 1: 61555.0, ...}, ... }
profile.income_statement = { "Revenue": {0: 391035.0, 1: 383285.0, ...}, ... }
profile.cash_flow        = { "Operating Cash Flow (OCF)": {0: 118254.0, ...}, ... }
```

- **Index 0 = most recent period**, 1 = one period prior, etc.
- All values stored in **$millions internally** regardless of input unit
- `_val(stmt, item, "current")` → index 0; `_val(stmt, item, "prior")` → index 1
- `_series(stmt, item, count)` → list of N values newest-first

### Statement Line Items

**Balance Sheet (19 items):**
```
Cash & Marketable Securities, Accounts Receivable, Inventory,
Total Current Assets, Property, Plant & Equipment (PP&E), Goodwill,
Intangible Assets, Total Assets, Accounts Payable, Accrued Expenses,
Short-term Debt, Operating Lease Liabilities, Total Current Liabilities,
Long-term Debt, Total Liabilities, Preferred Stock, Retained Earnings,
Treasury Stock (cumulative buybacks), Total Shareholders' Equity
```

**Income Statement (14 items):**
```
Revenue, Cost of Goods Sold (COGS), Gross Profit,
Research & Development (R&D), Sales & Marketing (S&M),
General & Administrative (G&A), Total Operating Expenses,
Operating Income (EBIT), Interest Expense, Earnings Before Taxes (EBT),
Income Tax Expense, Net Income, Shares Outstanding, Diluted EPS
```

**Cash Flow (10 items):**
```
Net Income, Depreciation & Amortization (D&A),
Stock-Based Compensation (SBC), Changes in Working Capital,
Operating Cash Flow (OCF), Capital Expenditures (CapEx),
Free Cash Flow (FCF), Cash from Investing, Cash from Financing,
Net Change in Cash
```

---

## The 10 Analysis Modules

Each module has a `compute(profile) -> dict` function.

| # | Module | File | Key output |
|---|--------|------|-----------|
| 1 | 3-Statement Analyzer | `analyzers/statements.py` | `rows` with vals list, bs_checks, fcf_checks |
| 2 | Buffett Moat Scanner | `analyzers/buffett.py` | `passes` (out of 14), `verdict_level` (good/warn/poor), per-rule results |
| 3 | Rule of 40 | `analyzers/saas.py` | `score`, `passes` bool, per-margin breakdown |
| 4 | Stage Classifier | `analyzers/stage.py` | `stage` (1-5), `label`, `recommended`, `signals` |
| 5 | Survival Analysis | `analyzers/survival.py` | `runway`, `positive_fcf`, `verdict_label`, `verdict_cls` |
| 6 | Cash Conversion Cycle | `analyzers/ccc.py` | `rows` (DIO/DSO/DPO/CCC with cur/prior), `interp`, `trend` |
| 7 | Operating Leverage | `analyzers/leverage.py` | `rows` (margin rows), `inc_gm`, `inc_om`, `signal` |
| 8 | Balance Sheet Health | `analyzers/balance_health.py` | `ratios` (with sig_cls/sig_txt), `flags` list |
| 9 | Income Scanner | `analyzers/income_scan.py` | `margins`, `growth`, `flags`, `flags_raised` (0-4) |
| 10 | Consistency Tracker | `analyzers/consistency.py` | `labels`, `rows` (with passed/total/verdict_cls), `revenue_trend`, `re_trend` |

### How `_run_analysis()` works (app.py)

```python
def _run_analysis(request_form) -> dict:
    # 1. Parse n_periods (2-8), period labels, unit
    # 2. Parse form fields: {prefix}_{item_idx}_{period_idx} → float * unit_factor
    # 3. Build CompanyProfile, assign .balance_sheet / .income_statement / .cash_flow
    # 4. Run all 10 compute() functions
    # 5. Return dict with all results + metadata
```

The same dict is also built in `edgar_analyze()` and `yahoo_analyze()` — those routes
skip the form parsing and instead populate the profile directly from API data.

---

## Flask Routes

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/` | Manual entry form (index.html) |
| POST | `/analyze` | Parse form, run all 10 modules, save report, render results |
| GET | `/download/<report_id>` | Serve saved HTML report as file download |
| GET | `/reports` | Saved reports dashboard (reports_list.html) |
| POST | `/reports/<id>/delete` | Delete report from disk |
| GET | `/edgar` | Import hub page (edgar.html) |
| GET | `/edgar/search?q=` | AJAX: search SEC companies, returns JSON |
| GET | `/edgar/filings?cik=&form=` | AJAX: list 10-K/10-Q filings for a CIK |
| POST | `/edgar/analyze` | Fetch XBRL data, run all 10 modules, save + render |
| GET | `/yahoo/search?q=` | AJAX: search Yahoo Finance, returns JSON |
| POST | `/yahoo/analyze` | Fetch yfinance data, run all 10 modules, save + render |

---

## SEC EDGAR Integration (`utils/edgar.py`)

- **Company search:** Downloads `https://www.sec.gov/files/company_tickers.json` once (cached in memory via `@lru_cache`), searches by ticker (exact) then company name (substring)
- **Filings:** `https://data.sec.gov/submissions/CIK{cik}.json` — returns recent 10-K and 10-Q filings with period dates
- **XBRL data:** `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` — all reported facts
- **Mapping:** `BS_CONCEPTS`, `IS_CONCEPTS`, `CF_CONCEPTS` dicts map our 43 line items to priority-ordered XBRL concept names
- **Conversion:** Raw USD ÷ 1,000,000 → $M; shares ÷ 1,000,000 → M shares; EPS kept as-is
- **Rate limit:** 0.11s sleep between requests (SEC allows 10/sec)
- **User-Agent header required:** `"FinSight financial-analysis-tool attschris1995@gmail.com"`

### EDGAR UI flow (edgar.html — SEC EDGAR tab)
1. Search box → AJAX `/edgar/search` → click company to select
2. Filings list loads → filter by 10-K/10-Q → check up to 8 periods (auto-selects 4 most recent 10-Ks)
3. "Fetch & Analyze" → POST `/edgar/analyze` with `cik` + `selected_filings` (JSON array)

---

## Yahoo Finance Integration (`utils/yahoo.py`)

- **Search:** `https://query1.finance.yahoo.com/v1/finance/search?q=...` — returns global equities
- **Data:** `yfinance.Ticker(sym).income_stmt / .balance_sheet / .cash_flow` (annual) or `.quarterly_*` variants
- **Mapping:** `BS_MAP`, `IS_MAP`, `CF_MAP` dicts map our line items to yfinance DataFrame index names
- **Coverage:** All global markets — append exchange suffix for non-US: `.L` London, `.PA` Paris, `.T` Tokyo, `.HK` Hong Kong, `.AS` Amsterdam, `.KS` Korea
- **Periods:** Annual up to 4 years; Quarterly up to 4 quarters
- **Conversion:** Raw USD ÷ 1,000,000 → $M; CapEx normalised to positive; FCF = OCF - CapEx if not provided

### Yahoo Finance UI flow (edgar.html — Yahoo Finance tab)
1. Search box → AJAX `/yahoo/search` → click company
2. Choose Annual or Quarterly, choose 1–4 periods
3. "Fetch & Analyze" → POST `/yahoo/analyze` with `ticker`, `period_type`, `n_periods`

---

## Report Persistence

```python
REPORTS_DIR = Path(__file__).parent / "saved_reports"

# On every /analyze, /edgar/analyze, /yahoo/analyze:
_save_report(report_id, data, html)
    → saved_reports/{report_id}.json   # metadata + 18 metrics
    → saved_reports/{report_id}.html   # full rendered report

# Dashboard (/reports):
_load_all_meta()  # reads all .json files, sorts newest-first

# Download (/download/<id>):
# reads .html from disk; falls back to in-memory _report_store
```

### `_extract_metrics(data)` — 18 dashboard metrics
```python
{
    "buffett_passes", "buffett_level",
    "revenue_growth", "r40_fcf_score", "r40_fcf_passes", "r40_op_score",
    "stage_num", "stage_label",
    "runway_label", "runway_years", "positive_fcf",
    "gross_margin", "operating_margin", "net_margin",
    "ccc_days", "fixed_cost_layer", "current_ratio", "flags_raised"
}
```

---

## Frontend — Key Templates

### `index.html` — Manual Entry Form
- Period count toggle: 2–8 buttons, `setPeriods(n)` JS shows/hides columns
- Unit toggle: Hundreds / Thousands / Millions — multiplied by `unit_factor` before storing
- Form field naming: `{prefix}_{item_idx}_{period_idx}` e.g. `bs_0_0`, `inc_3_1`
- Period label inputs: `period_0` ... `period_7`
- "Import from SEC EDGAR" button in topbar → `/edgar`

### `edgar.html` — Import Hub (two tabs)
- Tab switching: `switchTab('edgar')` / `switchTab('yahoo')`
- SEC EDGAR: 3-step flow (search → filing checkboxes → analyze)
- Yahoo Finance: 3-step flow (search → Annual/Quarterly + N picker → analyze)
- Loading overlay covers screen during API calls
- Filing items are `<label>` elements wrapping checkboxes (avoids double-toggle bug)
- `active_tab` Jinja variable controls which tab opens on load (used for error redirects)

### `results.html` — 10-Tab Results Page
Tabs: Buffett | Rule of 40 | Statements | Stage | Survival | Cash Cycle | Leverage | Balance Sheet | Income Scan | Consistency

### `reports_list.html` — Saved Reports Dashboard
- Sortable table: click column header → asc, click again → desc, blanks always bottom
- Color-coded chips: green/yellow/red thresholds per metric
- Filter search box with live row count badge
- Download + Delete actions per row

### `report.html` — Downloadable Report
- Self-contained HTML with inline CSS (no CDN dependencies)
- All 10 sections included in order

---

## Jinja Filters (app.py)

```python
{{ value | money }}   # → "$1,234.5M" or "-$45.2M" or "n/a"
{{ value | pct }}     # → "+12.3%" or "-5.0%"
```

---

## Key Conventions

- **All money values are in $millions internally.** Input units (hundreds/thousands/millions) are multiplied by `unit_factor` at parse time. Analyzers always see $M.
- **CapEx is always stored as a positive number** in both the manual form and the API importers. FCF = OCF - CapEx.
- **Treasury Stock is stored as a positive number.**
- **Windows encoding:** All template text uses ASCII equivalents — `>=` not `≥`, `OK` not `✓`, no special Unicode chars in Python files (cp1252 compatibility).
- **No test suite** — functionality verified by running the app and testing in browser.
- **Git push:** `git push origin main` — repo is `https://github.com/Onlinegrampa/Buffet.git`

---

## How to Run Locally

```bash
cd "C:\Users\Dell User\finsight-cli"
.venv\Scripts\python app.py
# Visit http://localhost:5000
```

Or from PowerShell:
```powershell
cd "C:\Users\Dell User\finsight-cli"
.venv\Scripts\python app.py
```

### Install dependencies (fresh clone):
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

---

## Current State (as of last session)

**All 10 modules are fully implemented** in both the web app and downloadable report.

**Data import sources implemented:**
1. Manual entry form (index.html) — 2–8 periods, unit toggle
2. SEC EDGAR (US public companies, 10-K + 10-Q) — free, no API key
3. Yahoo Finance (global equities, annual + quarterly) — free, no API key

**Saved reports dashboard** — sortable by 13 metrics, filter search, download/delete per row.

### What could be added next (ideas, not started):
- More data sources: Financial Modeling Prep (FMP), Alpha Vantage, Companies House (UK)
- Charts / visualizations (Chart.js) on the results page
- Side-by-side company comparison
- Export to PDF (using WeasyPrint or similar)
- User accounts / login to separate saved reports per user
- Automated screening: scan a list of tickers and rank by score
- Valuation modules: DCF, EV/EBITDA, P/E vs peers

---

## Git Commit History

```
fbcfd54  Add Yahoo Finance as second import source alongside SEC EDGAR
b224fc0  Add SEC EDGAR integration — pull live 10-K/10-Q data automatically
8017c9d  Dashboard table for saved reports with sortable columns and color-coded metrics
3dae124  Save reports to disk with list and delete pages
348d91b  Include all 10 modules in downloadable report
3fef1b1  Add all 10 modules to web app
0acdb9a  Add input unit toggle: hundreds, thousands, millions
bb68eb7  Add downloadable HTML report
c28f99a  Initial commit — FinSight CLI v3 with 8-period web app
```

---

*Last updated: June 2026*
