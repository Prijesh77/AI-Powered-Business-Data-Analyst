"""Grouped analyses: sales by product / country / customer, rankings and trends.

Every table returns net_sales, gross_sales, cancellations, orders and units
with the same definitions as kpis.py, so the group totals add up to the KPIs.
"""

import pandas as pd

from src.analytics.definitions import (
    CANCELLATION, COUNTRY, CUSTOMER_ID, INVOICE, INVOICE_DATE, LINE_TYPE, LINE_VALUE,
    PRODUCT_ID, PRODUCT_NAME, QUANTITY, SALE,
)
from src.analytics.errors import InvalidParameterError
from src.analytics.kpis import require_columns

DIMENSIONS = {"product": PRODUCT_ID, "country": COUNTRY, "customer": CUSTOMER_ID}
RANKING_METRICS = ("net_sales", "gross_sales", "units_sold", "orders")
# Weeks run Monday to Sunday.
FREQUENCIES = {"day": "D", "week": "W-SUN", "month": "M"}

TABLE_COLUMNS = ["net_sales", "gross_sales", "cancellations", "orders", "units_sold", "share_of_net_sales"]


def _dimension_column(df: pd.DataFrame, dimension: str) -> str:
    if dimension not in DIMENSIONS:
        raise InvalidParameterError(f"Unknown grouping '{dimension}'. Choose from {list(DIMENSIONS)}.")
    column = DIMENSIONS[dimension]
    require_columns(df, [column], f"Sales by {dimension}")
    return column


def sales_by(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """One row per product, country or customer, sorted by net sales (highest first).

    Rows without a value for the dimension (e.g. no customer ID) are left out.
    """
    key = _dimension_column(df, dimension)
    sales = df.loc[df[LINE_TYPE] == SALE]
    cancelled = df.loc[df[LINE_TYPE] == CANCELLATION]

    table = sales.groupby(key).agg(
        gross_sales=(LINE_VALUE, "sum"), orders=(INVOICE, "nunique"), units_sold=(QUANTITY, "sum"),
    )
    table = table.join(cancelled.groupby(key)[LINE_VALUE].sum().rename("cancellations"), how="outer")
    table = table.fillna({"gross_sales": 0.0, "orders": 0, "units_sold": 0, "cancellations": 0.0})
    table = table.astype({"orders": "int64", "units_sold": "int64"})
    table["net_sales"] = table["gross_sales"] + table["cancellations"]
    total = table["net_sales"].sum()
    table["share_of_net_sales"] = table["net_sales"] / total if total else float("nan")

    table = table.reset_index().sort_values(["net_sales", key], ascending=[False, True])
    columns = [key] + TABLE_COLUMNS
    if dimension == "product":
        names = df.drop_duplicates(PRODUCT_ID).set_index(PRODUCT_ID)[PRODUCT_NAME]
        table[PRODUCT_NAME] = table[key].map(names)
        columns.insert(1, PRODUCT_NAME)
    return table[columns].reset_index(drop=True)


def top_n(
    df: pd.DataFrame,
    dimension: str,
    n: int = 10,
    metric: str = "net_sales",
    bottom: bool = False,
) -> pd.DataFrame:
    """Best (or worst, with bottom=True) n groups by a metric.

    Exactly n rows are returned; equal values share a rank (e.g. 1, 2, 2, 4).
    "Bottom" only considers groups with at least one order in the data given.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise InvalidParameterError(f"n must be a whole number of at least 1, not {n!r}.")
    if metric not in RANKING_METRICS:
        raise InvalidParameterError(f"Cannot rank by '{metric}'. Choose from {list(RANKING_METRICS)}.")

    table = sales_by(df, dimension)
    key = DIMENSIONS[dimension]
    if bottom:
        table = table.loc[table["orders"] > 0]
    table = table.sort_values([metric, key], ascending=[bottom, True])
    table.insert(0, "rank", table[metric].rank(method="min", ascending=bottom).astype("int64"))
    return table.head(n).reset_index(drop=True)


def sales_over_time(
    df: pd.DataFrame,
    freq: str = "month",
    coverage_start=None,
    coverage_end=None,
) -> pd.DataFrame:
    """Sales per day, week or month, including periods with no sales (as zero).

    is_partial is True when the data does not cover the whole period. Coverage
    defaults to the first and last date in df; when df was filtered to a date
    range, pass that range so the first/last periods are judged correctly.
    """
    if freq not in FREQUENCIES:
        raise InvalidParameterError(f"Unknown period '{freq}'. Choose from {list(FREQUENCIES)}.")
    columns = ["period", "period_start", "period_end", "net_sales", "gross_sales", "cancellations",
               "orders", "average_order_value", "is_partial"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    start = pd.Timestamp(coverage_start if coverage_start is not None else df[INVOICE_DATE].min()).normalize()
    end = pd.Timestamp(coverage_end if coverage_end is not None else df[INVOICE_DATE].max()).normalize()
    periods = pd.period_range(start, end, freq=FREQUENCIES[freq])
    period_of_row = df[INVOICE_DATE].dt.to_period(FREQUENCIES[freq])
    is_sale = df[LINE_TYPE] == SALE
    is_cancel = df[LINE_TYPE] == CANCELLATION

    gross = df.loc[is_sale, LINE_VALUE].groupby(period_of_row[is_sale]).sum()
    cancelled = df.loc[is_cancel, LINE_VALUE].groupby(period_of_row[is_cancel]).sum()
    orders = df.loc[is_sale, INVOICE].groupby(period_of_row[is_sale]).nunique()

    table = pd.DataFrame({
        "period": periods.astype(str),
        "period_start": periods.start_time,
        "period_end": periods.end_time.normalize(),
        "gross_sales": gross.reindex(periods, fill_value=0.0).to_numpy(),
        "cancellations": cancelled.reindex(periods, fill_value=0.0).to_numpy(),
        "orders": orders.reindex(periods, fill_value=0).to_numpy().astype("int64"),
    })
    table["net_sales"] = table["gross_sales"] + table["cancellations"]
    table["average_order_value"] = (table["gross_sales"] / table["orders"]).where(table["orders"] > 0)
    table["is_partial"] = (table["period_start"] < start) | (table["period_end"] > end)
    return table[columns]


def customer_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Sales per identified customer with first and last purchase dates."""
    table = sales_by(df, "customer")
    sales = df.loc[(df[LINE_TYPE] == SALE) & df[CUSTOMER_ID].notna()]
    dates = sales.groupby(CUSTOMER_ID)[INVOICE_DATE].agg(first_purchase="min", last_purchase="max")
    return table.merge(dates, left_on=CUSTOMER_ID, right_index=True, how="left")
