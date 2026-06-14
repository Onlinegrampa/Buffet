"""In-memory company profile shared across FinSight modules within one session.

Statements are stored period-indexed: {line_item: {0: most_recent, 1: prior, ...}}.
_val() still accepts "current"/"prior" (indices 0/1) so every existing module keeps
working unchanged; new multi-period features use _series() across all periods.
"""
from __future__ import annotations

from utils.helpers import percent_change, safe_pct

Statement = dict


class CompanyProfile:
    def __init__(self, name: str, periods: list[str] | None = None) -> None:
        self.name = name
        self.periods = periods or ["Current", "Prior"]  # labels, most recent first
        self.balance_sheet: Statement = {}
        self.income_statement: Statement = {}
        self.cash_flow: Statement = {}

    @property
    def period_count(self) -> int:
        return len(self.periods)

    @staticmethod
    def _val(statement: Statement, item: str, period="current") -> float:
        idx = {"current": 0, "prior": 1}.get(period, period)
        return statement.get(item, {}).get(idx, 0.0)

    @staticmethod
    def _series(statement: Statement, item: str, count: int) -> list[float]:
        rec = statement.get(item, {})
        return [rec.get(i, 0.0) for i in range(count)]

    # ----- Module 2: Buffett -----
    def buffett_inputs(self) -> dict:
        bs, inc, cf, v = self.balance_sheet, self.income_statement, self.cash_flow, self._val
        return {
            "revenue": v(inc, "Revenue"),
            "gross_profit": v(inc, "Gross Profit"),
            "sga": v(inc, "Sales & Marketing (S&M)") + v(inc, "General & Administrative (G&A)"),
            "rnd": v(inc, "Research & Development (R&D)"),
            "depreciation": v(cf, "Depreciation & Amortization (D&A)"),
            "operating_income": v(inc, "Operating Income (EBIT)"),
            "interest_expense": v(inc, "Interest Expense"),
            "income_tax": v(inc, "Income Tax Expense"),
            "pretax_income": v(inc, "Earnings Before Taxes (EBT)"),
            "net_income": v(inc, "Net Income"),
            "eps_current": v(inc, "Diluted EPS", "current"),
            "eps_prior": v(inc, "Diluted EPS", "prior"),
            "total_cash": v(bs, "Cash & Marketable Securities"),
            "total_debt": v(bs, "Short-term Debt") + v(bs, "Long-term Debt"),
            "total_liabilities": v(bs, "Total Liabilities"),
            "equity": v(bs, "Total Shareholders' Equity"),
            "treasury_stock": abs(v(bs, "Treasury Stock (cumulative buybacks)")),
            "preferred_stock": abs(v(bs, "Preferred Stock")),
            "re_current": v(bs, "Retained Earnings", "current"),
            "re_prior": v(bs, "Retained Earnings", "prior"),
            "capex": abs(v(cf, "Capital Expenditures (CapEx)")),
        }

    # ----- Module 3: Rule of 40 -----
    def rule_of_40_inputs(self) -> dict:
        inc, cf, v = self.income_statement, self.cash_flow, self._val
        revenue = v(inc, "Revenue")
        return {
            "growth": percent_change(revenue, v(inc, "Revenue", "prior")),
            "margins": {
                "Free Cash Flow Margin": safe_pct(v(cf, "Free Cash Flow (FCF)"), revenue),
                "GAAP Operating Margin": safe_pct(v(inc, "Operating Income (EBIT)"), revenue),
                "Net Margin": safe_pct(v(inc, "Net Income"), revenue),
            },
        }

    # ----- Module 4: Business stage -----
    def stage_inputs(self) -> dict:
        inc, v = self.income_statement, self._val
        rev_c, rev_p = v(inc, "Revenue", "current"), v(inc, "Revenue", "prior")
        return {
            "revenue": rev_c,
            "revenue_growth": percent_change(rev_c, rev_p),
            "gross_profit_c": v(inc, "Gross Profit", "current"),
            "gross_profit_p": v(inc, "Gross Profit", "prior"),
            "operating_income": v(inc, "Operating Income (EBIT)"),
            "net_income": v(inc, "Net Income"),
            "shares_growth": percent_change(
                v(inc, "Shares Outstanding", "current"), v(inc, "Shares Outstanding", "prior")),
            "fcf": v(self.cash_flow, "Free Cash Flow (FCF)"),
        }

    # ----- Module 5: Survival -----
    def survival_inputs(self) -> dict:
        bs, inc, cf, v = self.balance_sheet, self.income_statement, self.cash_flow, self._val
        return {
            "cash": v(bs, "Cash & Marketable Securities"),
            "fcf": v(cf, "Free Cash Flow (FCF)"),
            "shares_growth": percent_change(
                v(inc, "Shares Outstanding", "current"), v(inc, "Shares Outstanding", "prior")),
            "cash_from_financing": v(cf, "Cash from Financing"),
        }

    # ----- Module 6: Cash conversion cycle -----
    def ccc_inputs(self) -> dict:
        bs, inc, v = self.balance_sheet, self.income_statement, self._val
        out = {}
        for period in ("current", "prior"):
            out[period] = {
                "revenue": v(inc, "Revenue", period),
                "cogs": v(inc, "Cost of Goods Sold (COGS)", period),
                "ar": v(bs, "Accounts Receivable", period),
                "inventory": v(bs, "Inventory", period),
                "ap": v(bs, "Accounts Payable", period),
            }
        return out

    # ----- Module 7: Operating leverage -----
    def leverage_inputs(self) -> dict:
        inc, v = self.income_statement, self._val
        revenue = v(inc, "Revenue")
        return {
            "revenue": revenue,
            "gross_margin": safe_pct(v(inc, "Gross Profit"), revenue),
            "operating_margin": safe_pct(v(inc, "Operating Income (EBIT)"), revenue),
            "operating_income": v(inc, "Operating Income (EBIT)"),
        }

    # ----- Module 8: Balance sheet health -----
    def balance_health_inputs(self) -> dict:
        bs, v = self.balance_sheet, self._val
        out = {}
        for period in ("current", "prior"):
            out[period] = {
                "cash": v(bs, "Cash & Marketable Securities", period),
                "ar": v(bs, "Accounts Receivable", period),
                "inventory": v(bs, "Inventory", period),
                "current_assets": v(bs, "Total Current Assets", period),
                "current_liabilities": v(bs, "Total Current Liabilities", period),
                "total_liabilities": v(bs, "Total Liabilities", period),
                "equity": v(bs, "Total Shareholders' Equity", period),
                "goodwill": v(bs, "Goodwill", period),
                "intangibles": v(bs, "Intangible Assets", period),
                "total_assets": v(bs, "Total Assets", period),
                "total_debt": v(bs, "Short-term Debt", period) + v(bs, "Long-term Debt", period),
            }
        return out

    # ----- Module 9: Income statement scan -----
    def income_scan_inputs(self) -> dict:
        inc, v = self.income_statement, self._val
        out = {}
        for period in ("current", "prior"):
            out[period] = {
                "revenue": v(inc, "Revenue", period),
                "gross_profit": v(inc, "Gross Profit", period),
                "operating_income": v(inc, "Operating Income (EBIT)", period),
                "net_income": v(inc, "Net Income", period),
                "sga": v(inc, "Sales & Marketing (S&M)", period) + v(inc, "General & Administrative (G&A)", period),
                "interest": v(inc, "Interest Expense", period),
                "shares": v(inc, "Shares Outstanding", period),
                "eps": v(inc, "Diluted EPS", period),
            }
        return out

    # ----- Module 10: Multi-year consistency -----
    def consistency_series(self) -> dict:
        inc, bs, n = self.income_statement, self.balance_sheet, self.period_count
        rev = self._series(inc, "Revenue", n)
        gp = self._series(inc, "Gross Profit", n)
        oi = self._series(inc, "Operating Income (EBIT)", n)
        ni = self._series(inc, "Net Income", n)

        def margin(num):
            return [safe_pct(num[i], rev[i]) for i in range(n)]

        return {
            "labels": self.periods,
            "revenue": rev,
            "gross_margin": margin(gp),
            "operating_margin": margin(oi),
            "net_margin": margin(ni),
            "eps": self._series(inc, "Diluted EPS", n),
            "retained_earnings": self._series(bs, "Retained Earnings", n),
        }


# --- session singleton -------------------------------------------------------
_session_profile: CompanyProfile | None = None


def get_profile() -> CompanyProfile | None:
    return _session_profile


def set_profile(profile: CompanyProfile) -> None:
    global _session_profile
    _session_profile = profile
