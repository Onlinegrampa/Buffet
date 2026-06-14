"""Module 9: Income Statement Scanner (margins + yellow flags).

Margin trends plus the income-statement yellow flags from the boot camp: margin
compression, creeping SG&A, rising interest expense, and share dilution. Growth
bands: >25% rapid, <10% slow.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import console, fmt_money, fmt_pct, percent_change, prompt_float, safe_pct
from utils.profile import get_profile


def _margins(p: dict) -> dict:
    return {
        "gross":    safe_pct(p["gross_profit"], p["revenue"]),
        "operating": safe_pct(p["operating_income"], p["revenue"]),
        "net":      safe_pct(p["net_income"], p["revenue"]),
        "sga_pct":  safe_pct(p["sga"], p["revenue"]),
    }


def _report(name: str, cur: dict, pri: dict) -> None:
    mc, mp = _margins(cur), _margins(pri)
    table = Table(title=f"Income Statement Scan — {name}", box=box.SIMPLE_HEAVY,
                  title_style="bold magenta")
    table.add_column("Margin")
    table.add_column("Current", justify="right")
    table.add_column("Prior", justify="right")
    table.add_column("Trend", justify="center")

    def m_row(label, key, good_up=True):
        c, p = mc[key], mp[key]
        cs = f"{c:.1f}%" if c is not None else "n/a"
        ps = f"{p:.1f}%" if p is not None else "n/a"
        if c is None or p is None:
            tr = "--"
        else:
            up = c > p
            arrow = "^" if up else "v"
            tr = f"[green]{arrow}[/]" if up == good_up else f"[red]{arrow}[/]"
        table.add_row(label, cs, ps, tr)

    m_row("Gross margin",        "gross")
    m_row("Operating margin",    "operating")
    m_row("Net margin",          "net")
    m_row("SG&A % of revenue",   "sga_pct", good_up=False)
    console.print()
    console.print(table)

    growth = percent_change(cur["revenue"], pri["revenue"])
    band = ("n/a" if growth is None else
            "[green]rapid growth[/]" if growth >= 25 else
            "[yellow]slow growth[/]" if growth <= 10 else "moderate growth")
    console.print(f"\n  Revenue growth: [bold]{fmt_pct(growth)}[/] ({band})  [dim]>25% rapid, <10% slow[/]")

    md = [k for k in ("gross", "operating", "net")
          if mc[k] is not None and mp[k] is not None and mc[k] < mp[k]]
    sga_disp = (f'{mp["sga_pct"]:.1f}% -> {mc["sga_pct"]:.1f}%'
                if mc["sga_pct"] is not None and mp["sga_pct"] is not None else "n/a")
    sga_up = mc["sga_pct"] is not None and mp["sga_pct"] is not None and mc["sga_pct"] > mp["sga_pct"]
    int_up = cur["interest"] > pri["interest"]
    sh_growth = percent_change(cur["shares"], pri["shares"])
    if sh_growth is None:
        dil, dil_detail = "OK", "n/a"
    elif sh_growth > 2:
        dil, dil_detail = "FLAG", f"+{sh_growth:.1f}% shares"
    elif sh_growth < 0:
        dil, dil_detail = "OK", f"{sh_growth:.1f}% (buybacks)"
    else:
        dil, dil_detail = "OK", f"{sh_growth:+.1f}%"

    flags = [
        ("Margins compressing", ", ".join(md) or "none", "FLAG" if md else "OK"),
        ("SG&A creeping up",    sga_disp,                "FLAG" if sga_up else "OK"),
        ("Interest expense rising",
         f'{fmt_money(pri["interest"])} -> {fmt_money(cur["interest"])}',
         "WATCH" if int_up else "OK"),
        ("Share dilution", dil_detail, dil),
    ]
    label_map = {"OK": "[green]OK[/]", "WATCH": "[yellow]WATCH[/]", "FLAG": "[red]FLAG[/]"}
    ft = Table(title="Income Statement Yellow Flags", box=box.SIMPLE_HEAVY, title_style="bold yellow")
    ft.add_column("Flag")
    ft.add_column("Detail", style="dim")
    ft.add_column("Status", justify="center")
    raised = 0
    for fn, detail, st in flags:
        raised += st in ("FLAG", "WATCH")
        ft.add_row(fn, detail, label_map[st])
    console.print()
    console.print(ft)
    console.print(f"\n  {raised} of 4 flags raised. [dim]Yellow = worth a closer look.[/]")


def compute(profile) -> dict:
    d = profile.income_scan_inputs()
    cur, pri = d["current"], d["prior"]
    mc, mp = _margins(cur), _margins(pri)

    margin_rows = [
        {"label": "Gross Margin",      "cur": mc["gross"],     "pri": mp["gross"],     "good_up": True},
        {"label": "Operating Margin",  "cur": mc["operating"], "pri": mp["operating"], "good_up": True},
        {"label": "Net Margin",        "cur": mc["net"],       "pri": mp["net"],       "good_up": True},
        {"label": "SG&A % of Revenue", "cur": mc["sga_pct"],   "pri": mp["sga_pct"],   "good_up": False},
    ]

    growth = percent_change(cur["revenue"], pri["revenue"])
    if growth is None:   band_cls, band_txt = "secondary", "n/a"
    elif growth >= 25:   band_cls, band_txt = "success", f"Rapid growth (+{growth:.1f}%)"
    elif growth <= 10:   band_cls, band_txt = "warning",  f"Slow growth ({growth:+.1f}%)"
    else:                band_cls, band_txt = "primary",   f"Moderate growth ({growth:+.1f}%)"

    compressed = [k for k in ("gross", "operating", "net")
                  if mc[k] is not None and mp[k] is not None and mc[k] < mp[k]]
    sga_up = mc["sga_pct"] is not None and mp["sga_pct"] is not None and mc["sga_pct"] > mp["sga_pct"]
    int_up = cur["interest"] > pri["interest"]
    sh_growth = percent_change(cur["shares"], pri["shares"])
    dil = sh_growth is not None and sh_growth > 2

    sga_detail = (f'{mp["sga_pct"]:.1f}% -> {mc["sga_pct"]:.1f}%'
                  if mc["sga_pct"] is not None and mp["sga_pct"] is not None else "n/a")
    flags = [
        {"label": "Margins compressing",     "detail": ", ".join(compressed) or "none",              "status": "FLAG" if compressed else "OK"},
        {"label": "SG&A creeping up",        "detail": sga_detail,                                   "status": "FLAG" if sga_up else "OK"},
        {"label": "Interest expense rising", "detail": f'${pri["interest"]:,.1f}M -> ${cur["interest"]:,.1f}M', "status": "WATCH" if int_up else "OK"},
        {"label": "Share dilution",          "detail": f"{sh_growth:+.1f}% YoY" if sh_growth is not None else "n/a", "status": "FLAG" if dil else "OK"},
    ]

    return {
        "margins": margin_rows, "growth": growth,
        "band_cls": band_cls, "band_txt": band_txt,
        "flags": flags, "flags_raised": sum(1 for f in flags if f["status"] in ("FLAG", "WATCH")),
    }


def run() -> None:
    console.rule("[bold magenta]Module 9 — Income Statement Scanner[/]")
    profile = get_profile()
    if profile is not None:
        choice = console.input(
            f"  Use saved figures for '[bold]{profile.name}[/]'? [Y/n]: "
        ).strip().lower()
        if choice in ("", "y", "yes"):
            d = profile.income_scan_inputs()
            _report(profile.name, d["current"], d["prior"])
            return
    name = console.input("  Company name: ").strip() or "Target Company"
    cur, pri = {}, {}
    for period, store in (("current", cur), ("prior", pri)):
        console.rule(f"[cyan]{period.capitalize()} period[/]")
        store["revenue"]        = prompt_float("Revenue")
        store["gross_profit"]   = prompt_float("Gross Profit")
        store["operating_income"] = prompt_float("Operating Income (EBIT)")
        store["net_income"]     = prompt_float("Net Income")
        store["sga"]            = prompt_float("SG&A (S&M + G&A)")
        store["interest"]       = prompt_float("Interest Expense")
        store["shares"]         = prompt_float("Diluted Shares Outstanding")
        store["eps"]            = prompt_float("Diluted EPS")
    _report(name, cur, pri)
