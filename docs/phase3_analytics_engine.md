# Phase 3 — Core Analytical Engine

**Status:** Draft for student review
**Date:** 2026-10-28

## 1. Purpose of this phase

The analytics engine is the "kitchen" from the Phase 1 architecture. It is plain Python and Pandas code that calculates every business number. It has **no user interface and no AI**, and that separation is deliberate:

- You can test it on its own, with answers worked out on paper.
- In Phase 5 the rule-based interpreter and the LLM interpreter will both call **these same functions**. That keeps the comparison fair, and it means the AI can never produce a number by itself.

## 2. Files

| File | Role |
|------|------|
| `src/analytics/definitions.py` | One place for column names, line types, dataset rules and the written definition of every metric |
| `src/analytics/errors.py` | Error types with messages a user can read (e.g. "Gross profit cannot be calculated: this dataset has no product cost column") |
| `src/analytics/prepare.py` | Turns an uploaded table into a standard transactions table |
| `src/analytics/kpis.py` | Single-number KPIs and the date/country/product/customer filter |
| `src/analytics/breakdowns.py` | Sales by product, country and customer; top/bottom N; trends by day, week or month |
| `src/data/online_retail.py` | Loads the development dataset and removes the duplicated sheet overlap |
| `tests/` | 56 automated tests |

## 3. Key ideas, with small examples

### 3.1 Canonical columns ("one vocabulary inside")

Every uploaded file names its columns differently: `Price`, `UnitPrice`, `Unit Price (£)`. A **mapping** renames them **once**, at the entrance:

```python
ONLINE_RETAIL_II_MAPPING = {"unit_price": "Price", "customer_id": "Customer ID", ...}
df = prepare_transactions(raw, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES)
df["unit_price"]   # always this name, whatever the file called it
```

All later code uses only the internal names. Supporting a new dataset therefore means writing a new mapping, not changing the KPI code. In Phase 4 the user will build this mapping on screen.

### 3.2 Line classification

Every row gets exactly **one** `line_type`. The first rule that matches wins:

| Order | Rule | Line type | Counts towards revenue? |
|-------|------|-----------|-------------------------|
| 1 | Invoice starts with "A" | `accounting_adjustment` | No |
| 2 | Product code is on the non-product list (POST, AMAZONFEE…) | `non_product` | No |
| 3 | Invoice starts with "C" | `cancellation` | Yes (negative) |
| 4 | Quantity > 0 and price > 0 | `sale` | Yes |
| 5 | Quantity ≤ 0 | `stock_adjustment` | No |
| 6 | Anything else (quantity > 0, price ≤ 0) | `zero_price` | No |

Once every row has a class, each KPI becomes simple. For example, net sales = sum of `line_value` where `line_type` is `sale` or `cancellation`. For a dataset without "C" invoices, a negative quantity marks a cancellation instead.

### 3.3 Why the functions take a table, not a date range

Filtering and calculating are separate steps:

```python
feb = kpis.filter_transactions(df, start="2011-02-01", end="2011-02-28")
kpis.net_sales(feb)            # 500,510.33
breakdowns.top_n(feb, "product", n=5)
```

There is one filter function, so every KPI respects date ranges in exactly the same way. **Both dates are inclusive**: `end="2011-02-28"` keeps everything up to 23:59 on 28 February. This is a classic source of off-by-one-day mistakes, and it has its own test.

### 3.4 How the tests work: "Arrange, Act, Assert"

`tests/conftest.py` holds a **13-row dataset I built by hand**. It includes one of every awkward case: a postage line, a duplicate, a cancellation, a missing description, a missing customer, a stock adjustment, a bad-debt entry, a free item, and an invoice with two timestamps. The expected answers were **worked out on paper** and are written at the top of that file. A typical test:

```python
def test_headline_kpis_match_hand_calculation(transactions):   # Arrange: fixture
    assert kpis.net_sales(transactions) == pytest.approx(185)  # Act + Assert
```

`pytest.approx` allows for tiny rounding differences in decimal arithmetic, for example 0.1 + 0.2 = 0.30000000000000004.

## 4. Function reference

### kpis.py

| Function | Returns | Notes |
|----------|---------|-------|
| `filter_transactions(df, start, end, countries, product_ids, customer_ids)` | filtered table | Dates are inclusive. Gives an error if start is after end or a date is invalid. |
| `gross_sales`, `cancellations`, `net_sales` | float | Net sales is the default meaning of "revenue" |
| `order_count`, `units_sold` | int | Orders = distinct invoices with a sale line |
| `average_order_value`, `cancellation_rate` | float or `None` | `None` when there is nothing to divide by |
| `active_customers`, `identified_sales_share`, `repeat_customer_rate` | number | Need the customer column |
| `gross_profit` | float | Raises `MetricUnavailableError` if there is no cost column or a cost is missing |
| `kpi_summary` | dict | All headline KPIs |

### breakdowns.py

| Function | Returns |
|----------|---------|
| `sales_by(df, "product" / "country" / "customer")` | One row per group: net, gross, cancellations, orders, units, share of net sales |
| `top_n(df, dimension, n, metric, bottom)` | Ranked table. Tied values share a rank. "Bottom" ignores groups with no orders. |
| `sales_over_time(df, "day" / "week" / "month")` | One row per period, **including periods with zero sales**, plus an `is_partial` flag |
| `customer_summary(df)` | Per-customer sales with first and last purchase dates |

Weeks run Monday to Sunday.

## 5. Verification results (actual)

```
56 passed in 6.78s, coverage of src/: 99%
```

| Check | Type | Result |
|-------|------|--------|
| 49 unit tests on the 13-row hand-calculated dataset | **Independent** (answers worked out on paper) | All pass |
| 7 tests on the full dataset compared with the Phase 2 figures (rows 1,044,848; net sales £18,981,261.52; top product 22423; Nov 2010/2011; partial Dec 2011; 5,852 customers) | **Consistency** (same author as the EDA script) | All pass |
| Speed: preparing 1,044,848 rows | Measured | About 1.9 s. Each KPI or ranking call takes under 0.35 s. |

**Honest limitation:** the full-dataset tests show that the engine *agrees with* the EDA script. They do not prove that both are right, because I wrote both. To check independently, do the task below by hand.

## 6. Your manual verification task (about 20 minutes, recommended for your report)

Check **February 2011** in Excel without using any Python:

1. Open `data/raw/online_retail_ii/online_retail_II.xlsx` and go to sheet **"Year 2010-2011"**.
2. Add a column `=D2*F2` (Quantity × Price).
3. Filter InvoiceDate to February 2011.
4. Filter out StockCodes `POST, DOT, C2, M, m, D, S, B, BANK CHARGES, AMAZONFEE, CRUK, ADJUST, ADJUST2, TEST001, TEST002, GIFT` and any code starting with `gift_`.
5. **Gross sales:** Invoice does *not* start with "C" or "A", Quantity > 0 and Price > 0. Sum the new column. The engine's answer is **£508,886.20**.
6. **Cancellations:** Invoice starts with "C". Sum the new column. The engine's answer is **−£8,375.87**.

Write down whether your numbers match. That gives your report an independently verified data point. If they **don't** match, tell me the numbers and we'll find out why before going further.

## 7. How to run

```bash
.venv\Scripts\python -m pytest                 # all tests
.venv\Scripts\python -m pytest -m "not dataset" # skip the slower real-data tests
.venv\Scripts\python -m pytest --cov=src         # with coverage
```

## 8. Known limitations and items for later phases

- **Date formats:** text dates are parsed automatically. An ambiguous date such as `03/04/2011` (3 April or 4 March?) will need the user to choose a format in Phase 4. One test shows a warning from Pandas about this.
- **Data-quality report:** profiling (missing-value tables, outlier flags) and the cleaning log belong to Phase 4. This phase provides the building blocks: duplicate flags and line types.
- **No category analysis** for this dataset (there is no category column). `sales_by(df, "category")` gives a clear error.
- **Dataset-specific rules** (the C/A prefixes and the non-product list) live in `ONLINE_RETAIL_RULES`. Other datasets will need their own rules or the default (negative quantity = cancellation).
