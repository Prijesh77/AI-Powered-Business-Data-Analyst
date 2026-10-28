# Phase 2 — Data Exploration

**Dataset:** UCI Online Retail II
**Status:** Draft for student review
**Date:** 2026-10-28

Every number in this document comes from running `scripts/eda_online_retail.py` on the real file. The full output is in [eda/eda_output.txt](eda/eda_output.txt), and the CSV tables are in [eda/](eda/). To reproduce it:

```bash
python scripts/convert_online_retail.py
python scripts/eda_online_retail.py > docs/eda/eda_output.txt
```

---

## 1. Source and citation

| Item | Value |
|------|-------|
| Source | UCI Machine Learning Repository, dataset 502 |
| Citation (as given by UCI) | Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D |
| Licence | CC BY 4.0. Reuse is allowed if you give attribution. |
| UCI description | All transactions of a UK-based, non-store online retailer from 01/12/2009 to 09/12/2011. The company sells mainly all-occasion gift-ware, and many of its customers are wholesalers. |
| File downloaded | `online_retail_II.xlsx`, 45.6 MB, 2 sheets |
| Local copy | `data/raw/online_retail_ii/` (kept out of Git), converted to `data/processed/online_retail_ii.parquet` |

**Why convert to Parquet?** Reading the Excel file takes about one minute. Parquet is a compressed column-based file format that Pandas loads in about a second, and it keeps the column types. The original Excel file is never changed.

---

## 2. Actual schema compared with the documentation

**Lesson:** the documentation and the actual file use different column names. If our code had trusted the documentation, it would fail with `KeyError: 'UnitPrice'`. This is why we inspect the real file before writing code, and why Phase 4 needs a column-mapping step.

| Column in file | Name in UCI docs | Pandas type | Meaning | Observed facts |
|----------------|------------------|-------------|---------|----------------|
| `Invoice` | InvoiceNo | text | Invoice or transaction number. A "C" prefix means a cancellation. | 53,628 distinct values. There are also 6 invoices with an "A" prefix, which the docs do not mention (see §4.4). |
| `StockCode` | StockCode | text | Product code | 5,305 distinct codes. The docs say "5-digit", but 63 codes are not (e.g. `POST`, `85123A`, `DCGS0058`). |
| `Description` | Description | text | Product name | 4,275 missing values. 1,232 codes have more than one description. |
| `Quantity` | Quantity | integer | Units on this invoice line | Ranges from −80,995 to 80,995. Negative values appear on cancellations and stock adjustments. |
| `InvoiceDate` | InvoiceDate | datetime (to the minute) | When the invoice was created | Runs from 2009-12-01 07:45 to 2011-12-09 12:50. The time zone is not stated, so we assume UK local time. |
| `Price` | UnitPrice | decimal | Price per unit in **pounds sterling (£)** | 6,024 rows have a price of zero and 5 rows have a negative price. |
| `Customer ID` | CustomerID | number (stored as float) | Customer identifier | 22.5% are missing. All values are whole numbers, so store them as **text IDs**, not numbers. |
| `Country` | Country | text | Country where the customer lives | 43 values, 91.9% of them UK. Includes `Unspecified`, `European Community` and `West Indies`. |

**Granularity:** one row is **one invoice line**, meaning one product on one invoice. It is not one order. Orders must be counted as *distinct invoices*. An invoice has a median of 9 lines and a maximum of 1,114.

**Single currency:** all prices are in pounds sterling, so the app does not need currency conversion for this dataset. It should still display "£" and record the currency in reports.

**No product categories, no costs:** this confirms what Phase 1 assumed. The app cannot calculate profit or category performance from this dataset.

---

## 3. What exploratory data analysis (EDA) means here

EDA is "getting to know the data before trusting it". For each column we ask:
1. Does it match the documentation?
2. What values look impossible or suspicious?
3. How would each problem change a business answer?

The third question matters most. For example, a few negative quantities might look harmless, but §5 shows they change total revenue by about £700,000.

---

## 4. Data-quality findings

### 4.1 The two sheets overlap: an exact copy of 9 days

| Fact | Value |
|------|-------|
| Sheet "Year 2009-2010" | 2009-12-01 to **2010-12-09** |
| Sheet "Year 2010-2011" | **2010-12-01** to 2011-12-09 |
| Rows from 1–9 Dec 2010 in each sheet | 22,523 in each |
| Identical row for row? | **Yes** |

If we stacked both sheets naively, every sale from 1–9 Dec 2010 would be counted twice. **Rule:** drop the rows dated on or after 2010-12-01 from the 2009-2010 sheet. That leaves **1,044,848 rows**.

### 4.2 Exact duplicate lines within the data

- **11,812 rows (1.13%)** are exact copies of another row: same invoice, product, quantity, price, minute and customer. They appear on 4,387 invoices.
- Example: invoice 489517 has "SET OF THREE VINTAGE GIFT WRAPS ×1 @ £1.95" twice in the same minute.
- **We cannot tell** whether this is a data-entry duplicate or a customer genuinely adding the same item twice. Your project brief says not to delete legitimate repeated transactions automatically.
- **Impact:** removing them would lower net product sales by **£53,862 (0.28%)**, from £18,981,261.52 to £18,927,399.07.
- **Rule:** **keep them by default**, flag them on the Data Quality page, and let the user choose whether to remove them.

### 4.3 Missing values

| Column | Missing | % | Meaning and treatment |
|--------|---------|---|------------------------|
| `Customer ID` | 235,287 | 22.52% | Probably guest or unregistered purchases. **Keep these rows** for revenue and order KPIs, because the sales really happened. Exclude them only from customer-level analysis, and tell the user so. Rows with a Customer ID account for 86.9% of gross product sales. |
| `Description` | 4,275 | 0.41% | Most are zero-price stock adjustments. Fill missing names from the most common description for the same StockCode. |

### 4.4 Invoice types

| Type | Rows | What it is |
|------|------|-----------|
| Normal (digits only) | 1,025,677 | Sales. Also includes 3,393 stock adjustments (see §4.5). |
| `C…` (cancellation) | 19,165 | Cancelled or returned lines. All but one have a negative quantity. |
| `A…` (adjustment) | 6 | "Adjust bad debt", stock code `B`, worth up to −£53,594 each. These are accounting entries, not sales. |

### 4.5 Negative quantities on normal invoices are stock adjustments

There are 3,393 rows with a negative quantity on a normal invoice. **Every one of them** has a price of £0 and no customer. Their descriptions are notes such as "damages", "check", "missing", "smashed" or "thrown away", or are blank. They record warehouse adjustments, not sales. Their price is zero, so they add £0 to revenue, but they **would** distort unit-quantity totals. **Rule:** exclude them from sales.

### 4.6 Codes that are not products

The UCI docs describe 5-digit product codes. In the data, 63 codes break that pattern, so I reviewed each one by hand ([eda/nonstandard_stockcodes.csv](eda/nonstandard_stockcodes.csv)):

| Treated as **non-product** (5,812 rows) | Treated as product |
|------------------------------------------|---------------------|
| `POST`, `DOT` (postage), `C2` (carriage), `M`/`m` (manual), `D` (discount), `S` (samples), `B` (bad debt), `BANK CHARGES`, `AMAZONFEE`, `CRUK` (charity commission), `ADJUST`, `ADJUST2`, `TEST001`, `TEST002`, `GIFT`, `gift_0001_*` (gift vouchers) | `85123A`-style variants, `DCGS…` (web-shop items such as "MISO PRETTY GUM"), `SP1002`, `47503J`, `PADS` |

A regular expression alone would have been wrong, because it would have thrown away real `DCGS…` products. That is why the app will use an **explicit, documented list**. Some fees are very large: the AMAZONFEE lines net to about −£221,521.

### 4.7 Extreme values: two very large orders that were cancelled

| Product | Order | Cancellation |
|---------|-------|--------------|
| PAPER CRAFT, LITTLE BIRDIE | 80,995 units @ £2.08 (invoice 581483, 2011-12-09 09:15) | −80,995 units (C581484, 12 minutes later) |
| MEDIUM CERAMIC TOP STORAGE JAR | 74,215 units @ £1.04 (541431, 2011-01-18) | −74,215 units (C541433, 16 minutes later) |

These look like data-entry mistakes that were corrected straight away. Section 5.2 shows they change a "top product" answer completely.

### 4.8 Outliers: why we only flag them

- Under the usual IQR rule (above Q3 + 1.5×IQR, which is £38.40 per line), **81,186 sale lines (8.0%)** count as outliers.
- In a wholesale business, many of those are ordinary large orders, so deleting them would be wrong.
- A stricter rule, |z| > 3 on log₁₀(line value), flags 5,320 lines.
- **Rule:** outliers are **flagged for review and never removed automatically**. This matches the brief.

### 4.9 Smaller issues

- **83 invoices** have more than one timestamp, but never more than 9 minutes apart. We use the earliest time as the invoice date.
- Every invoice has exactly one customer and one country. Good: no conflicts.
- **1,232 stock codes** have more than one description, often staff notes such as "wrongly coded 23343". Use the most common description as the official product name.
- **Partial months:** December 2011 has only **8 trading days**. Showing it as a normal month would look like a collapse in sales. It must be labelled partial and left out of forecasting.

---

## 5. Why business rules matter: one question, seven answers

**"What is the total revenue?"** has a different answer under each rule:

| Rule | Revenue (£) |
|------|-------------|
| A. Sum of Quantity × Price over the raw workbook (includes overlap) | 19,287,250.57 |
| B. Same, after removing the sheet overlap | 18,909,762.12 |
| C. Sale lines only (normal invoice, Qty > 0, Price > 0), all codes | 20,522,679.86 |
| D. **Gross product sales**: C, product codes only | **19,700,954.46** |
| E. Value of cancelled products (C-invoices) | −719,692.94 |
| F. **Net product sales**: D + E | **18,981,261.52** |
| G. Sensitivity check: F with within-file duplicates removed | 18,927,399.07 |

The highest and lowest answers differ by about **£1.6 million (8%)**. This is the strongest argument in the project for **why an LLM must not calculate answers freely**: the "right" number depends on explicit business rules. The app must show which rule it used.

### 5.2 Gross ranking compared with net ranking

| Product | Gross rank | Net rank |
|---------|-----------|----------|
| REGENCY CAKESTAND 3 TIER | 1 | 1 |
| PAPER CRAFT, LITTLE BIRDIE | **4** | **4,877** (net £0.00) |
| MEDIUM CERAMIC TOP STORAGE JAR | **8** | **1,013** |

**Decision:** "revenue" in the app means **net product sales** (rule F) by default. Gross sales and cancellations are shown as separate KPIs.

---

## 6. First business insights (descriptive only)

These are observations from the data, not causal claims.

- **Strong seasonality.** Monthly net sales rise from about £0.5–0.7M in spring to a peak in November: **£1,400,559 in Nov 2010** and **£1,432,735 in Nov 2011**. That fits a gift-ware seller with a Christmas trade.
- **Customer concentration.** Among 5,852 identified customers, the top 10% (585) account for **63.8%** of identified gross product sales. **27.6%** of customers ordered only once.
- **Cancellations** amount to **3.65%** of gross product sales by value.
- **Geography.** 91.9% of rows are from the UK. Next come EIRE, Germany and France.
- **Top products by net sales:** Regency Cakestand 3 Tier (£314,513), White Hanging Heart T-Light Holder (£248,679), Jumbo Bag Red Retrospot (£178,719).

Monthly figures: [eda/monthly_sales.csv](eda/monthly_sales.csv). Product figures: [eda/product_sales.csv](eda/product_sales.csv).

---

## 7. Proposed cleaning rules (for Phase 3/4)

These rules **do not modify the original data**. The app builds a cleaned *view* of it and records each rule in the cleaning log. The user approves every rule shown as optional.

| # | Rule | Default | User can change? |
|---|------|---------|------------------|
| R1 | Remove the 2009-2010 sheet's copy of 1–9 Dec 2010 (dataset-specific) | On | No. It is a confirmed exact copy. |
| R2 | Store Customer ID as text; missing stays missing | On | No |
| R3 | Classify each line as `sale`, `cancellation`, `stock_adjustment` (normal invoice with Qty ≤ 0 or Price = 0), `bad_debt` (A-invoice) or `non_product` (code list) | On | Can edit the non-product code list |
| R4 | Fill missing descriptions with the most common description for that StockCode | On | Yes |
| R5 | Remove exact duplicate lines | **Off** (flag only) | Yes |
| R6 | Flag outliers | Flag only | Can choose the method |
| R7 | Mark the last month as partial if it has fewer trading days than usual | On | No |

---

## 8. KPI definitions (draft)

All KPIs are calculated on the cleaned view and a **date range the user chooses**. Each KPI also says which line classes it includes.

| KPI | Definition / formula | Lines included | Notes |
|-----|----------------------|----------------|-------|
| **Line value** | `Quantity × Price` | — | The basic calculation used by the others |
| **Gross product sales** | Σ line value | `sale` | |
| **Cancellations** | Σ line value (negative) | `cancellation` with a product code | Dated by the cancellation date, which may fall in a later month than the original sale |
| **Net product sales ("Revenue")** | Gross product sales + Cancellations | | **Default meaning of "revenue"** |
| **Orders** | Count of *distinct* `Invoice` | `sale` | Never a row count |
| **Average order value (AOV)** | Gross product sales ÷ Orders | `sale` | Uses gross on purpose, so the numerator and the order count cover the same invoices |
| **Units sold** | Σ Quantity | `sale` | |
| **Cancellation rate** | −Cancellations ÷ Gross product sales | | |
| **Sales by product / country / period** | Net product sales grouped by StockCode / Country / month or week | | Product name = most common description |
| **Top / bottom N products** | Rank by net product sales (or units, if the user asks) | | Ties share a rank. "Bottom" only counts products sold in the period. |
| **Active customers** | Distinct non-missing `Customer ID` | `sale` | States the share of sales with no customer ID |
| **Revenue per customer** | Σ net product sales per Customer ID | | Identified customers only |
| **Repeat-customer rate** | Customers with ≥ 2 orders ÷ active customers | | |
| **Gross profit** | Revenue − Cost of goods sold | — | **Not available for this dataset** (no cost column). The app must say so. |
| **Category sales** | — | — | **Not available** (no category column) unless the user uploads a mapping |

**Not calculated:** postage, fees and bad debt are left out of product revenue but can be reported separately as "non-product amounts".

---

## 9. Implications for later phases

- **Phase 3 (analytics engine):** implement R1–R7 and the KPIs above. Write tests with a small hand-made file that contains a cancellation, a duplicate line, a stock adjustment, a POST line and a missing customer, so the expected answers can be worked out on paper.
- **Phase 4 (app):** the column-mapping step is essential, because the documentation names did not match the file.
- **Phase 5 (AI):** the explanation shown with an answer must state the revenue definition used. Example benchmark questions with an expected **clarification** reply: "total revenue including postage?" and "top product by quantity or by revenue?"
- **Phase 6 (forecasting):** there are 24 full months (Dec 2009 – Nov 2011) plus a partial Dec 2011. That is too few for a reliable monthly model with yearly seasonality, since the model sees each month only twice. **Recommendation:** forecast **weekly** net sales (about 104 weeks). Compare against a seasonal-naïve baseline (same week last year) and a naïve baseline, and drop the partial final week.

---

## 10. Questions for you

1. Do you agree that **"revenue" should mean net product sales** (rule F) by default?
2. Should within-file duplicates be **kept by default** (my recommendation) or removed by default?
3. Are you happy with **weekly** forecasting instead of monthly?
