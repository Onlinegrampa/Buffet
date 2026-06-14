"""Module 7: Operating Leverage / Margin Expansion.

Shows the gross-to-operating margin spread (the fixed-cost layer) and the
incremental margins between periods. The 75/25 quality signal: great businesses
convert ~75%+ of each incremental revenue dollar to gross profit and 25%+ to
operating income — meaning fixed costs are growing slower than revenue.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import console, fmt_money, fmt_pct, percent_change, prompt_float, safe_pct
from utils.profile import CompanyProfile, get_profile


def _incremental_margin(delta_num: float, delta_rev: float) -> float | None:
    return safe_pct(delta_num, delta_rev)


def _report(name: str, cur: dict, pri: dict | None = None) -> None:
    gm_c = cur["gross_margin"]
    om_c = cur["operating_margin"]
    spread = (gm_c - om_c) if (gm_c is not None and om_c is not None) else None

    table = Table(title=f"Operating Leverage — {name}", box=box.SIMPLE_HEAVY,
                  title_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Current", justify="right")
    if pri:
        table.add_column("Prior", justify="right")
        table.add_column("Change", justify="right")

    def row(label, vc, vp=None, pct=True, good_up=True):
        cs = f"{vc:.1f}%" if vc is not None else "n/a"
        if pri and vp is not None and vc is not None:
            delta = vc - vp
            color = "green" if (delta >= 0) == good_up else "red"
            table.add_row(label, cs, f"{vp:.1f}%", f"[{color}]{delta:+.1f}pp[/]")
        elif pri:
            table.add_row(label, cs, "n/a", "n/a")
        else:
            table.add_row(label, cs)

    row("Gross Margin",     gm_c, pri.get("gross_margin")    if pri else None)
    row("Operating Margin", om_c, pri.get("operating_margin") if pri else None)
    row("Fixed Cost Layer (spread)", spread,
        ((pri["gross_margin"] - pri["operating_margin"])
         if pri and pri.get("gross_margin") is not None and pri.get("operating_margin") is not None
         else None),
        good_up=False)

    console.print()
    console.print(table)

    # Incremental margins (only when prior data available)
    if pri and pri.get("revenue") is not None:
        rev_c, rev_p = cur["revenue"], pri["revenue"]
        gp_c = cur["revenue"] * (gm_c or 0) / 100
        gp_p = pri["revenue"] * (pri.get("gross_margin") or 0) / 100
        oi_c = cur["operating_income"]
        oi_p = pri.get("operating_income", 0.0)
        delta_rev = rev_c - rev_p
        if abs(delta_rev) > 0.1:
            inc_gm = _incremental_margin(gp_c - gp_p, delta_rev)
            inc_om = _incremental_margin(oi_c - oi_p, delta_rev)
            console.rule("[bold]Incremental Margins[/]")
            console.print(
                f"  For each incremental revenue dollar, "
                f"[bold]{fmt_pct(inc_gm)}[/] flowed to gross profit "
                f"and [bold]{fmt_pct(inc_om)}[/] to operating income."
            )
            q_gm = inc_gm is not None and inc_gm >= 75
            q_om = inc_om is not None and inc_om >= 25
            if q_gm and q_om:
                console.print(
                    "  [green]75/25 quality signal PASS[/] — fixed costs are scaling slower than "
                    "revenue; the business has meaningful operating leverage."
                )
            elif inc_gm is not None and inc_gm >= 50:
                console.print(
                    "  [yellow]Partial operating leverage[/] — gross profit is expanding but "
                    "fixed costs are absorbing a large share of incremental revenue."
                )
            else:
                console.print(
                    "  [red]Weak leverage[/] — fixed costs are rising nearly as fast as revenue; "
                    "little incremental profit falls through to operating income."
                )

    console.print(
        "\n  [dim]The fixed-cost layer = Gross Margin - Operating Margin. "
        "As revenue scales, a shrinking layer signals improving leverage.[/]"
    )


def run() -> None:
    console.rule("[bold magenta]Module 7 — Operating Leverage / Margin Expansion[/]")
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            console.print(f"  [green]Loaded {profile.name} from the 3-Statement Analyzer.[/]")
            d = profile.leverage_inputs()
            v = CompanyProfile._val
            pri = {
                "revenue": v(profile.income_statement, "Revenue", "prior"),
                "gross_margin": safe_pct(
                    v(profile.income_statement, "Gross Profit", "prior"),
                    v(profile.income_statement, "Revenue", "prior")),
                "operating_margin": safe_pct(
                    v(profile.income_statement, "Operating Income (EBIT)", "prior"),
                    v(profile.income_statement, "Revenue", "prior")),
                "operating_income": v(profile.income_statement, "Operating Income (EBIT)", "prior"),
            }
            _report(profile.name, d, pri)
            return

    name = console.input("  Company name: ").strip() or "Target Company"
    rev_c = prompt_float("Revenue (current)")
    gp_c  = prompt_float("Gross Profit (current)")
    oi_c  = prompt_float("Operating Income / EBIT (current)")
    cur = {
        "revenue": rev_c,
        "gross_margin": safe_pct(gp_c, rev_c),
        "operating_margin": safe_pct(oi_c, rev_c),
        "operating_income": oi_c,
    }
    console.print("  [dim]Enter prior-period figures for incremental margin analysis (Enter = skip).[/]")
    rev_p = prompt_float("Revenue (prior)", 0.0)
    if rev_p > 0:
        gp_p = prompt_float("Gross Profit (prior)")
        oi_p = prompt_float("Operating Income (prior)")
        pri = {
            "revenue": rev_p,
            "gross_margin": safe_pct(gp_p, rev_p),
            "operating_margin": safe_pct(oi_p, rev_p),
            "operating_income": oi_p,
        }
        _report(name, cur, pri)
    else:
        _report(name, cur)
