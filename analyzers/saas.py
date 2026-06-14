"""Module 3: SaaS Rule of 40 Dashboard.

Rule of 40 = Revenue Growth Rate (%) + a Profit Margin (%). Free cash flow margin
is the preferred profitability measure, but GAAP operating margin and net margin
are supported. >= 40 is HEALTHY; higher is always better. When a session profile
exists, growth and all three margin options are derived from the saved statements.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import console, prompt_float
from utils.profile import get_profile

MARGIN_TYPES = {
    "1": "Free Cash Flow Margin",
    "2": "GAAP Operating Margin",
    "3": "Net Margin",
}


def compute(name: str, growth: float, margin: float, margin_label: str) -> dict:
    """Return structured Rule of 40 analysis for web rendering."""
    score = growth + margin
    ml = margin_label.lower()
    if margin < 0 and growth >= 40:
        profile_type = "aggressive"
        insight = (
            f"Growing {growth:.0f}% while burning cash ({margin_label} {margin:.0f}%). "
            f"Clears the bar on growth alone, but the negative margin is real cash burn — "
            f"confirm the balance sheet can fund losses until margins inflect."
        )
    elif score >= 40 and margin >= 0 and growth >= 0:
        profile_type = "balanced"
        insight = (
            f"Growth ({growth:.0f}%) and {ml} ({margin:.0f}%) both pull their weight — "
            f"the most durable position, funding growth without leaning on outside capital."
        )
    elif score < 40 and growth >= 40:
        profile_type = "at_risk"
        insight = (
            f"Even {growth:.0f}% growth cannot offset a {margin:.0f}% {ml}. "
            f"This is the bankruptcy-risk zone — the burn is outrunning the growth."
        )
    else:
        profile_type = "maturing"
        insight = (
            f"With {growth:.0f}% growth and a {margin:.0f}% {ml}, lean on margin "
            f"expansion to carry the score. The Rule of 40 fits high-growth SaaS best; "
            f"for slower, profitable firms use other valuation measures."
        )
    return {
        "name": name, "growth": growth, "margin": margin,
        "margin_label": margin_label, "score": score,
        "passes": score >= 40, "profile_type": profile_type, "insight": insight,
    }


def _insight(growth: float, margin: float, score: float, margin_label: str) -> None:
    ml = margin_label.lower()
    if margin < 0 and growth >= 40:
        cushion = "comfortably above" if score >= 55 else "only just above"
        console.print(
            f"  Profile: [yellow]aggressive market capture[/]. Growing {growth:.0f}% "
            f"while burning cash ({margin_label} {margin:.0f}%). It clears the bar on "
            f"growth alone, but the negative margin is real cash burn — confirm the "
            f"balance sheet can fund losses until margins inflect. Score {score:.0f} is "
            f"{cushion} 40."
        )
    elif score >= 40 and margin >= 0 and growth >= 0:
        console.print(
            f"  Profile: [green]balanced[/]. Growth ({growth:.0f}%) and {ml} "
            f"({margin:.0f}%) both pull their weight — the most durable position, "
            f"funding growth without leaning on outside capital."
        )
    elif score < 40 and growth >= 40:
        console.print(
            f"  Profile: [red]growth at any cost[/]. Even {growth:.0f}% growth can't "
            f"offset a {margin:.0f}% {ml}. This is the bankruptcy-risk zone — the "
            f"burn is outrunning the growth."
        )
    else:
        console.print(
            f"  Profile: [yellow]maturing / slowing[/]. With {growth:.0f}% growth and a "
            f"{margin:.0f}% {ml}, lean on margin expansion to carry the score. The Rule "
            f"of 40 fits high-growth, cash-burning SaaS best; for slower, profitable "
            f"firms use other measures."
        )
    console.print(
        "\n  [dim]Note: the Rule of 40 is a yearly figure that works best for "
        "service/SaaS businesses; higher is always better (an 80 beats a 40).[/]"
    )


def _report(name: str, growth: float, margin: float, margin_label: str) -> None:
    score = growth + margin
    table = Table(title=f"Rule of 40 — {name}", box=box.SIMPLE_HEAVY,
                  title_style="bold magenta")
    table.add_column("Component")
    table.add_column("Value", justify="right")
    table.add_row("Revenue Growth Rate", f"{growth:+.1f}%")
    table.add_row(margin_label, f"{margin:+.1f}%")
    table.add_row("[bold]Rule of 40 Score[/]", f"[bold]{score:+.1f}[/]")
    console.print()
    console.print(table)

    if score >= 40:
        console.print(f"\n  Status: [bold green]HEALTHY / PASS[/] "
                      f"(score {score:.1f} >= 40)")
    else:
        console.print(f"\n  Status: [bold red]HIGH RISK / FAIL[/] "
                      f"(score {score:.1f} < 40)")

    console.rule("[bold]Contextual Breakdown[/]")
    _insight(growth, margin, score, margin_label)


def _pick_margin(margins: dict[str, float | None]) -> tuple[str, float | None]:
    console.print("\n  Profitability measure to use:")
    keys = list(margins.keys())
    for i, key in enumerate(keys, 1):
        mv = margins[key]
        disp = f"{mv:+.1f}%" if mv is not None else "n/a"
        console.print(f"    {i}. {key}  [dim]({disp})[/]")
    sel = console.input(f"  Select [1-{len(keys)}] (default 1): ").strip() or "1"
    try:
        idx = int(sel) - 1
        label = keys[idx] if 0 <= idx < len(keys) else keys[0]
    except ValueError:
        label = keys[0]
    return label, margins[label]


def _run_from_profile(profile) -> None:
    console.print(f"  [green]Loaded {profile.name} from the 3-Statement Analyzer.[/]")
    data = profile.rule_of_40_inputs()
    growth = data["growth"]
    if growth is None:
        console.print("  [yellow]Prior-year revenue is 0 — can't derive growth.[/]")
        growth = prompt_float("Revenue Growth Rate (%)")
    else:
        console.print(f"  Derived revenue growth rate: [bold]{growth:+.1f}%[/]")
    margin_label, margin = _pick_margin(data["margins"])
    if margin is None:
        console.print(f"  [yellow]{margin_label} couldn't be derived (revenue is 0).[/]")
        margin = prompt_float(f"{margin_label} (%)")
    _report(profile.name, growth, margin, margin_label)


def _run_manual() -> None:
    name = console.input("  Company name: ").strip() or "Target Company"
    console.print("\n  Profitability measure to use:")
    for key, val in MARGIN_TYPES.items():
        console.print(f"    {key}. {val}")
    choice = console.input("  Select [1-3] (default 1): ").strip() or "1"
    margin_label = MARGIN_TYPES.get(choice, MARGIN_TYPES["1"])
    growth = prompt_float("Revenue Growth Rate (%)")
    margin = prompt_float(f"{margin_label} (%)")
    _report(name, growth, margin, margin_label)


def run() -> None:
    console.rule("[bold magenta]Module 3 — SaaS Rule of 40 Dashboard[/]")
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            _run_from_profile(profile)
            return
    _run_manual()
