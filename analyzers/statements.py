"""Module 1: Core 3-Statement Analyzer (2-5 comparative periods).

Captures each line item for N periods (most-recent first), shows the period
comparison with $ and % change vs the immediately prior period, validates
Assets = Liabilities + Equity and FCF = OCF - CapEx for every period, and saves
all periods to the shared session profile (feeds Modules 2-10).
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import (
    absolute_change,
    console,
    fmt_money,
    fmt_pct,
    percent_change,
    prompt_float,
)
from utils.profile import CompanyProfile, set_profile

BALANCE_SHEET = [
    "Cash & Marketable Securities", "Accounts Receivable", "Inventory",
    "Total Current Assets", "Property, Plant & Equipment (PP&E)", "Goodwill",
    "Intangible Assets", "Total Assets", "Accounts Payable", "Accrued Expenses",
    "Short-term Debt", "Operating Lease Liabilities", "Total Current Liabilities",
    "Long-term Debt", "Total Liabilities", "Preferred Stock", "Retained Earnings",
    "Treasury Stock (cumulative buybacks)", "Total Shareholders' Equity",
]
INCOME_STATEMENT = [
    "Revenue", "Cost of Goods Sold (COGS)", "Gross Profit",
    "Research & Development (R&D)", "Sales & Marketing (S&M)",
    "General & Administrative (G&A)", "Total Operating Expenses",
    "Operating Income (EBIT)", "Interest Expense", "Earnings Before Taxes (EBT)",
    "Income Tax Expense", "Net Income", "Shares Outstanding", "Diluted EPS",
]
CASH_FLOW = [
    "Net Income", "Depreciation & Amortization (D&A)",
    "Stock-Based Compensation (SBC)", "Changes in Working Capital",
    "Operating Cash Flow (OCF)", "Capital Expenditures (CapEx)",
    "Free Cash Flow (FCF)", "Cash from Investing", "Cash from Financing",
    "Net Change in Cash",
]


def _period_labels(n: int) -> list[str]:
    return ["Most recent"] + [f"{i} yr prior" for i in range(1, n)]


def _capture(name: str, items: list[str], n: int, labels: list[str]) -> dict:
    console.rule(f"[bold cyan]{name}[/]")
    console.print("[dim]Enter each line most-recent-first. Press Enter to leave a value at 0.[/dim]\n")
    data: dict = {}
    for item in items:
        console.print(f"[bold]{item}[/]")
        data[item] = {i: prompt_float(labels[i], 0.0) for i in range(n)}
    return data


def _comparison_table(title: str, data: dict, labels: list[str]) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAVY, title_style="bold cyan")
    table.add_column("Line Item")
    for lbl in labels:
        table.add_column(lbl, justify="right")
    table.add_column("$ Chg", justify="right")
    table.add_column("% Chg", justify="right")
    n = len(labels)
    for item, rec in data.items():
        vals = [rec.get(i, 0.0) for i in range(n)]
        cur, pri = vals[0], vals[1]
        chg, pct = absolute_change(cur, pri), percent_change(cur, pri)
        style = "green" if chg >= 0 else "red"
        table.add_row(
            item, *[fmt_money(x) for x in vals],
            f"[{style}]{fmt_money(chg)}[/]", f"[{style}]{fmt_pct(pct)}[/]",
        )
    return table


def _validate_balance_sheet(bs: dict, labels: list[str]) -> None:
    console.rule("[bold]Integrity Check  -  Assets = Liabilities + Equity[/]")
    for i, lbl in enumerate(labels):
        assets = bs["Total Assets"].get(i, 0.0)
        rhs = bs["Total Liabilities"].get(i, 0.0) + bs["Total Shareholders' Equity"].get(i, 0.0)
        diff = assets - rhs
        tol = max(1.0, abs(assets) * 0.005)
        if abs(diff) <= tol:
            console.print(f"  [green]OK {lbl}[/]: Assets {fmt_money(assets)} = L+E {fmt_money(rhs)}")
        else:
            console.print(
                f"  [bold red]!! {lbl} OUT OF BALANCE[/]: "
                f"Assets {fmt_money(assets)} vs L+E {fmt_money(rhs)} (off by {fmt_money(diff)})"
            )


def _validate_fcf(cf: dict, labels: list[str]) -> None:
    console.rule("[bold]Integrity Check  -  FCF = OCF - CapEx[/]")
    for i, lbl in enumerate(labels):
        ocf = cf["Operating Cash Flow (OCF)"].get(i, 0.0)
        capex = cf["Capital Expenditures (CapEx)"].get(i, 0.0)
        reported = cf["Free Cash Flow (FCF)"].get(i, 0.0)
        computed = ocf - capex
        if abs(computed - reported) <= max(1.0, abs(computed) * 0.005):
            console.print(
                f"  [green]OK {lbl}[/]: OCF {fmt_money(ocf)} - CapEx {fmt_money(capex)} = {fmt_money(computed)}"
            )
        else:
            console.print(
                f"  [yellow]!! {lbl} FCF mismatch[/]: computed {fmt_money(computed)} "
                f"vs entered {fmt_money(reported)} (enter CapEx as a positive number)"
            )


def compute(profile: CompanyProfile) -> dict:
    """Return structured analysis data for web rendering (supports N periods)."""
    n = profile.period_count

    def make_rows(stmt: dict) -> list[dict]:
        rows = []
        for item in stmt:
            vals = [stmt.get(item, {}).get(i, 0.0) for i in range(n)]
            cur, pri = vals[0], (vals[1] if n > 1 else 0.0)
            chg = absolute_change(cur, pri)
            pct = percent_change(cur, pri)
            rows.append({"item": item, "vals": vals,
                         "current": cur, "prior": pri, "change": chg, "pct": pct})
        return rows

    bs, cf = profile.balance_sheet, profile.cash_flow

    bs_checks = []
    for i, lbl in enumerate(profile.periods[:2]):
        assets = bs.get("Total Assets", {}).get(i, 0.0)
        liab   = bs.get("Total Liabilities", {}).get(i, 0.0)
        equity = bs.get("Total Shareholders' Equity", {}).get(i, 0.0)
        rhs    = liab + equity
        diff   = assets - rhs
        tol    = max(1.0, abs(assets) * 0.005)
        bs_checks.append({"period": lbl, "ok": abs(diff) <= tol,
                          "assets": assets, "rhs": rhs, "diff": diff})

    fcf_checks = []
    for i, lbl in enumerate(profile.periods[:2]):
        ocf      = cf.get("Operating Cash Flow (OCF)", {}).get(i, 0.0)
        capex    = cf.get("Capital Expenditures (CapEx)", {}).get(i, 0.0)
        reported = cf.get("Free Cash Flow (FCF)", {}).get(i, 0.0)
        computed = ocf - capex
        tol      = max(1.0, abs(computed) * 0.005)
        fcf_checks.append({"period": lbl, "ok": abs(computed - reported) <= tol,
                           "ocf": ocf, "capex": capex, "computed": computed, "reported": reported})

    return {
        "balance_sheet": make_rows(profile.balance_sheet),
        "income_statement": make_rows(profile.income_statement),
        "cash_flow": make_rows(profile.cash_flow),
        "bs_checks": bs_checks,
        "fcf_checks": fcf_checks,
    }


def run() -> None:
    console.rule("[bold magenta]Module 1 — Core 3-Statement Analyzer[/]")
    name = console.input("  Company name: ").strip() or "Target Company"
    n = int(prompt_float("How many periods to compare? (2-5)", 2))
    n = max(2, min(5, n))
    labels = _period_labels(n)

    bs = _capture("Balance Sheet", BALANCE_SHEET, n, labels)
    inc = _capture("Income Statement", INCOME_STATEMENT, n, labels)
    cf = _capture("Cash Flow Statement", CASH_FLOW, n, labels)

    console.print()
    console.print(_comparison_table("Balance Sheet — Period Comparison", bs, labels))
    console.print(_comparison_table("Income Statement — Period Comparison", inc, labels))
    console.print(_comparison_table("Cash Flow Statement — Period Comparison", cf, labels))

    console.print()
    _validate_balance_sheet(bs, labels)
    _validate_fcf(cf, labels)

    profile = CompanyProfile(name, labels)
    profile.balance_sheet, profile.income_statement, profile.cash_flow = bs, inc, cf
    set_profile(profile)
    extra = ("  With 3+ periods, the Consistency Tracker (Module 10) is now meaningful."
             if n >= 3 else "  Modules 2-10 can now reuse these figures.")
    console.print(f"\n  [green]Saved '{name}' ({n} periods) to this session.[/]{extra}")
