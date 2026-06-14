"""Module 6: Cash Conversion Cycle.

CCC = DIO + DSO - DPO
  DIO = Inventory / COGS * 365   (days inventory outstanding)
  DSO = AR / Revenue * 365       (days sales outstanding)
  DPO = AP / COGS * 365          (days payable outstanding)

Lower CCC = faster cash conversion. Negative CCC (e.g. Amazon, Costco) means
customers pay before the company pays suppliers — a structural cash advantage.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import console, fmt_pct, prompt_float, safe_pct
from utils.profile import get_profile


def _ccc(d: dict) -> tuple[float | None, float | None, float | None, float | None]:
    rev, cogs = d["revenue"], d["cogs"]
    if rev == 0 or cogs == 0:
        return None, None, None, None
    dio = d["inventory"] / cogs * 365
    dso = d["ar"] / rev * 365
    dpo = d["ap"] / cogs * 365
    return dio, dso, dpo, dio + dso - dpo


def _report(name: str, cur: dict, pri: dict | None = None) -> None:
    dio_c, dso_c, dpo_c, ccc_c = _ccc(cur)

    table = Table(title=f"Cash Conversion Cycle — {name}", box=box.SIMPLE_HEAVY,
                  title_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Formula", style="dim")
    table.add_column("Current", justify="right")
    if pri:
        table.add_column("Prior", justify="right")
        table.add_column("Change", justify="right")

    def fmt(v: float | None) -> str:
        return f"{v:.1f} days" if v is not None else "n/a"

    def _row(label, formula, vc, vp=None):
        if pri:
            change = (f"{vc - vp:+.1f}d" if vc is not None and vp is not None else "n/a")
            color = "green" if (vc is not None and vp is not None and vc <= vp) else "red"
            table.add_row(label, formula, fmt(vc), fmt(vp), f"[{color}]{change}[/]")
        else:
            table.add_row(label, formula, fmt(vc))

    if pri:
        _, _, _, ccc_p = _ccc(pri)
        dio_p = pri["inventory"] / pri["cogs"] * 365 if pri["cogs"] else None
        dso_p = pri["ar"] / pri["revenue"] * 365 if pri["revenue"] else None
        dpo_p = pri["ap"] / pri["cogs"] * 365 if pri["cogs"] else None
    else:
        dio_p = dso_p = dpo_p = ccc_p = None

    _row("DIO  (Days Inventory)",  "Inventory / COGS * 365", dio_c, dio_p)
    _row("DSO  (Days Receivable)", "AR / Revenue * 365",     dso_c, dso_p)
    _row("DPO  (Days Payable)",    "AP / COGS * 365",        dpo_c, dpo_p)
    _row("CCC  (Net cycle)",       "DIO + DSO - DPO",        ccc_c, ccc_p)

    console.print()
    console.print(table)

    if ccc_c is not None:
        console.rule("[bold]Interpretation[/]")
        if ccc_c < 0:
            console.print(
                f"  [green]Negative CCC ({ccc_c:.1f} days)[/] — customers pay before the company "
                "pays suppliers. This is a structural cash advantage (Amazon / Costco model)."
            )
        elif ccc_c < 30:
            console.print(
                f"  [green]Very efficient ({ccc_c:.1f} days)[/] — cash moves through the business quickly."
            )
        elif ccc_c < 60:
            console.print(f"  [yellow]Moderate cycle ({ccc_c:.1f} days)[/] — typical for many industries.")
        else:
            console.print(
                f"  [red]Long cycle ({ccc_c:.1f} days)[/] — cash is tied up. "
                "Look for inventory build-up or slow receivables collection."
            )
        if pri and ccc_p is not None:
            delta = ccc_c - ccc_p
            direction = "improving" if delta < 0 else "worsening"
            console.print(f"  YoY trend: [bold]{delta:+.1f} days[/] — {direction}.")


def run() -> None:
    console.rule("[bold magenta]Module 6 — Cash Conversion Cycle[/]")
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            console.print(f"  [green]Loaded {profile.name} from the 3-Statement Analyzer.[/]")
            d = profile.ccc_inputs()
            _report(profile.name, d["current"], d["prior"])
            return

    name = console.input("  Company name: ").strip() or "Target Company"
    revenue   = prompt_float("Revenue")
    cogs      = prompt_float("Cost of Goods Sold (COGS)")
    ar        = prompt_float("Accounts Receivable")
    inventory = prompt_float("Inventory")
    ap        = prompt_float("Accounts Payable")
    _report(name, {"revenue": revenue, "cogs": cogs, "ar": ar,
                   "inventory": inventory, "ap": ap})
