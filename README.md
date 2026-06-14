# FinSight CLI

A terminal financial-analysis suite with three modules that share an in-memory
company profile within a session:

- **3-Statement Analyzer** — period-over-period $ and % change with balance and
  FCF integrity checks. Saves the company to the session.
- **Buffett Moat Scanner** — the 14 Rules of Thumb with a Moat Durability Score.
- **Rule of 40 Dashboard** — growth + margin health for SaaS businesses.

Enter a company once in Module 1, then Modules 2 and 3 offer to reuse the figures.

## Setup

```
pip install -r requirements.txt
python main.py
```

Jump to a module directly: `python main.py -m 2`
