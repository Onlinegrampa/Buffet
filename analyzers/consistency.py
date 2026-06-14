"""Module 10: Multi-Year Consistency Tracker.

Buffett rewards consistency, especially through downturns. Walks the key metrics
across every captured period and reports how many years clear each threshold.
Most meaningful with 3+ periods captured in Module 1.
"""
from __future__ import annotations

from rich import box
from rich.table import Table

from utils.helpers import console
from utils.profile import get_profile


def _pass_count(values, test) -> tuple[int, int]:
    vals = [v for v in values if v is not None]
    return sum(1 for v in vals if test(v)), len(vals)


def _verdict(passed: int, total: int) -> str:
    if total == 0:
        return "[yellow]n/a[/]"
    if passed == total:
        return f"[green]{passed}/{total}[/]"
    return f"[yellow]{passed}/{total}[/]" if passed else f"[red]{passed}/{total}[/]"


def _trend(series) -> str:
    clean = [x for x in series if x is not None]
    if len(clean) < 2:
        return "n/a"
    # series is most-recent-first: clean[0] newest, clean[-1] oldest
    return "rising" if clean[0] > clean[-1] else ("flat" if clean[0] == clean[-1] else "declining")


def compute(profile) -> dict:
    s = profile.consistency_series()

    rows = [
        {"label": "Gross Margin",     "threshold": "> 40%", "test": lambda v: v > 40, "vals": s["gross_margin"], "fmt": "pct"},
        {"label": "Operating Margin", "threshold": "> 0%",  "test": lambda v: v > 0,  "vals": s["operating_margin"], "fmt": "pct"},
        {"label": "Net Margin",       "threshold": "> 20%", "test": lambda v: v > 20, "vals": s["net_margin"], "fmt": "pct"},
        {"label": "EPS (positive)",   "threshold": "> 0",   "test": lambda v: v > 0,  "vals": s["eps"], "fmt": "num"},
    ]
    for row in rows:
        vals = [v for v in row["vals"] if v is not None]
        passed = sum(1 for v in vals if row["test"](v))
        total = len(vals)
        row["passed"], row["total"] = passed, total
        row["verdict_cls"] = "success" if passed == total and total > 0 else ("warning" if passed > 0 else "danger")

    def trend(series):
        clean = [x for x in series if x is not None]
        if len(clean) < 2:
            return "n/a"
        return "rising" if clean[0] > clean[-1] else ("flat" if clean[0] == clean[-1] else "declining")

    return {
        "labels": s["labels"],
        "rows": rows,
        "revenue_trend": trend(s["revenue"]),
        "re_trend": trend(s["retained_earnings"]),
        "period_count": profile.period_count,
    }


def run() -> None:
    console.rule("[bold magenta]Module 10 — Multi-Year Consistency Tracker[/]")
    profile = get_profile()
    if profile is None:
        console.print("  [yellow]No saved profile. Run Module 1 first (capture 3+ periods).[/]")
        return
    if profile.period_count < 3:
        console.print(
            f"  [yellow]Only {profile.period_count} periods captured — re-run Module 1 "
            "with 3+ periods for a meaningful consistency read. Showing what's available.[/]"
        )

    s = profile.consistency_series()
    labels = s["labels"]
    table = Table(title=f"Consistency — {profile.name}", box=box.SIMPLE_HEAVY,
                  title_style="bold magenta")
    table.add_column("Metric")
    for lbl in labels:
        table.add_column(lbl, justify="right")
    table.add_column("Holds", justify="center")

    def margin_row(name, key, test, thresh):
        vals = s[key]
        cells = [f"{v:.1f}%" if v is not None else "n/a" for v in vals]
        passed, total = _pass_count(vals, test)
        table.add_row(f"{name} ({thresh})", *cells, _verdict(passed, total))

    margin_row("Gross margin",     "gross_margin",     lambda v: v > 40, ">40%")
    margin_row("Operating margin", "operating_margin", lambda v: v > 0,  ">0")
    margin_row("Net margin",       "net_margin",       lambda v: v > 20, ">20%")

    eps = s["eps"]
    eps_cells = [f"{v:.2f}" for v in eps]
    pos, total = _pass_count(eps, lambda v: v > 0)
    table.add_row("EPS (positive)", *eps_cells, _verdict(pos, total))

    console.print()
    console.print(table)
    console.print(f"\n  Revenue trend (oldest -> newest): [bold]{_trend(s['revenue'])}[/]")
    console.print(f"  Retained earnings trend: [bold]{_trend(s['retained_earnings'])}[/]")
    console.print(
        "\n  [dim]A metric that clears its threshold every year (ideally through a "
        "downturn) is far stronger than one that only clears it on average.[/]"
    )
