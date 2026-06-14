"""Shared helpers for FinSight CLI: formatting, change math, and input parsing."""
from __future__ import annotations

from rich.console import Console

console = Console()


def safe_pct(numerator: float, denominator: float) -> float | None:
    """Return numerator/denominator as a percentage, or None when undefined."""
    if denominator == 0:
        return None
    return (numerator / denominator) * 100.0


def absolute_change(current: float, prior: float) -> float:
    """Absolute dollar change between two periods."""
    return current - prior


def percent_change(current: float, prior: float) -> float | None:
    """Percentage change between two periods (None when prior is 0)."""
    if prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100.0


def fmt_money(value: float) -> str:
    """Format a number as currency (figures are assumed in $millions)."""
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.1f}"


def fmt_pct(value: float | None) -> str:
    """Format a signed percentage, or 'n/a' when undefined."""
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def prompt_float(label: str, default: float = 0.0) -> float:
    """Prompt for a float; blank uses the default. Strips $, comma and % symbols."""
    raw = console.input(f"  {label} [dim](default {default})[/dim]: ").strip()
    if raw == "":
        return default
    cleaned = raw.replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        console.print(f"  [yellow]Could not parse '{raw}', using {default}.[/yellow]")
        return default


def status_label(status: str) -> str:
    """Color a PASS / FAIL / WARN status for rich output."""
    colors = {"PASS": "bold green", "FAIL": "bold red", "WARN": "bold yellow"}
    return f"[{colors.get(status, 'white')}]{status}[/]"
