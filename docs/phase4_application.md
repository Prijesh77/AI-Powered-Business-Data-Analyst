# Phase 4 — Initial Application

**Status:** Draft for student review
**Date:** 2026-10-28

## 1. Purpose of this phase

This phase builds the first version you can open in a browser. Users can upload a file, map its columns, review data-quality problems, choose cleaning steps and explore a dashboard. All numbers come from the Phase 3 engine; this phase adds screens around it. There is still no AI: that is Phase 5.

## 2. How to run it

```bash
.venv\Scripts\streamlit run app.py
```

The app opens at http://localhost:8501. On the **Upload & map** page, click **"Use the Online Retail II sample"** to load the development dataset instantly. Uploading the 45 MB Excel file also works, but takes about one minute to read.

## 3. New concepts

### 3.1 How Streamlit works

A Streamlit page is an ordinary Python script. **Every time the user clicks or types, Streamlit runs the script again from top to bottom.** A widget such as `st.selectbox(...)` returns the current value, so the code reads like a normal script:

```python
freq = st.selectbox("Trend by", ["month", "week", "day"])   # returns the user's choice
trend = breakdowns.sales_over_time(selected, freq)          # recalculated on every rerun
st.plotly_chart(sales_trend(trend, freq))
```

### 3.2 Session state and privacy

Variables vanish on each rerun. Anything that must survive, such as the uploaded table, is kept in `st.session_state`, which works like a dictionary. **Each browser tab gets its own session state**, so one user's data cannot appear in another user's session. All the key names are listed in `src/ui_state.py`.

I deliberately did **not** use `st.cache_data` for uploads, because that cache is shared by all users of the server. The trade-off is that **refreshing the page (F5) starts a new session and the data has to be loaded again**. Use the links in the sidebar to move between pages.

### 3.3 Review before cleaning

Cleaning happens in two steps:
1. `propose_cleaning()` *counts* what each step would affect. Nothing changes yet.
2. The user ticks or unticks optional steps, then `apply_cleaning()` builds a cleaned **copy** and returns a **cleaning log**.

The uploaded table in session state is never modified. A test checks this (`test_original_upload_is_not_modified`).

### 3.4 Repeated rows across sheets: a general version of the Phase 2 fix

In Phase 2, the overlap between the two sheets was removed with a rule written for this dataset only. The app now detects it **for any workbook**: a row in a later sheet counts as a repeat if the same row already appears in an earlier sheet. Copies are matched **one for one**. If a line appears twice in sheet 1 and twice in sheet 2, both sheet-2 copies are repeats. If it appears once in sheet 1 and twice in sheet 2, one sheet-2 copy is kept.

On the real workbook this finds **exactly 22,523 rows**, the same number Phase 2 found by hand, and net sales come out at the same **£18,981,261.52**.

## 4. Files added

| File | Role |
|------|------|
| `app.py` | Entry point; defines the four pages and their order |
| `pages/home.py` | Introduction, current data status, privacy note |
| `pages/upload.py` | Upload, preview, column mapping, business rules, currency, date format |
| `pages/data_quality.py` | Column profile, invalid values, cleaning steps for review, cleaning log, quality indicators, outliers |
| `pages/dashboard.py` | Filters, KPI cards, trend, products, countries, customers, metric definitions |
| `src/data/loader.py` | Safe file reading (type, size, signature, encoding and delimiter detection, sheet combining) |
| `src/data/mapping.py` | Column-mapping suggestions and checks; business-rule presets |
| `src/data/profiling.py` | Data-quality descriptions (changes nothing) |
| `src/data/cleaning.py` | Proposed cleaning steps and the cleaning log |
| `src/visualization/charts.py` | Plotly charts drawn directly from analytics tables |
| `src/ui_state.py` | Session-state keys and small UI helpers |
| `.streamlit/config.toml` | 50 MB upload limit; Streamlit usage statistics switched off |
| `.claude/launch.json` | Lets the Claude app's browser pane start the app |

Small change to Phase 3 code: `prepare.py` now has a `dayfirst` option for text dates, and shares its conversion functions with the profiler.

## 5. Security measures in this phase

| Measure | Where |
|---------|-------|
| Only `.csv` and `.xlsx` accepted; `.xlsm`, `.xls` and anything else rejected | `validate_upload` |
| A `.xlsx` must really be a zip archive; it is rejected if it expands to more than 500 MB (protects against "zip bombs") | `validate_upload` |
| CSV files containing binary data are rejected | `validate_upload` |
| 50 MB file limit and 2,000,000 row limit | `loader.py`, `.streamlit/config.toml` |
| File contents are only parsed, never executed. openpyxl ignores macros and reads stored values instead of recalculating formulas. | `loader.py` |
| Parsing errors become friendly messages instead of stack traces | `read_upload` |
| Data kept in per-session memory only; nothing written to disk; no shared cache | `ui_state.py` |
| Streamlit usage statistics switched off | `config.toml` |

## 6. Verification (actual results)

```
101 passed in 11.27s, coverage of src/: 96%
```

| Check | Result |
|-------|--------|
| 13 file-upload tests (bad types, fake Excel, binary CSV, size and row limits, malformed CSV, `;` delimiter, Windows encoding, combining sheets) | Pass |
| 6 column-mapping tests (Online Retail names and generic names such as "Order ID", "SKU", "Qty") | Pass |
| 13 cleaning/profiling tests (one-for-one sheet repeats, invalid rows, duplicate choice, original data unchanged) | Pass |
| 4 chart tests: **each chart shows exactly the values in its table** | Pass |
| 6 app smoke tests (every page renders; a full click-through gives net sales of GBP 185.00 on the hand-made data) | Pass |
| Manual run in a browser with the real data (1,067,371 rows loaded → 1,044,848 after cleaning) | Net sales GBP 18,981,261.52, 39,516 orders, AOV GBP 498.56, 5,852 customers. All match Phase 2/3. |
| Real 45 MB workbook through the upload code | 2 sheets combined, 22,523 repeats found, about 56 s to read |

**Two bugs found during the manual browser check, both fixed:**
1. Customer IDs such as "18102" were drawn on a *numeric* axis (13k–18k) instead of as labels. Fixed by forcing a category axis; a test was added.
2. KPI cards were cut off ("GBP …") in a narrow window. They now sit in two rows of three.

## 7. Known limitations

- **Refreshing the page loses the data** (see 3.2). This is the cost of keeping data private to each session.
- **Large Excel files are slow** (about 1 minute for 45 MB) because reading .xlsx is slow in Python. CSV files of the same data load much faster.
- **Each click recalculates on the full table.** That takes about 1–3 s on 1 million rows. It is acceptable for a prototype; caching per session could be added later if needed.
- **Column mapping and business rules are not saved** between sessions, so you set them up again for each upload.
- **No category chart** for Online Retail II, because the dataset has no category column.
- **Exports** (Excel/PDF reports, a downloadable cleaning log) come in the reporting phase. When exporting, cell values beginning with `=`, `+`, `-` or `@` will need escaping to prevent "CSV/formula injection" in Excel.

## 8. What to try

1. Load the sample, keep the default cleaning steps, and open the dashboard.
2. Change **Trend by** to *week*: partial weeks appear as hollow markers.
3. Filter **Countries** to *France*, then switch Products to **Bottom**.
4. Go back to Data quality, tick **"Remove exact duplicate lines"**, rebuild, and watch net sales change by about £54k (0.28%), as predicted in Phase 2.
5. Upload a small CSV of your own. Try a file with the wrong extension, or with text in the price column, to see the error messages.
