"""Exploratory data analysis (EDA) of UCI Online Retail II.

Prints facts about the raw data and saves summary tables to docs/eda/.
Every number in docs/phase2_data_exploration.md comes from the output of
this script (saved as docs/eda/eda_output.txt).

Usage:
    python scripts/convert_online_retail.py   # once
    python scripts/eda_online_retail.py > docs/eda/eda_output.txt
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_FILE = Path("data/processed/online_retail_ii.parquet")
OUT_DIR = Path("docs/eda")

DATA_COLUMNS = ["Invoice", "StockCode", "Description", "Quantity",
                "InvoiceDate", "Price", "Customer ID", "Country"]

# The workbook's two sheets both contain 2010-12-01 .. 2010-12-09.
OVERLAP_SHEET = "Year 2009-2010"
OVERLAP_START = pd.Timestamp("2010-12-01")

# Stock codes that are services, fees, adjustments or vouchers, not
# merchandise. Built by reviewing every code that is not "5 digits +
# optional letters" (see nonstandard_stockcodes.csv). Codes such as
# DCGS0058 or SP1002 look unusual but are real products, so they stay.
NON_PRODUCT_CODES = {
    "POST", "DOT", "C2", "M", "m", "D", "S", "B", "BANK CHARGES", "AMAZONFEE",
    "CRUK", "ADJUST", "ADJUST2", "TEST001", "TEST002", "GIFT",
}
NON_PRODUCT_PREFIXES = ("gift_",)
STANDARD_CODE_PATTERN = r"^\d{5}[A-Za-z]{0,2}$"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def is_product_code(codes: pd.Series) -> pd.Series:
    return ~(codes.isin(NON_PRODUCT_CODES) | codes.str.startswith(NON_PRODUCT_PREFIXES))


def main() -> None:
    raw = pd.read_parquet(DATA_FILE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 140)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_rows", 100)

    section("1. Shape and types (raw workbook, both sheets)")
    print(f"Rows: {len(raw):,}   Columns: {raw.shape[1]}")
    print(raw.dtypes)
    print(raw[DATA_COLUMNS].head(5))

    section("2. Date range per sheet")
    print(raw.groupby("SourceSheet")["InvoiceDate"].agg(["min", "max", "count"]))

    section("3. Overlap between sheets")
    in_overlap_1 = (raw["SourceSheet"] == OVERLAP_SHEET) & (raw["InvoiceDate"] >= OVERLAP_START)
    in_overlap_2 = (raw["SourceSheet"] != OVERLAP_SHEET) & (raw["InvoiceDate"] < "2010-12-10")
    h1 = pd.util.hash_pandas_object(raw.loc[in_overlap_1, DATA_COLUMNS], index=False).value_counts()
    h2 = pd.util.hash_pandas_object(raw.loc[in_overlap_2, DATA_COLUMNS], index=False).value_counts()
    print(f"Rows dated >= 2010-12-01 in '{OVERLAP_SHEET}': {in_overlap_1.sum():,}")
    print(f"Rows dated <  2010-12-10 in the other sheet:     {in_overlap_2.sum():,}")
    print(f"Identical row-for-row (same rows, same counts): {h1.sort_index().equals(h2.sort_index())}")
    df = raw[~in_overlap_1].drop(columns="SourceSheet").reset_index(drop=True)
    print(f"Rows after removing the overlapping copy: {len(df):,}")
    print("\nAll following sections use this overlap-free data.")

    section("4. Missing values")
    missing = pd.DataFrame({"missing": df.isna().sum(), "pct": (df.isna().mean() * 100).round(2)})
    print(missing)
    print(f"Blank (empty-string) descriptions: {df['Description'].str.strip().eq('').sum()}")

    section("5. Exact duplicate rows (within the data)")
    dup = df.duplicated(keep="first")
    print(f"Exact duplicate rows: {dup.sum():,} ({dup.mean() * 100:.2f}%)")
    print(f"  on cancellation invoices: {(dup & df['Invoice'].str.startswith('C')).sum():,}")
    print(f"  invoices affected: {df.loc[dup, 'Invoice'].nunique():,}")
    print("Example (same invoice, product, quantity, price, minute):")
    ex_inv = df.loc[dup, "Invoice"].iloc[0]
    print(df[(df["Invoice"] == ex_inv) & df.duplicated(keep=False)].sort_values("StockCode").head(6))

    section("6. Invoice types (first character)")
    df["InvoiceType"] = np.where(df["Invoice"].str.match(r"^\d"), "normal", df["Invoice"].str[0])
    print(df["InvoiceType"].value_counts())
    print("\nQuantity sign by invoice type:")
    print(pd.crosstab(df["InvoiceType"], np.sign(df["Quantity"]).map({-1: "neg", 0: "zero", 1: "pos"})))
    print("\n'A' invoices:")
    print(df[df["InvoiceType"] == "A"][DATA_COLUMNS])

    section("7. Quantity and Price")
    print(df[["Quantity", "Price"]].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).round(2))
    print(f"\nPrice == 0: {(df['Price'] == 0).sum():,}   Price < 0: {(df['Price'] < 0).sum():,}")
    neg_normal = df[(df["Quantity"] < 0) & (df["InvoiceType"] == "normal")]
    print(f"Negative quantity on normal invoices: {len(neg_normal):,} "
          f"(Price == 0: {(neg_normal['Price'] == 0).sum():,}; "
          f"no Customer ID: {neg_normal['Customer ID'].isna().sum():,})")
    print("Most common descriptions on those rows:")
    print(neg_normal["Description"].value_counts(dropna=False).head(10))

    section("8. Extreme lines")
    print("Largest absolute quantities:")
    print(df.reindex(df["Quantity"].abs().sort_values(ascending=False).index)[DATA_COLUMNS].head(8))
    print("\nHighest unit prices:")
    print(df.sort_values("Price", ascending=False)[DATA_COLUMNS].head(8))

    section("9. Non-standard stock codes")
    standard = df["StockCode"].str.match(STANDARD_CODE_PATTERN)
    odd = (
        df[~standard]
        .assign(LineValue=lambda x: x["Quantity"] * x["Price"])
        .groupby("StockCode")
        .agg(rows=("Invoice", "size"), example_description=("Description", "first"),
             total_value=("LineValue", "sum"))
        .sort_values("rows", ascending=False)
    )
    odd["treated_as_product"] = is_product_code(odd.index.to_series())
    print(f"Rows with non-standard StockCode: {(~standard).sum():,} across {len(odd)} codes")
    print(odd)
    odd.to_csv(OUT_DIR / "nonstandard_stockcodes.csv")
    non_product = ~is_product_code(df["StockCode"])
    print(f"\nRows classified as NON-product (services/fees/adjustments/vouchers): {non_product.sum():,}")

    section("10. Distinct counts")
    for col in ["Invoice", "StockCode", "Description", "Customer ID", "Country"]:
        print(f"{col:12s}: {df[col].nunique():,}")
    desc_per_code = df.dropna(subset=["Description"]).groupby("StockCode")["Description"].nunique()
    print(f"StockCodes with more than one Description: {(desc_per_code > 1).sum():,}")
    print(f"Example, StockCode {desc_per_code.idxmax()}:")
    print(df[df["StockCode"] == desc_per_code.idxmax()]["Description"].value_counts().head(6))
    print(f"Customer IDs with a fractional part: {(df['Customer ID'].dropna() % 1 != 0).sum()}")

    section("11. Invoice consistency")
    per_inv = df.groupby("Invoice").agg(
        timestamps=("InvoiceDate", "nunique"), customers=("Customer ID", "nunique"),
        countries=("Country", "nunique"), lines=("StockCode", "size"),
    )
    multi_ts = per_inv[per_inv["timestamps"] > 1].index
    spread = df[df["Invoice"].isin(multi_ts)].groupby("Invoice")["InvoiceDate"].agg(lambda s: s.max() - s.min())
    print(f"Invoices with >1 timestamp: {len(multi_ts):,} (max spread: {spread.max()})")
    print(f"Invoices with >1 customer: {(per_inv['customers'] > 1).sum():,}")
    print(f"Invoices with >1 country: {(per_inv['countries'] > 1).sum():,}")
    print("Lines per invoice:")
    print(per_inv["lines"].describe().round(2))

    section("12. Countries")
    country = df["Country"].value_counts()
    print(country.head(12))
    print(f"Countries: {len(country)}; UK share of rows: {country.get('United Kingdom', 0) / len(df) * 100:.1f}%")
    print(f"Unusual country values: {[c for c in country.index if c in ('Unspecified', 'European Community', 'West Indies')]}")
    country.to_csv(OUT_DIR / "country_counts.csv")

    section("13. Revenue under different rules (why business rules matter)")
    df["LineValue"] = df["Quantity"] * df["Price"]
    product = is_product_code(df["StockCode"])
    normal = df["InvoiceType"] == "normal"
    cancel = df["InvoiceType"] == "C"
    sale_line = normal & (df["Quantity"] > 0) & (df["Price"] > 0)
    gross = df.loc[sale_line & product, "LineValue"].sum()
    cancelled = df.loc[cancel & product, "LineValue"].sum()
    rows = [
        ("A. Naive sum(Qty*Price), raw workbook incl. sheet overlap", (raw["Quantity"] * raw["Price"]).sum()),
        ("B. Naive sum(Qty*Price), overlap removed", df["LineValue"].sum()),
        ("C. Sale lines only (normal invoice, Qty>0, Price>0), all codes", df.loc[sale_line, "LineValue"].sum()),
        ("D. Gross product sales = C restricted to product codes", gross),
        ("E. Cancelled product value ('C' invoices, product codes)", cancelled),
        ("F. Net product sales = D + E", gross + cancelled),
        ("G. Sensitivity: F with within-file exact duplicates removed",
         df.loc[~dup & sale_line & product, "LineValue"].sum() + df.loc[~dup & cancel & product, "LineValue"].sum()),
    ]
    for name, value in rows:
        print(f"{name:66s} {value:>16,.2f}")
    print(f"\nCancellation rate (value): {-cancelled / gross * 100:.2f}% of gross product sales")

    section("14. Monthly product sales and orders")
    df["Month"] = df["InvoiceDate"].dt.to_period("M")
    sales = df[sale_line & product]
    monthly = sales.groupby("Month").agg(
        gross_sales=("LineValue", "sum"), orders=("Invoice", "nunique"),
        customers=("Customer ID", "nunique"), trading_days=("InvoiceDate", lambda s: s.dt.date.nunique()),
    )
    monthly["cancellations"] = df[cancel & product].groupby("Month")["LineValue"].sum()
    monthly["net_sales"] = monthly["gross_sales"] + monthly["cancellations"]
    monthly["avg_order_value"] = monthly["gross_sales"] / monthly["orders"]
    print(monthly.round(2))
    monthly.to_csv(OUT_DIR / "monthly_sales.csv")
    nov = monthly.loc[[pd.Period("2010-11"), pd.Period("2011-11")], "net_sales"]
    print(f"\nNovember net sales 2010 vs 2011: {nov.iloc[0]:,.2f} vs {nov.iloc[1]:,.2f}")

    section("15. Top products: gross vs net (cancellations matter)")
    by_product = pd.DataFrame({
        "description": df[product].groupby("StockCode")["Description"].agg(
            lambda s: s.mode().iat[0] if not s.mode().empty else None),
        "gross_sales": sales.groupby("StockCode")["LineValue"].sum(),
        "cancelled": df[cancel & product].groupby("StockCode")["LineValue"].sum(),
        "units_sold": sales.groupby("StockCode")["Quantity"].sum(),
        "orders": sales.groupby("StockCode")["Invoice"].nunique(),
    }).fillna({"gross_sales": 0, "cancelled": 0, "units_sold": 0, "orders": 0})
    by_product["net_sales"] = by_product["gross_sales"] + by_product["cancelled"]
    by_product["gross_rank"] = by_product["gross_sales"].rank(ascending=False, method="min")
    by_product["net_rank"] = by_product["net_sales"].rank(ascending=False, method="min")
    print("Top 10 by GROSS sales:")
    print(by_product.sort_values("gross_sales", ascending=False).head(10).round(2))
    print("\nTop 10 by NET sales:")
    print(by_product.sort_values("net_sales", ascending=False).head(10).round(2))
    by_product.sort_values("net_sales", ascending=False).to_csv(OUT_DIR / "product_sales.csv")

    section("16. Customers")
    identified = sales["Customer ID"].notna()
    print(f"Gross product sales with a Customer ID: "
          f"{sales.loc[identified, 'LineValue'].sum() / sales['LineValue'].sum() * 100:.1f}%")
    cust = sales[identified].groupby("Customer ID")["LineValue"].sum().sort_values(ascending=False)
    top_n = int(len(cust) * 0.1)
    print(f"Customers with purchases: {len(cust):,}; top 10% ({top_n}) share of identified sales: "
          f"{cust.head(top_n).sum() / cust.sum() * 100:.1f}%")
    orders_per_cust = sales[identified].groupby("Customer ID")["Invoice"].nunique()
    print(f"Customers with only one order: {(orders_per_cust == 1).mean() * 100:.1f}%")

    section("17. Outlier flagging on sale-line value (IQR rule)")
    q1, q3 = sales["LineValue"].quantile([0.25, 0.75])
    upper = q3 + 1.5 * (q3 - q1)
    flagged = sales["LineValue"] > upper
    print(f"Q1={q1:.2f}  Q3={q3:.2f}  upper fence={upper:.2f}")
    print(f"Lines above fence: {flagged.sum():,} ({flagged.mean() * 100:.1f}%)")
    print("The IQR rule flags many ordinary wholesale orders: flag for review, never auto-remove.")
    log_val = np.log10(sales["LineValue"])
    z = (log_val - log_val.mean()) / log_val.std()
    print(f"Alternative: |z| > 3 on log10(line value): {(z.abs() > 3).sum():,} lines")


if __name__ == "__main__":
    main()
