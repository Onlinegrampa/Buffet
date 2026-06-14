"""Module 5: Survival Analysis — cash runway and dilution risk.

Bands: <1 yr CRITICAL, 1-2 yr DANGER, 2-3 yr WATCH, >3 yr SAFE.
Flags rising share count (dilution) and dependency on external financing.
"""
from __future__ import annotations

from utils.helpers import console, fmt_money, fmt_pct, percent_change, prompt_float, safe_pct
from utils.profile import get_profile

BANDS = [
    (1.0, "CRITICAL", "red", "Raise capital immediately or cut burn drastically."),
    (2.0, "DANGER",   "yellow", "Needs fresh capital within 12 months — high urgency."),
    (3.0, "WATCH",    "yellow", "Runway is tightening; plan the next raise now."),
]
SAFE_MSG = ("SAFE", "green", "Adequate runway. Focus on reaching FCF breakeven.")


def _verdict(runway_years: float) -> tuple[str, str, str]:
    for threshold, label, color, msg in BANDS:
        if runway_years < threshold:
            return label, color, msg
    return SAFE_MSG


def _report(name: str, d: dict) -> None:
    cash = d["cash"]
    fcf = d["fcf"]
    shares_growth = d["shares_growth"]
    financing = d.get("cash_from_financing", 0.0)

    console.rule(f"[bold]Survival Analysis — {name}[/]")
    console.print(f"  Cash position:      [bold]{fmt_money(cash)}[/]")
    console.print(f"  Free Cash Flow:     [bold]{fmt_money(fcf)}[/] per year")

    if fcf >= 0:
        console.print("\n  [green]FCF is positive — company is not burning cash.[/]")
        console.print("  Survival risk is low from a cash-flow perspective.")
    else:
        burn = abs(fcf)
        runway = cash / burn if burn > 0 else float("inf")
        label, color, msg = _verdict(runway)
        console.print(f"\n  Burn rate:          [bold]{fmt_money(burn)}[/] per year")
        console.print(f"  Cash runway:        [bold {color}]{runway:.1f} years[/]")
        console.print(f"  Verdict:            [{color}]{label}[/] — {msg}")

    console.rule("[bold]Dilution & Financing[/]")
    if shares_growth is None:
        console.print("  Share count change: n/a (no prior-period data)")
    elif shares_growth > 2:
        console.print(
            f"  [red]Share dilution FLAG[/]: share count up {shares_growth:+.1f}% YoY — "
            "issuing equity to fund operations erodes existing shareholders."
        )
    elif shares_growth < 0:
        console.print(
            f"  [green]Buybacks[/]: share count down {shares_growth:.1f}% YoY — "
            "returning capital to shareholders."
        )
    else:
        console.print(f"  Share count change: {shares_growth:+.1f}% YoY — minimal dilution.")

    if financing > 0:
        pct = safe_pct(financing, cash) or 0.0
        console.print(
            f"  Cash from financing: [yellow]{fmt_money(financing)}[/] "
            f"({pct:.0f}% of ending cash) — dependent on external capital."
        )
    elif financing < 0:
        console.print(f"  Cash from financing: {fmt_money(financing)} (net debt repayment / buybacks).")

    console.print(
        "\n  [dim]Runway assumes current burn rate is constant. "
        "Include debt covenants and upcoming maturities in your own assessment.[/]"
    )


def compute(profile) -> dict:
    d = profile.survival_inputs()
    cash, fcf = d["cash"], d["fcf"]
    shares_growth = d["shares_growth"]
    financing = d.get("cash_from_financing", 0.0)

    if fcf >= 0:
        runway = None
        verdict_label, verdict_cls = "SAFE", "success"
        verdict_msg = "FCF is positive — company is not burning cash. Survival risk is low."
    else:
        burn = abs(fcf)
        runway = cash / burn if burn > 0 else float("inf")
        lbl, color, msg = _verdict(runway)
        verdict_label, verdict_msg = lbl, msg
        verdict_cls = "danger" if color == "red" else ("success" if lbl == "SAFE" else "warning")

    if shares_growth is None:
        dil_cls, dil_msg = "secondary", "Share count change: n/a"
    elif shares_growth > 2:
        dil_cls = "danger"
        dil_msg = f"Dilution: share count +{shares_growth:.1f}% YoY — issuing equity erodes shareholders."
    elif shares_growth < 0:
        dil_cls = "success"
        dil_msg = f"Buybacks: share count {shares_growth:.1f}% YoY — returning capital to shareholders."
    else:
        dil_cls, dil_msg = "secondary", f"Minimal dilution: {shares_growth:+.1f}% YoY"

    fin_note = None
    if financing > 0:
        pct = (financing / cash * 100) if cash else 0
        fin_note = f"Cash from financing ${financing:,.1f}M ({pct:.0f}% of ending cash) — dependent on external capital."
    elif financing < 0:
        fin_note = f"Cash from financing ${financing:,.1f}M — net debt repayment / buybacks."

    return {
        "cash": cash, "fcf": fcf, "runway": runway,
        "positive_fcf": fcf >= 0,
        "verdict_label": verdict_label, "verdict_cls": verdict_cls, "verdict_msg": verdict_msg,
        "dil_cls": dil_cls, "dil_msg": dil_msg, "fin_note": fin_note,
    }


def run() -> None:
    console.rule("[bold magenta]Module 5 — Survival Analysis[/]")
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            console.print(f"  [green]Loaded {profile.name} from the 3-Statement Analyzer.[/]")
            _report(profile.name, profile.survival_inputs())
            return

    name = console.input("  Company name: ").strip() or "Target Company"
    cash = prompt_float("Cash & Marketable Securities")
    fcf = prompt_float("Free Cash Flow (negative = burning)")
    sh_c = prompt_float("Shares Outstanding (current)")
    sh_p = prompt_float("Shares Outstanding (prior)")
    _report(name, {
        "cash": cash,
        "fcf": fcf,
        "shares_growth": percent_change(sh_c, sh_p),
        "cash_from_financing": 0.0,
    })
