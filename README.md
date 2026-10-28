# AI-Powered Business Data Analyst

**Answering natural-language business questions over tabular sales data using validated analytical functions.**

An undergraduate IT capstone project: a web app that lets non-technical users upload sales data, check its quality, and explore key business figures. In a later phase, it will also answer questions in plain English.

The core design rule: **the AI only chooses *what* to calculate; tested Python functions do all the calculating.** Every number on screen comes from the uploaded data under documented business rules. When the data cannot answer a question (for example, profit with no cost data), the app says so instead of guessing.

> **Status: work in progress.** Phases 1–4 of 8 are complete. Plain-English questions, forecasting, reports and the evaluation are still to come (see [Roadmap](#roadmap)).

## Features (current)

- **Upload & map:** accepts CSV and Excel (.xlsx) files, validates them safely and previews them. The app suggests which column is which (invoice, product, quantity, date, price…) and the user confirms.
- **Data quality:** profiles every column and flags missing or unreadable values, duplicates, rows repeated across Excel sheets, and outliers. Cleaning steps are **proposed first and applied only when the user confirms**, with a cleaning log. The original upload is never modified.
- **Dashboard:** KPI cards (net sales, orders, average order value, units, cancellation rate, customers), a sales trend by day, week or month with partial periods marked, top/bottom products, and top countries and customers. Date and country filters apply to every figure.
- **Transparent definitions:** every metric shows the formula it uses.
- **Privacy:** uploaded data stays in the user's browser session only. It is not written to disk and not shared between users.

## Quick start (Windows)

Requires **Python 3.12**.

```bash
git clone https://github.com/Prijesh77/AI-Powered-Business-Data-Analyst.git
cd AI-Powered-Business-Data-Analyst
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

The app opens at http://localhost:8501. Upload your own CSV or .xlsx file, or set up the sample dataset as described below.

On macOS or Linux, use `python3.12 -m venv .venv` and `.venv/bin/...` instead of `.venv\Scripts\...`.

## Sample dataset (optional)

Development and testing use the **UCI Online Retail II** dataset: about 1.07 million transactions from a UK online retailer, December 2009 to December 2011. It is not included in this repository.

1. Download https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip
2. Extract `online_retail_II.xlsx` into `data/raw/online_retail_ii/`
3. Convert it once to a faster format:

   ```bash
   .venv\Scripts\python scripts\convert_online_retail.py
   ```

A **"Use the Online Retail II sample"** button then appears on the Upload page.

> Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D (CC BY 4.0)

## Tests

```bash
.venv\Scripts\python -m pytest                    # all tests
.venv\Scripts\python -m pytest -m "not dataset"   # skip tests that need the sample dataset
```

The core KPI tests use a small hand-made dataset whose expected answers were worked out on paper (see `tests/conftest.py`). Other tests check that every chart shows exactly the values in its table.

## Project structure

```
app.py                 Streamlit entry point
pages/                 Home, Upload & map, Data quality, Dashboard
src/analytics/         KPI engine: definitions, preparation, KPIs, breakdowns (no UI, no AI)
src/data/              File loading, column mapping, profiling, cleaning
src/visualization/     Plotly charts
scripts/               Dataset conversion, exploratory analysis, command-line demo
tests/                 Automated tests
docs/                  Phase documents, project log, exploratory analysis outputs
```

## Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| 1 | Proposal and planning | ✅ Done |
| 2 | Data exploration | ✅ Done |
| 3 | Core analytics engine | ✅ Done |
| 4 | Web app: upload, data quality, dashboard | ✅ Done |
| 5 | Plain-English questions (rule-based, then a free local LLM) | Planned |
| 6 | Weekly sales forecasting against a seasonal-naïve baseline | Planned |
| 7 | Benchmark evaluation, usability study, Excel/PDF reports | Planned |
| 8 | Deployment and final documentation | Planned |

Design decisions, known issues and progress are recorded in [docs/project_log.md](docs/project_log.md). Each phase has its own document in [docs/](docs/).

## Known limitations

- Only `.csv` and `.xlsx` files are supported, up to 50 MB.
- Refreshing the browser page clears the loaded data, because data is kept private to each session.
- Online Retail II has no product category or cost columns, so category and profit analyses are not available for it.

## Author

[Prijesh77](https://github.com/Prijesh77): undergraduate IT capstone project.
