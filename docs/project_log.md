# Project Log

Running record of progress, decisions, and known issues. Updated at the end of every phase.

## Current phase

**Phase 4 — Initial application** (awaiting student review)

## Completed

- [x] Phase 1: proposal and planning (`docs/phase1_proposal.md`), approved 2026-10-28
- [x] Phase 2: downloaded Online Retail II, verified the real schema, ran the EDA script, documented the data dictionary, quality issues, cleaning rules and KPI definitions (`docs/phase2_data_exploration.md`), approved 2026-10-28
- [x] Python 3.12 virtual environment (`.venv`), `requirements.txt`, `.gitignore`, local Git repository
- [x] Phase 3: `src/analytics` (definitions, preparation, KPIs, breakdowns), `src/data/online_retail.py`, 56 tests passing with 99% coverage (`docs/phase3_analytics_engine.md`), approved 2026-10-28
- [x] `scripts/demo_analytics.py`: command-line demo of the engine
- [x] Phase 4: Streamlit app (upload & map, data quality with reviewable cleaning, dashboard), 101 tests passing with 96% coverage, checked manually in the browser with the real data (`docs/phase4_application.md`)

## Remaining

- [ ] Student review of Phase 4
- [ ] Student's manual Excel check of February 2011 (Phase 3 doc, section 6)
- [ ] Verify every literature source before citing
- [ ] First Git commit (nothing committed yet)
- [ ] Phase 5: AI integration (rule-based interpreter first, then a free local LLM)
- [ ] Phase 6: advanced feature (forecasting)
- [ ] Phase 7: testing and evaluation
- [ ] Phase 8: deployment and documentation

## Decisions

| Date | Decision | Reason | Status |
|------|----------|--------|--------|
| 2026-10-28 | Title 1; Online Retail II; forecasting as the advanced module | Student approved the Phase 1 recommendations | Approved |
| 2026-10-28 | LLM selects functions; Python computes all numbers | Prevents fabricated figures | Approved |
| 2026-10-28 | Two interpreters (rule-based + LLM) over one function catalogue | Fair comparison; free offline fallback | Approved |
| 2026-10-28 | Streamlit only, no FastAPI initially; SQLite for logs | Simplicity | Approved |
| 2026-10-28 | Accept .csv and .xlsx only | Avoid macro-enabled or legacy formats | Approved |
| 2026-10-28 | Cache the Excel file as Parquet | Excel loads in about 1 min, Parquet in about 1 s | Done |
| 2026-10-28 | Drop the 2009-2010 sheet's copy of 1–9 Dec 2010 | Verified exact copy of 22,523 rows | Approved |
| 2026-10-28 | "Revenue" = net product sales (sales + cancellations, product codes only) | Gross ranking is distorted by cancelled bulk orders | Approved |
| 2026-10-28 | Explicit non-product code list, not a regex | A regex would wrongly drop real DCGS… products | Approved |
| 2026-10-28 | Keep exact duplicate lines by default; flag them | Cannot tell errors from legitimate repeats (impact 0.28%) | Approved |
| 2026-10-28 | Flag outliers, never auto-remove | The IQR rule flags 8% of lines, mostly normal wholesale orders | Approved |
| 2026-10-28 | Weekly forecasting, partial periods excluded | Only 24 full months of data | Approved |
| 2026-10-28 | Canonical column names plus a mapping, applied once at load time | KPI code stays independent of any dataset | Done |
| 2026-10-28 | Each row gets exactly one line type; KPIs sum by line type | One clear rule per KPI; easy to explain and test | Done |
| 2026-10-28 | Filters are separate from KPIs; end dates are inclusive | Same filter behaviour for every KPI | Done |
| 2026-10-28 | Product name = most common description per code | Staff notes ("wrongly coded…") pollute descriptions | Done |
| 2026-10-28 | Trend tables include zero-sales periods and an is_partial flag | Needed for honest charts and for forecasting | Done |
| 2026-10-28 | LLM for Phase 5 = free local model (no paid API) | Student's choice: no API cost; data stays on the machine | Approved |
| 2026-10-28 | No ethics approval required by the college | Student confirmed; informed consent forms still used for the usability study | Approved |
| 2026-10-28 | Data kept in per-session memory; no st.cache_data for uploads | Session isolation and privacy (cost: page refresh loses data) | Done |
| 2026-10-28 | Cross-sheet repeats detected generically, one copy for one copy | Replaces the dataset-specific overlap rule; finds the same 22,523 rows | Done |
| 2026-10-28 | Cleaning is proposed first, applied only on the user's click, with a log | Brief: users review cleaning; original data preserved | Done |
| 2026-10-28 | Charts are built only from analytics tables; tests compare chart values with the tables | Chart/table consistency (an evaluation criterion) | Done |

## Known issues / limitations

- Online Retail II has no product category or cost columns, so category and profit questions cannot be answered directly.
- The UCI documentation's column names differ from the actual file (InvoiceNo/Invoice, UnitPrice/Price, CustomerID/Customer ID).
- 22.5% of rows have no Customer ID, so customer analyses cover only 86.9% of gross product sales.
- December 2011 is a partial month (8 trading days).
- Windows Smart App Control blocked pandas 3.1.0, so pandas is pinned to 3.0.3.
- Ambiguous text dates (e.g. 03/04/2011): handled with a "day first" option on the upload page; the user must choose it.
- Refreshing the browser page starts a new session, so the data must be loaded again.
- The 45 MB Excel file takes about 56 s to read; each dashboard interaction takes about 1–3 s on 1 million rows.
- Exports must escape cells starting with = + - @ (formula injection) when added in the reporting phase.
- The full-dataset tests check consistency with the EDA script, not independent correctness (both written by the same author).
