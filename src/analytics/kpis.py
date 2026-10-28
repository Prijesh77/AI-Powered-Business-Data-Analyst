"""Single-number business KPIs.

All functions take a table produced by prepare.prepare_transactions. To use a
date range or other filter, call filter_transactions first and pass its result.
Definitions are in definitions.METRICS.
"""

import pandas as pd

from src.analytics.definitions import (
    CANCELLATION, COUNTRY, CUSTOMER_ID, INVOICE, INVOICE_DATE, LINE_TYPE, LINE_VALUE,
    PRODUCT_ID, QUANTITY, SALE, UNIT_COST,
)
from src.analytics.errors import InvalidParameterError, MetricUnavailableError, MissingColumnError


def require_columns(df: pd.DataFrame, columns: list[str], purpose: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise MissingColumnError(f"{purpose} needs column(s) {missing}, which this dataset does not have.")


def _parse_date(value, name: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise InvalidParameterError(f"'{value}' is not a valid {name} date.") from exc


def filter_transactions(
    df: pd.DataFrame,
    start=None,
    end=None,
    countries: list[str] | None = None,
    product_ids: list[str] | None = None,
    customer_ids: list[str] | None = None,
) -> pd.DataFrame:
    """Return the rows inside the filters.

    start and end are dates and both are inclusive: end="2011-12-31" keeps
    everything up to 23:59 on 31 December. None means "no limit".
    """
    mask = pd.Series(True, index=df.index)
    if start is not None:
        start = _parse_date(start, "start")
        mask &= df[INVOICE_DATE] >= start
    if end is not None:
        end = _parse_date(end, "end")
        mask &= df[INVOICE_DATE] < end.normalize() + pd.Timedelta(days=1)
    if start is not None and end is not None and start.normalize() > end.normalize():
        raise InvalidParameterError(f"Start date {start.date()} is after end date {end.date()}.")
    for column, values in ((COUNTRY, countries), (PRODUCT_ID, product_ids), (CUSTOMER_ID, customer_ids)):
        if values is not None:
            require_columns(df, [column], f"Filtering by {column}")
            mask &= df[column].isin(values)
    return df.loc[mask]


def _lines(df: pd.DataFrame, line_type: str) -> pd.DataFrame:
    return df.loc[df[LINE_TYPE] == line_type]


def gross_sales(df: pd.DataFrame) -> float:
    return float(_lines(df, SALE)[LINE_VALUE].sum())


def cancellations(df: pd.DataFrame) -> float:
    """Negative amount (or 0) for cancelled product lines."""
    return float(_lines(df, CANCELLATION)[LINE_VALUE].sum())


def net_sales(df: pd.DataFrame) -> float:
    """Revenue: gross product sales plus (negative) cancellations."""
    return gross_sales(df) + cancellations(df)


def order_count(df: pd.DataFrame) -> int:
    return int(_lines(df, SALE)[INVOICE].nunique())


def units_sold(df: pd.DataFrame) -> int:
    return int(_lines(df, SALE)[QUANTITY].sum())


def average_order_value(df: pd.DataFrame) -> float | None:
    """None when there are no orders (an average of nothing is undefined)."""
    orders = order_count(df)
    return gross_sales(df) / orders if orders else None


def cancellation_rate(df: pd.DataFrame) -> float | None:
    gross = gross_sales(df)
    return -cancellations(df) / gross if gross else None


def active_customers(df: pd.DataFrame) -> int:
    require_columns(df, [CUSTOMER_ID], "Counting customers")
    return int(_lines(df, SALE)[CUSTOMER_ID].nunique())


def identified_sales_share(df: pd.DataFrame) -> float | None:
    """Share of gross sales on lines that have a customer ID."""
    require_columns(df, [CUSTOMER_ID], "Customer analysis")
    sales = _lines(df, SALE)
    gross = sales[LINE_VALUE].sum()
    return float(sales.loc[sales[CUSTOMER_ID].notna(), LINE_VALUE].sum() / gross) if gross else None


def repeat_customer_rate(df: pd.DataFrame) -> float | None:
    require_columns(df, [CUSTOMER_ID], "Repeat customer rate")
    orders_per_customer = _lines(df, SALE).groupby(CUSTOMER_ID)[INVOICE].nunique()
    if orders_per_customer.empty:
        return None
    return float((orders_per_customer >= 2).mean())


def gross_profit(df: pd.DataFrame) -> float:
    """Net sales minus cost of goods sold. Needs a unit cost for every product line."""
    if UNIT_COST not in df.columns:
        raise MetricUnavailableError(
            "Gross profit cannot be calculated: this dataset has no product cost column. "
            "Revenue is not the same as profit."
        )
    lines = df.loc[df[LINE_TYPE].isin([SALE, CANCELLATION])]
    missing = lines[UNIT_COST].isna().sum()
    if missing:
        raise MetricUnavailableError(
            f"Gross profit cannot be calculated: {missing:,} sales lines have no unit cost."
        )
    cost_of_goods_sold = float((lines[QUANTITY] * lines[UNIT_COST]).sum())
    return net_sales(df) - cost_of_goods_sold


def kpi_summary(df: pd.DataFrame) -> dict:
    """The headline KPIs in one dictionary (customer KPIs only if the column exists)."""
    summary = {
        "net_sales": net_sales(df),
        "gross_sales": gross_sales(df),
        "cancellations": cancellations(df),
        "orders": order_count(df),
        "average_order_value": average_order_value(df),
        "units_sold": units_sold(df),
        "cancellation_rate": cancellation_rate(df),
        "first_date": df[INVOICE_DATE].min() if len(df) else None,
        "last_date": df[INVOICE_DATE].max() if len(df) else None,
    }
    if CUSTOMER_ID in df.columns:
        summary["active_customers"] = active_customers(df)
        summary["identified_sales_share"] = identified_sales_share(df)
        summary["repeat_customer_rate"] = repeat_customer_rate(df)
    return summary
