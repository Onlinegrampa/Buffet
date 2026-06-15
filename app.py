"""FinSight web app — enter financial statements in the browser, get instant analysis."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template, request, Response, url_for

from analyzers.balance_health import compute as balance_health_compute
from analyzers.buffett import compute as buffett_compute
from analyzers.ccc import compute as ccc_compute
from analyzers.consistency import compute as consistency_compute
from analyzers.income_scan import compute as income_scan_compute
from analyzers.leverage import compute as leverage_compute
from analyzers.saas import compute as saas_compute
from analyzers.stage import compute as stage_compute
from analyzers.statements import (
    BALANCE_SHEET,
    CASH_FLOW,
    INCOME_STATEMENT,
    compute as stmt_compute,
)
from analyzers.survival import compute as survival_compute
from utils.profile import CompanyProfile

app = Flask(__name__)

MAX_PERIODS = 8
DEFAULT_PERIOD_LABELS = ["FY2024", "FY2023", "FY2022", "FY2021",
                         "FY2020", "FY2019", "FY2018", "FY2017"]

HIGHLIGHT = {
    "Total Assets", "Total Liabilities", "Total Shareholders' Equity",
    "Revenue", "Gross Profit", "Operating Income (EBIT)", "Net Income",
    "Operating Cash Flow (OCF)", "Free Cash Flow (FCF)",
}

REPORTS_DIR = Path(__file__).parent / "saved_reports"
REPORTS_DIR.mkdir(exist_ok=True)

# In-memory store for the current session (fast access for results page)
_report_store: dict = {}


# ── Jinja filters ─────────────────────────────────────────────────────────────

@app.template_filter("money")
def money_filter(v: float | None) -> str:
    if v is None:
        return "n/a"
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.1f}M"


@app.template_filter("pct")
def pct_filter(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:+.1f}%"


# ── Disk helpers ──────────────────────────────────────────────────────────────

def _save_report(report_id: str, data: dict, html: str) -> None:
    """Persist report HTML and metadata to disk."""
    meta = {
        "report_id": report_id,
        "company":   data["company"],
        "periods":   data["periods"],
        "unit_label": data["unit_label"],
        "generated": data["generated"],
    }
    (REPORTS_DIR / f"{report_id}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    (REPORTS_DIR / f"{report_id}.html").write_text(html, encoding="utf-8")


def _load_all_meta() -> list[dict]:
    """Return all saved report metadata sorted newest-first."""
    metas = []
    for p in REPORTS_DIR.glob("*.json"):
        try:
            metas.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    metas.sort(key=lambda m: m.get("generated", ""), reverse=True)
    return metas


def _delete_report(report_id: str) -> None:
    for ext in ("html", "json"):
        f = REPORTS_DIR / f"{report_id}.{ext}"
        if f.exists():
            f.unlink()
    _report_store.pop(report_id, None)


# ── Analysis ──────────────────────────────────────────────────────────────────

def _run_analysis(request_form) -> dict:
    n = min(MAX_PERIODS, max(2, int(request_form.get("n_periods") or 2)))
    periods = [
        (request_form.get(f"period_{i}") or DEFAULT_PERIOD_LABELS[i]).strip()
        for i in range(n)
    ]
    name = request_form.get("company_name", "").strip() or "Target Company"

    unit = request_form.get("unit", "millions")
    unit_factor = {"hundreds": 0.0001, "thousands": 0.001, "millions": 1.0}.get(unit, 1.0)
    unit_label  = {"hundreds": "$00s (Hundreds)", "thousands": "$000s (Thousands)",
                   "millions": "$M (Millions)"}.get(unit, "$M (Millions)")

    def parse_stmt(prefix: str, items: list[str]) -> dict:
        stmt: dict = {}
        for item_idx, item in enumerate(items):
            stmt[item] = {}
            for p_idx in range(n):
                try:
                    val = float(request_form.get(f"{prefix}_{item_idx}_{p_idx}") or 0)
                except ValueError:
                    val = 0.0
                stmt[item][p_idx] = val * unit_factor
        return stmt

    profile = CompanyProfile(name, periods)
    profile.balance_sheet    = parse_stmt("bs",  BALANCE_SHEET)
    profile.income_statement = parse_stmt("inc", INCOME_STATEMENT)
    profile.cash_flow        = parse_stmt("cf",  CASH_FLOW)

    stmt   = stmt_compute(profile)
    buft   = buffett_compute(profile.name, profile.buffett_inputs())
    r40    = profile.rule_of_40_inputs()
    growth = r40["growth"] if r40["growth"] is not None else 0.0
    saas_results = {
        label: saas_compute(profile.name, growth, (m if m is not None else 0.0), label)
        for label, m in r40["margins"].items()
    }
    stage       = stage_compute(profile)
    survival    = survival_compute(profile)
    ccc         = ccc_compute(profile)
    leverage    = leverage_compute(profile)
    bhealth     = balance_health_compute(profile)
    income_scan = income_scan_compute(profile)
    consistency = consistency_compute(profile)

    return dict(
        company=name, periods=periods, stmt=stmt, buft=buft,
        saas_results=saas_results, growth=growth,
        stage=stage, survival=survival, ccc=ccc, leverage=leverage,
        bhealth=bhealth, income_scan=income_scan, consistency=consistency,
        unit_label=unit_label,
        generated=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        balance_sheet=BALANCE_SHEET,
        income_statement=INCOME_STATEMENT,
        cash_flow=CASH_FLOW,
        highlight=HIGHLIGHT,
        max_periods=MAX_PERIODS,
        default_period_labels=DEFAULT_PERIOD_LABELS,
    )


@app.route("/analyze", methods=["POST"])
def analyze() -> str:
    data = _run_analysis(request.form)
    report_id = str(uuid.uuid4())
    _report_store[report_id] = data

    # Render and save to disk immediately
    html = render_template("report.html", **data)
    _save_report(report_id, data, html)

    return render_template("results.html", report_id=report_id, **data)


@app.route("/download/<report_id>")
def download(report_id: str) -> Response:
    # Try disk first, then fall back to in-memory
    disk_file = REPORTS_DIR / f"{report_id}.html"
    if disk_file.exists():
        html = disk_file.read_text(encoding="utf-8")
    elif report_id in _report_store:
        html = render_template("report.html", **_report_store[report_id])
    else:
        return Response("Report not found. Please run the analysis again.", status=404)

    # Get metadata for filename
    meta_file = REPORTS_DIR / f"{report_id}.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    else:
        meta = _report_store.get(report_id, {})

    company_slug = str(meta.get("company", "report")).replace(" ", "_").replace("/", "-")
    periods = meta.get("periods", [""])
    filename = f"FinSight_{company_slug}_{periods[0]}.html"
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/reports")
def reports_list() -> str:
    return render_template("reports_list.html", reports=_load_all_meta())


@app.route("/reports/<report_id>/delete", methods=["POST"])
def delete_report(report_id: str):
    _delete_report(report_id)
    return redirect(url_for("reports_list"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
