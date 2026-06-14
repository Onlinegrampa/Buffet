"""Module 8: Balance Sheet Health Check.

Four key ratios (current ratio, quick ratio, debt-to-equity, debt-to-assets)
plus four yellow flags: poor liquidity, goodwill overhang, rising leverage, and
declining equity — the balance-sheet red flags from the boot camp curriculum.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import console, fmt_money, fmt_pct, prompt_float, safe_pct
from utils.profile import get_profile


def _ratios(d: dict) -> dict:
    ca  = d["current_assets"]
    cl  = d["current_liabilities"]
    inv = d["inventory"]
    tl  = d["total_liabilities"]
    eq  = d["equity"]
    ta  = d["total_assets"]
    return {
        "current_ratio": ca / cl if cl else None,
        "quick_ratio":   (ca - inv) / cl if cl else None,
        "debt_to_equity": tl / eq if eq else None,
        "debt_to_assets": safe_pct(tl, ta),
    }


def _report(name: str, cur: dict, pri: dict | None = None) -> None:
    rc = _ratios(cur)
    rp = _ratios(pri) if pri else None

    table = Table(title=f"Balance Sheet Health — {name}", box=box.SIMPLE_HEAVY,
                  title_style="bold magenta")
    table.add_column("Ratio")
    table.add_column("Formula", style="dim")
    table.add_column("Current", justify="right")
    if rp:
        table.add_column("Prior", justify="right")
    table.add_column("Signal", justify="center")

    def ratio_row(label, formula, key, threshold_label, good_fn):
        vc = rc[key]
        vp = rp[key] if rp else None
        cs = f"{vc:.2f}" if vc is not None else "n/a"
        signal = good_fn(vc)
        if rp:
            ps = f"{vp:.2f}" if vp is not None else "n/a"
            table.add_row(label, formula, cs, ps, signal)
        else:
            table.add_row(label, formula, cs, signal)

    ratio_row("Current Ratio",    "Current Assets / CL",     "current_ratio",  ">= 2.0",
              lambda v: "[green]OK[/]" if v and v >= 2.0 else ("[yellow]WATCH[/]" if v and v >= 1.0 else "[red]DANGER[/]"))
    ratio_row("Quick Ratio",      "(CA - Inventory) / CL",   "quick_ratio",    ">= 1.0",
              lambda v: "[green]OK[/]" if v and v >= 1.0 else ("[yellow]WATCH[/]" if v and v >= 0.7 else "[red]DANGER[/]"))
    ratio_row("Debt / Equity",    "Total Liabilities / Equity", "debt_to_equity", "< 0.8",
              lambda v: "[green]OK[/]" if v is not None and v < 0.8 else ("[yellow]WATCH[/]" if v is not None and v < 1.5 else "[red]HIGH[/]"))
    ratio_row("Debt / Assets",    "Total Liabilities / Total Assets (%)", "debt_to_assets", "< 50%",
              lambda v: "[green]OK[/]" if v is not None and v < 50 else ("[yellow]WATCH[/]" if v is not None and v < 70 else "[red]HIGH[/]"))

    console.print()
    console.print(table)

    # Yellow flags
    console.rule("[bold]Yellow Flags[/]")
    flags = []

    cr = rc["current_ratio"]
    if cr is not None and cr < 1.0:
        flags.append(("Liquidity danger", f"Current ratio {cr:.2f} < 1.0 — cannot cover near-term obligations.", "red"))

    gw_int = cur["goodwill"] + cur["intangibles"]
    ta = cur["total_assets"]
    gw_pct = safe_pct(gw_int, ta)
    if gw_pct is not None and gw_pct > 30:
        flags.append(("Goodwill / intangibles overhang",
                      f"{gw_pct:.0f}% of assets are goodwill + intangibles — "
                      "acquisition premiums dominate the balance sheet; impairment risk.", "yellow"))

    if rp:
        da_c, da_p = rc["debt_to_assets"], rp["debt_to_assets"]
        if da_c is not None and da_p is not None and da_c > da_p + 3:
            flags.append(("Rising leverage",
                          f"Debt-to-assets rose {da_c - da_p:+.1f}pp YoY — "
                          "balance sheet is getting heavier.", "yellow"))

        eq_c, eq_p = cur["equity"], pri["equity"]
        if eq_c < eq_p:
            flags.append(("Declining equity",
                          f"Equity fell {fmt_money(eq_c - eq_p)} YoY ({eq_c - eq_p:+.0f}M) — "
                          "check for large buybacks, losses, or goodwill write-downs.", "yellow"))

    if not flags:
        console.print("  [green]No yellow flags raised.[/]")
    else:
        for title, detail, color in flags:
            console.print(f"  [{color}]{title}[/]: {detail}")

    console.print(
        "\n  [dim]Ratios benchmarks: current >= 2, quick >= 1, D/E < 0.8, D/A < 50%. "
        "Context matters — capital-light businesses naturally carry more debt.[/]"
    )


def compute(profile) -> dict:
    d = profile.balance_health_inputs()
    cur, pri = d["current"], d["prior"]
    rc, rp = _ratios(cur), _ratios(pri)

    def _sig(key, good_fn):
        v = rc[key]
        cls, txt = good_fn(v)
        return {"cur": v, "pri": rp[key], "sig_cls": cls, "sig_txt": txt}

    ratio_rows = [
        {"label": "Current Ratio",   "formula": "Current Assets / Current Liabilities", "threshold": ">= 2.0",
         **_sig("current_ratio",
                lambda v: ("ok","OK") if v and v >= 2 else (("warn","WATCH") if v and v >= 1 else ("bad","DANGER")))},
        {"label": "Quick Ratio",     "formula": "(Current Assets - Inventory) / CL",    "threshold": ">= 1.0",
         **_sig("quick_ratio",
                lambda v: ("ok","OK") if v and v >= 1 else (("warn","WATCH") if v and v >= 0.7 else ("bad","DANGER")))},
        {"label": "Debt / Equity",   "formula": "Total Liabilities / Equity",           "threshold": "< 0.8",
         **_sig("debt_to_equity",
                lambda v: ("ok","OK") if v is not None and v < 0.8 else (("warn","WATCH") if v is not None and v < 1.5 else ("bad","HIGH")))},
        {"label": "Debt / Assets %", "formula": "Total Liabilities / Total Assets",     "threshold": "< 50%",
         **_sig("debt_to_assets",
                lambda v: ("ok","OK") if v is not None and v < 50 else (("warn","WATCH") if v is not None and v < 70 else ("bad","HIGH")))},
    ]

    flags = []
    cr = rc["current_ratio"]
    if cr is not None and cr < 1.0:
        flags.append({"cls": "danger", "title": "Liquidity danger",
                      "detail": f"Current ratio {cr:.2f} < 1.0 — cannot cover near-term obligations."})

    gw_pct = safe_pct(cur["goodwill"] + cur["intangibles"], cur["total_assets"])
    if gw_pct is not None and gw_pct > 30:
        flags.append({"cls": "warning", "title": "Goodwill / Intangibles overhang",
                      "detail": f"{gw_pct:.0f}% of assets are goodwill + intangibles — impairment risk."})

    da_c, da_p = rc["debt_to_assets"], rp["debt_to_assets"]
    if da_c is not None and da_p is not None and da_c > da_p + 3:
        flags.append({"cls": "warning", "title": "Rising leverage",
                      "detail": f"Debt-to-assets rose {da_c - da_p:+.1f}pp YoY — balance sheet is getting heavier."})

    eq_c, eq_p = cur["equity"], pri["equity"]
    if eq_c < eq_p:
        flags.append({"cls": "warning", "title": "Declining equity",
                      "detail": f"Equity fell ${abs(eq_c - eq_p):,.1f}M YoY — check buybacks, losses, or goodwill write-downs."})

    return {"ratios": ratio_rows, "flags": flags}


def run() -> None:
    console.rule("[bold magenta]Module 8 — Balance Sheet Health Check[/]")
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            console.print(f"  [green]Loaded {profile.name} from the 3-Statement Analyzer.[/]")
            d = profile.balance_health_inputs()
            _report(profile.name, d["current"], d["prior"])
            return

    name = console.input("  Company name: ").strip() or "Target Company"
    console.rule("[cyan]Balance Sheet inputs[/]")
    cur = {
        "cash":                prompt_float("Cash & Marketable Securities"),
        "ar":                  prompt_float("Accounts Receivable"),
        "inventory":           prompt_float("Inventory"),
        "current_assets":      prompt_float("Total Current Assets"),
        "current_liabilities": prompt_float("Total Current Liabilities"),
        "total_liabilities":   prompt_float("Total Liabilities"),
        "equity":              prompt_float("Total Shareholders' Equity"),
        "goodwill":            prompt_float("Goodwill"),
        "intangibles":         prompt_float("Intangible Assets"),
        "total_assets":        prompt_float("Total Assets"),
        "total_debt":          0.0,
    }
    _report(name, cur)
