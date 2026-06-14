"""Module 2: Buffett Moat Scanner — the 14 Rules of Thumb.

Eight income-statement rules, five balance-sheet rules, and one cash-flow rule.
Inputs are loaded from the shared session profile when available (entered once in
Module 1), otherwise prompted manually. Each rule returns PASS / FAIL / WARN; the
Moat Durability Score counts PASSes out of 14. ROE is a labeled bonus metric.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import (
    console,
    fmt_money,
    fmt_pct,
    percent_change,
    prompt_float,
    safe_pct,
    status_label,
)
from utils.profile import get_profile


def _eval_max(value: float | None, threshold: float, warn_band: float) -> str:
    """Rule passes when value <= threshold."""
    if value is None:
        return "WARN"
    if value <= threshold:
        return "PASS"
    if value <= threshold + warn_band:
        return "WARN"
    return "FAIL"


def _eval_min(value: float | None, threshold: float, warn_band: float) -> str:
    """Rule passes when value >= threshold."""
    if value is None:
        return "WARN"
    if value >= threshold:
        return "PASS"
    if value >= threshold - warn_band:
        return "WARN"
    return "FAIL"


def _prompt_inputs() -> tuple[str, dict]:
    name = console.input("  Company name: ").strip() or "Target Company"
    console.rule("[cyan]Income Statement inputs[/]")
    inp = {
        "revenue": prompt_float("Revenue"),
        "gross_profit": prompt_float("Gross Profit"),
        "sga": prompt_float("SG&A expense"),
        "rnd": prompt_float("R&D expense"),
        "depreciation": prompt_float("Depreciation & Amortization"),
        "operating_income": prompt_float("Operating Income (EBIT)"),
        "interest_expense": prompt_float("Interest Expense"),
        "income_tax": prompt_float("Income Tax Expense"),
        "pretax_income": prompt_float("Pre-tax Income (EBT)"),
        "net_income": prompt_float("Net Income"),
        "eps_current": prompt_float("Diluted EPS (current year)"),
        "eps_prior": prompt_float("Diluted EPS (prior year)"),
    }
    console.rule("[cyan]Balance Sheet inputs[/]")
    inp.update({
        "total_cash": prompt_float("Total Cash & Investments"),
        "total_debt": prompt_float("Total Debt (short + long term)"),
        "total_liabilities": prompt_float("Total Liabilities"),
        "equity": prompt_float("Total Shareholders' Equity"),
        "treasury_stock": prompt_float("Treasury Stock (cumulative buybacks, positive)"),
        "preferred_stock": prompt_float("Preferred Stock"),
        "re_current": prompt_float("Retained Earnings (current year)"),
        "re_prior": prompt_float("Retained Earnings (prior year)"),
    })
    console.rule("[cyan]Cash Flow input[/]")
    inp["capex"] = prompt_float("Capital Expenditures (positive)")
    return name, inp


def _gather_inputs() -> tuple[str, dict]:
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            console.print(
                f"  [green]Loaded {profile.name} from the 3-Statement Analyzer.[/]"
            )
            return profile.name, profile.buffett_inputs()
    return _prompt_inputs()


def _build_rules(inp: dict) -> list[tuple[str, str, str, str, str]]:
    """Build the 14-rule list as (name, formula, value, threshold, status) tuples."""
    rules: list[tuple[str, str, str, str, str]] = []

    gm = safe_pct(inp["gross_profit"], inp["revenue"])
    rules.append(("1. Gross Margin", "Gross Profit / Revenue",
                  f"{gm:.1f}%" if gm is not None else "n/a", "> 40%",
                  _eval_min(gm, 40, 5)))

    sgam = safe_pct(inp["sga"], inp["gross_profit"])
    rules.append(("2. SG&A Margin", "SG&A / Gross Profit",
                  f"{sgam:.1f}%" if sgam is not None else "n/a", "< 30%",
                  _eval_max(sgam, 30, 10)))

    if inp["rnd"] == 0:
        r3, rnd_disp = "PASS", "0.0% (none)"
    else:
        rndm = safe_pct(inp["rnd"], inp["gross_profit"])
        r3 = _eval_max(rndm, 30, 10)
        rnd_disp = f"{rndm:.1f}%" if rndm is not None else "n/a"
    rules.append(("3. R&D Margin", "R&D / Gross Profit", rnd_disp, "< 30%", r3))

    depm = safe_pct(inp["depreciation"], inp["gross_profit"])
    rules.append(("4. Depreciation Margin", "D&A / Gross Profit",
                  f"{depm:.1f}%" if depm is not None else "n/a", "< 10%",
                  _eval_max(depm, 10, 5)))

    intm = safe_pct(inp["interest_expense"], inp["operating_income"])
    rules.append(("5. Interest Expense Margin", "Interest / Operating Income",
                  f"{intm:.1f}%" if intm is not None else "n/a", "< 15%",
                  _eval_max(intm, 15, 10)))

    taxm = safe_pct(inp["income_tax"], inp["pretax_income"])
    if taxm is None:
        r6 = "WARN"
    elif abs(taxm - 21) <= 4:
        r6 = "PASS"
    else:
        r6 = "WARN"
    rules.append(("6. Income Tax Margin", "Income Tax / Pre-tax Income",
                  f"{taxm:.1f}%" if taxm is not None else "n/a", "~ 21%", r6))

    nm = safe_pct(inp["net_income"], inp["revenue"])
    rules.append(("7. Net Profit Margin", "Net Income / Revenue",
                  f"{nm:.1f}%" if nm is not None else "n/a", "> 20%",
                  _eval_min(nm, 20, 5)))

    eps_c, eps_p = inp["eps_current"], inp["eps_prior"]
    if eps_c > 0 and eps_c > eps_p:
        r8 = "PASS"
    elif eps_c > 0:
        r8 = "WARN"
    else:
        r8 = "FAIL"
    eps_growth = percent_change(eps_c, eps_p)
    rules.append(("8. EPS Positive & Growing", "Diluted EPS YoY",
                  f"{eps_c:.2f} vs {eps_p:.2f} ({fmt_pct(eps_growth)})",
                  "positive & rising", r8))

    r9 = "PASS" if inp["total_cash"] > inp["total_debt"] else "FAIL"
    rules.append(("9. Cash vs Debt", "Cash & Investments > Total Debt",
                  f"{fmt_money(inp['total_cash'])} vs {fmt_money(inp['total_debt'])}",
                  "cash > debt", r9))

    adj_equity = inp["equity"] + inp["treasury_stock"]
    if adj_equity <= 0:
        de_disp, de_status = "n/a (equity <= 0)", "WARN"
    else:
        de = inp["total_liabilities"] / adj_equity
        de_disp, de_status = f"{de:.2f}", _eval_max(de, 0.80, 0.40)
    rules.append(("10. Adjusted Debt-to-Equity",
                  "Total Liabilities / (Equity + Treasury Stock)",
                  de_disp, "< 0.80", de_status))

    r11 = "PASS" if inp["preferred_stock"] == 0 else "WARN"
    rules.append(("11. Preferred Stock", "Preferred Stock balance",
                  fmt_money(inp["preferred_stock"]), "none", r11))

    re_c, re_p = inp["re_current"], inp["re_prior"]
    if re_c > re_p:
        r12 = "PASS"
    elif inp["treasury_stock"] > 0:
        r12 = "WARN"
    else:
        r12 = "FAIL"
    re_growth = percent_change(re_c, re_p)
    rules.append(("12. Retained Earnings Growth", "Retained Earnings YoY",
                  f"{fmt_money(re_c)} vs {fmt_money(re_p)} ({fmt_pct(re_growth)})",
                  "consistently rising", r12))

    r13 = "PASS" if inp["treasury_stock"] > 0 else "WARN"
    rules.append(("13. Treasury Stock (Buybacks)", "Cumulative buybacks present",
                  fmt_money(inp["treasury_stock"]), "> 0", r13))

    capexm = safe_pct(inp["capex"], inp["net_income"])
    rules.append(("14. CapEx Margin", "CapEx / Net Income",
                  f"{capexm:.1f}%" if capexm is not None else "n/a", "< 25%",
                  _eval_max(capexm, 25, 15)))

    return rules


def compute(name: str, inp: dict) -> dict:
    """Return structured Buffett analysis for web rendering."""
    rules = _build_rules(inp)
    passes = sum(1 for _, _, _, _, s in rules if s == "PASS")
    warns  = sum(1 for _, _, _, _, s in rules if s == "WARN")
    fails  = sum(1 for _, _, _, _, s in rules if s == "FAIL")

    if passes >= 11:
        verdict, verdict_level = "WIDE MOAT — strong, consistent economics", "good"
    elif passes >= 7:
        verdict, verdict_level = "NARROW / MIXED — investigate WARN and FAIL items", "warn"
    else:
        verdict, verdict_level = "NO CLEAR MOAT — fails most of Buffett's tests", "bad"

    return {
        "name": name,
        "rules": [{"name": r[0], "formula": r[1], "value": r[2],
                   "threshold": r[3], "status": r[4]} for r in rules],
        "passes": passes, "warns": warns, "fails": fails,
        "score_pct": passes / 14 * 100,
        "verdict": verdict, "verdict_level": verdict_level,
        "roe": safe_pct(inp["net_income"], inp["equity"]),
    }


def _evaluate(name: str, inp: dict) -> None:
    rules = _build_rules(inp)

    # --- Render ---
    table = Table(title=f"Buffett Moat Scanner — {name}",
                  box=box.SIMPLE_HEAVY, title_style="bold magenta")
    table.add_column("Rule")
    table.add_column("Formula", style="dim")
    table.add_column("Value", justify="right")
    table.add_column("Threshold", justify="center")
    table.add_column("Status", justify="center")

    passes = warns = fails = 0
    for rname, formula, value, threshold, status in rules:
        passes += status == "PASS"
        warns += status == "WARN"
        fails += status == "FAIL"
        table.add_row(rname, formula, value, threshold, status_label(status))

    console.print()
    console.print(table)

    console.rule("[bold]Moat Durability Score[/]")
    console.print(
        f"  [bold]{name}[/]: [bold green]{passes} / 14[/] rules passed "
        f"({passes / 14 * 100:.0f}%)  —  {warns} warn, {fails} fail"
    )
    if passes >= 11:
        verdict = "[bold green]WIDE MOAT — strong, consistent economics[/]"
    elif passes >= 7:
        verdict = "[bold yellow]NARROW / MIXED — investigate WARN and FAIL items[/]"
    else:
        verdict = "[bold red]NO CLEAR MOAT — fails most of Buffett's tests[/]"
    console.print(f"  Verdict: {verdict}")

    roe = safe_pct(inp["net_income"], inp["equity"])
    if roe is not None:
        console.print(
            f"\n  [dim]Bonus — Return on Equity (Net Income / Equity): "
            f"{roe:.1f}%  ·  not one of the original 14, shown for context.[/]"
        )


def run() -> None:
    console.rule("[bold magenta]Module 2 — Buffett Moat Scanner (14 Rules of Thumb)[/]")
    name, inp = _gather_inputs()
    _evaluate(name, inp)
