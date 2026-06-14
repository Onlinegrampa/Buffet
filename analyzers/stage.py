"""Module 4: Business Stage Classifier with auto-router.

Classifies the six-stage growth phase, then offers to run the stage-appropriate
module(s) immediately. Classification is a heuristic — layer your own judgment.
"""
from __future__ import annotations

from utils.helpers import console, fmt_pct, percent_change, prompt_float
from utils.profile import get_profile

# stage -> (label, description, [module keys to auto-run])
STAGE_ANALYSIS = {
    1: ("Startup",          "Survival Analysis",                       ["5"]),
    2: ("Hypergrowth",      "Survival Analysis + Rule of 40",          ["5", "3"]),
    3: ("Self-funding",     "Cash Conversion Cycle",                   ["6"]),
    4: ("Operating Leverage", "Margin Expansion",                      ["7"]),
    5: ("Capital Return",   "Capital allocation review (no dedicated module yet)", []),
    6: ("Decline",          "Balance Sheet Health Check",              ["8"]),
}


def _classify(d: dict) -> tuple[int, list[str]]:
    growth = d["revenue_growth"]
    op_inc = d["operating_income"]
    ni = d["net_income"]
    gp_c, gp_p = d["gross_profit_c"], d["gross_profit_p"]
    shares_growth = d["shares_growth"]
    fcf = d["fcf"]
    signals: list[str] = []
    profitable = ni > 0 and op_inc > 0

    if not profitable:
        if d["revenue"] <= 0 or gp_c <= 0:
            stage = 1
            signals.append("Little/no revenue or gross profit, with losses -> startup")
        elif growth is not None and growth >= 40 and gp_c > 0:
            stage = 2
            signals.append(
                f"Rapid revenue growth ({fmt_pct(growth)}) with positive, expanding "
                "gross profit but ongoing losses -> hypergrowth"
            )
        elif fcf >= 0:
            stage = 3
            signals.append("Near breakeven with positive free cash flow -> self-funding")
        else:
            stage = 2
            signals.append("Growing but still burning cash -> hypergrowth / self-funding boundary")
    else:
        if growth is not None and growth < 0:
            stage = 6
            signals.append(f"Revenue declining ({fmt_pct(growth)}) while profitable -> decline")
        elif shares_growth is not None and shares_growth < -0.5 and (growth is None or growth < 15):
            stage = 5
            signals.append(
                "Profitable, slow growth, shrinking share count (buybacks) -> capital return"
            )
        else:
            stage = 4
            signals.append("Consistently profitable with room to widen margins -> operating leverage")
        if gp_c > gp_p:
            signals.append("Gross profit still expanding")

    if shares_growth is not None and shares_growth > 5:
        signals.append(f"Share count rising fast ({fmt_pct(shares_growth)}) — dilution risk")
    return stage, signals


def _gather() -> tuple[str, dict]:
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            return profile.name, profile.stage_inputs()
    name = console.input("  Company name: ").strip() or "Target Company"
    rev_c = prompt_float("Revenue (current)")
    rev_p = prompt_float("Revenue (prior)")
    sh_c  = prompt_float("Shares Outstanding (current)")
    sh_p  = prompt_float("Shares Outstanding (prior)")
    return name, {
        "revenue":        rev_c,
        "revenue_growth": percent_change(rev_c, rev_p),
        "gross_profit_c": prompt_float("Gross Profit (current)"),
        "gross_profit_p": prompt_float("Gross Profit (prior)"),
        "operating_income": prompt_float("Operating Income (current)"),
        "net_income":       prompt_float("Net Income (current)"),
        "shares_growth":  percent_change(sh_c, sh_p),
        "fcf":            prompt_float("Free Cash Flow (current)"),
    }


def _run_modules(keys: list[str]) -> None:
    from analyzers import balance_health, ccc, leverage, saas, survival
    runners = {"3": saas.run, "5": survival.run, "6": ccc.run,
               "7": leverage.run, "8": balance_health.run}
    for k in keys:
        runner = runners.get(k)
        if runner:
            console.print()
            runner()


def run() -> None:
    console.rule("[bold magenta]Module 4 — Business Stage Classifier[/]")
    name, d = _gather()
    stage, signals = _classify(d)
    label, recommended, keys = STAGE_ANALYSIS[stage]
    console.print(f"\n  [bold]{name}[/] looks like a [bold cyan]Stage {stage} — {label}[/] company.")
    console.print("\n  [bold]Signals:[/]")
    for s in signals:
        console.print(f"    * {s}")
    console.print(f"\n  [bold]Recommended next analysis:[/] {recommended}")
    console.print(
        "\n  [dim]Stage detection is a heuristic — confirm it against the business "
        "narrative before relying on it.[/]"
    )
    if keys:
        ans = console.input("\n  Run the recommended analysis now? [Y/n]: ").strip().lower()
        if ans in ("", "y", "yes"):
            _run_modules(keys)
