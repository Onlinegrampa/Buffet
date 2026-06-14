"""FinSight CLI - financial analysis suite (10 modules, fully offline, no API).

  1 Core 3-Statement Analyzer      6 Cash Conversion Cycle
  2 Buffett Moat Scanner           7 Operating Leverage / Margin Expansion
  3 SaaS Rule of 40 Dashboard      8 Balance Sheet Health Check
  4 Business Stage Classifier      9 Income Statement Scanner
  5 Survival Analysis             10 Multi-Year Consistency Tracker

Usage:
  python main.py            # interactive menu
  python main.py -m 4       # jump straight to a module
"""
from __future__ import annotations

import argparse

from rich.console import Console
from rich.panel import Panel

from analyzers import (
    balance_health, buffett, ccc, consistency, income_scan, leverage,
    saas, statements, stage, survival,
)
from utils.profile import get_profile

console = Console()

BANNER = (
    "[bold cyan]FinSight CLI[/]\n"
    "[dim]Statements, stage, moats, survival, growth, leverage, consistency — all offline[/]"
)

# key: (label, runner, reads_profile)
MODULES = {
    "1":  ("Core 3-Statement Analyzer",              statements.run,    False),
    "2":  ("Buffett Moat Scanner (14 Rules)",         buffett.run,       True),
    "3":  ("SaaS Rule of 40 Dashboard",               saas.run,          True),
    "4":  ("Business Stage Classifier (auto-routes)", stage.run,         True),
    "5":  ("Survival Analysis (cash runway)",         survival.run,      True),
    "6":  ("Cash Conversion Cycle",                   ccc.run,           True),
    "7":  ("Operating Leverage / Margin Expansion",   leverage.run,      True),
    "8":  ("Balance Sheet Health Check",              balance_health.run, True),
    "9":  ("Income Statement Scanner",                income_scan.run,   True),
    "10": ("Multi-Year Consistency Tracker",          consistency.run,   True),
}


def menu() -> None:
    console.print(Panel(BANNER, border_style="cyan"))
    while True:
        profile = get_profile()
        console.print("\n[bold]Select a module:[/]")
        for key in sorted(MODULES, key=int):
            label, _, reads = MODULES[key]
            tag = f"  [dim](saved: {profile.name})[/]" if (reads and profile) else ""
            console.print(f"  {key}. {label}{tag}")
        console.print("  q. Quit")
        choice = console.input("\n  > ").strip().lower()
        if choice in ("q", "quit", "exit"):
            console.print("[dim]Goodbye.[/]")
            return
        module = MODULES.get(choice)
        if module is None:
            console.print("[yellow]  Invalid choice, try again.[/]")
            continue
        console.print()
        module[1]()


def main() -> None:
    parser = argparse.ArgumentParser(description="FinSight CLI financial analysis suite")
    parser.add_argument("-m", "--module", choices=list(MODULES),
                        help="Run a module directly (1-10)")
    args = parser.parse_args()
    if args.module:
        MODULES[args.module][1]()
    else:
        menu()


if __name__ == "__main__":
    main()
