"""Data-quality profiling. These functions only describe the data; nothing is changed.

Functions on the raw upload use the file's own column names; functions on the
prepared table use the canonical names from analytics.definitions.
"""

import numpy as np
import pandas as pd

from src.analytics.breakdowns import sales_over_time
from src.analytics.definitions import (
    CANCELLATION, CUSTOMER_ID, INVOICE, INVOICE_DATE, IS_DUPLICATE, LINE_TYPE, LINE_TYPES,
    LINE_VALUE, PRODUCT_ID, QUANTITY, REQUIRED_COLUMNS, SALE,
)
from src.analytics.prepare import NUMBER_COLUMNS, to_datetime, to_number

REVENUE_LINE_TYPES = (SALE, CANCELLATION)


# --- Raw upload ---------------------------------------------------------------

def column_profile(raw: pd.DataFrame) -> pd.DataFrame:
    """One row per column: type, missing values, distinct values and examples."""
    rows = []
    for column in raw.columns:
        values = raw[column]
        rows.append({
            "column": str(column),
            "type": str(values.dtype),
            "missing": int(values.isna().sum()),
            "missing_pct": float(values.isna().mean() * 100),
            "distinct": int(values.nunique()),
            "examples": ", ".join(str(v) for v in values.dropna().unique()[:3]),
        })
    return pd.DataFrame(rows)


def numeric_summary(raw: pd.DataFrame) -> pd.DataFrame:
    numbers = raw.select_dtypes("number")
    if numbers.empty:
        return pd.DataFrame()
    return numbers.describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T


def top_values(raw: pd.DataFrame, column: str, n: int = 10) -> pd.DataFrame:
    counts = raw[column].value_counts(dropna=False).head(n)
    return pd.DataFrame({
        "value": counts.index.astype(str),
        "rows": counts.to_numpy(),
        "pct": counts.to_numpy() / len(raw) * 100,
    })


def invalid_values(raw: pd.DataFrame, mapping: dict[str, str], dayfirst: bool = False):
    """Missing or unreadable values in the required columns.

    Returns (summary table, boolean mask of rows with at least one problem).
    """
    bad_rows = pd.Series(False, index=raw.index)
    rows = []
    for canonical in REQUIRED_COLUMNS:
        source = mapping[canonical]
        values = raw[source]
        missing = values.isna()
        if canonical in NUMBER_COLUMNS:
            invalid = to_number(values).isna() & ~missing
        elif canonical == INVOICE_DATE:
            invalid = to_datetime(values, dayfirst).isna() & ~missing
        else:
            invalid = pd.Series(False, index=raw.index)
        bad_rows |= missing | invalid
        rows.append({"column": source, "used_as": canonical,
                     "missing": int(missing.sum()), "invalid": int(invalid.sum())})
    return pd.DataFrame(rows), bad_rows


# --- Prepared transactions ------------------------------------------------------

def line_type_summary(tx: pd.DataFrame) -> pd.DataFrame:
    """Lines and value per line type, and whether each type counts as revenue."""
    grouped = tx.groupby(LINE_TYPE).agg(lines=(LINE_VALUE, "size"), value=(LINE_VALUE, "sum"))
    grouped = grouped.reindex(LINE_TYPES).fillna(0).astype({"lines": "int64"})
    grouped["counts_in_revenue"] = grouped.index.isin(REVENUE_LINE_TYPES)
    return grouped.reset_index()


def outliers(tx: pd.DataFrame, method: str = "iqr") -> tuple[pd.DataFrame, str]:
    """Flag unusually large sale lines. They are candidates for review, not errors.

    iqr: line value above Q3 + 1.5 x IQR (simple, but flags many normal bulk orders).
    log_z: more than 3 standard deviations from the mean of log10(line value).
    Returns (flagged lines, largest first; explanation of the rule).
    """
    sales = tx.loc[tx[LINE_TYPE] == SALE]
    if sales.empty:
        return sales.iloc[0:0], "No sale lines to check."
    values = sales[LINE_VALUE]
    if method == "iqr":
        q1, q3 = values.quantile([0.25, 0.75])
        fence = q3 + 1.5 * (q3 - q1)
        flagged = values > fence
        rule = f"Line value above {fence:,.2f} (Q3 {q3:,.2f} + 1.5 x IQR)"
    elif method == "log_z":
        logs = np.log10(values)
        spread = logs.std()
        z = (logs - logs.mean()) / spread if spread else logs * 0
        flagged = z.abs() > 3
        rule = "log10(line value) more than 3 standard deviations from its mean"
    else:
        raise ValueError(f"Unknown outlier method '{method}'.")
    return sales.loc[flagged].sort_values(LINE_VALUE, ascending=False), rule


def quality_summary(tx: pd.DataFrame) -> dict:
    """Headline data-quality indicators for the prepared table."""
    sales = tx.loc[tx[LINE_TYPE] == SALE]
    gross = sales[LINE_VALUE].sum()
    summary = {
        "rows": len(tx),
        "invoices": int(tx[INVOICE].nunique()),
        "products": int(tx[PRODUCT_ID].nunique()),
        "first_date": tx[INVOICE_DATE].min(),
        "last_date": tx[INVOICE_DATE].max(),
        "exact_duplicates": int(tx[IS_DUPLICATE].sum()),
        "rows_outside_revenue": int((~tx[LINE_TYPE].isin(REVENUE_LINE_TYPES)).sum()),
        "negative_quantity_lines": int((tx[QUANTITY] < 0).sum()),
    }
    if CUSTOMER_ID in tx.columns:
        unidentified = sales.loc[sales[CUSTOMER_ID].isna(), LINE_VALUE].sum()
        summary["sales_without_customer_pct"] = float(unidentified / gross * 100) if gross else 0.0
    monthly = sales_over_time(tx, "month")
    summary["partial_months"] = monthly.loc[monthly["is_partial"], "period"].tolist()
    return summary
