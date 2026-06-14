"""Extract financial statement data from a PDF using the Claude API."""
from __future__ import annotations

import base64
import json
import re

import anthropic

EXTRACTION_PROMPT = """You are a financial data extraction assistant. Extract the financial statement data from this annual report or 10-K and return it as a single JSON object.

Rules:
- Extract TWO fiscal periods: the most recent (current) and the prior year (prior)
- All monetary values in MILLIONS USD. Convert if needed: thousands → divide by 1000; billions → multiply by 1000
- Capital Expenditures and Treasury Stock must be POSITIVE numbers (absolute values)
- Diluted EPS is a per-share value, NOT scaled to millions
- Shares Outstanding can stay in millions of shares
- If a line item is not in the report, use 0.0
- Return ONLY the JSON — no explanation, no markdown fences

{
  "company_name": "...",
  "current_period": "FY2024",
  "prior_period": "FY2023",
  "balance_sheet": {
    "Cash & Marketable Securities": {"current": 0.0, "prior": 0.0},
    "Accounts Receivable": {"current": 0.0, "prior": 0.0},
    "Inventory": {"current": 0.0, "prior": 0.0},
    "Total Current Assets": {"current": 0.0, "prior": 0.0},
    "Property, Plant & Equipment (PP&E)": {"current": 0.0, "prior": 0.0},
    "Goodwill": {"current": 0.0, "prior": 0.0},
    "Intangible Assets": {"current": 0.0, "prior": 0.0},
    "Total Assets": {"current": 0.0, "prior": 0.0},
    "Accounts Payable": {"current": 0.0, "prior": 0.0},
    "Accrued Expenses": {"current": 0.0, "prior": 0.0},
    "Short-term Debt": {"current": 0.0, "prior": 0.0},
    "Operating Lease Liabilities": {"current": 0.0, "prior": 0.0},
    "Total Current Liabilities": {"current": 0.0, "prior": 0.0},
    "Long-term Debt": {"current": 0.0, "prior": 0.0},
    "Total Liabilities": {"current": 0.0, "prior": 0.0},
    "Preferred Stock": {"current": 0.0, "prior": 0.0},
    "Retained Earnings": {"current": 0.0, "prior": 0.0},
    "Treasury Stock (cumulative buybacks)": {"current": 0.0, "prior": 0.0},
    "Total Shareholders' Equity": {"current": 0.0, "prior": 0.0}
  },
  "income_statement": {
    "Revenue": {"current": 0.0, "prior": 0.0},
    "Cost of Goods Sold (COGS)": {"current": 0.0, "prior": 0.0},
    "Gross Profit": {"current": 0.0, "prior": 0.0},
    "Research & Development (R&D)": {"current": 0.0, "prior": 0.0},
    "Sales & Marketing (S&M)": {"current": 0.0, "prior": 0.0},
    "General & Administrative (G&A)": {"current": 0.0, "prior": 0.0},
    "Total Operating Expenses": {"current": 0.0, "prior": 0.0},
    "Operating Income (EBIT)": {"current": 0.0, "prior": 0.0},
    "Interest Expense": {"current": 0.0, "prior": 0.0},
    "Earnings Before Taxes (EBT)": {"current": 0.0, "prior": 0.0},
    "Income Tax Expense": {"current": 0.0, "prior": 0.0},
    "Net Income": {"current": 0.0, "prior": 0.0},
    "Shares Outstanding": {"current": 0.0, "prior": 0.0},
    "Diluted EPS": {"current": 0.0, "prior": 0.0}
  },
  "cash_flow": {
    "Net Income": {"current": 0.0, "prior": 0.0},
    "Depreciation & Amortization (D&A)": {"current": 0.0, "prior": 0.0},
    "Stock-Based Compensation (SBC)": {"current": 0.0, "prior": 0.0},
    "Changes in Working Capital": {"current": 0.0, "prior": 0.0},
    "Operating Cash Flow (OCF)": {"current": 0.0, "prior": 0.0},
    "Capital Expenditures (CapEx)": {"current": 0.0, "prior": 0.0},
    "Free Cash Flow (FCF)": {"current": 0.0, "prior": 0.0},
    "Cash from Investing": {"current": 0.0, "prior": 0.0},
    "Cash from Financing": {"current": 0.0, "prior": 0.0},
    "Net Change in Cash": {"current": 0.0, "prior": 0.0}
  }
}"""


def extract_financials(pdf_bytes: bytes) -> dict:
    """Send PDF to Claude API and return structured financial data."""
    client = anthropic.Anthropic()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
