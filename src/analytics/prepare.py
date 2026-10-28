"""Turn an uploaded table into a standard transactions table.

Steps (each is a small function, so it can be tested on its own):
1. standardise_columns: rename columns via a mapping and convert types.
2. Flag exact duplicate lines (kept unless the caller asks to drop them).
3. Give each product one name (its most common description).
4. Use the earliest timestamp of each invoice as its date.
5. Add line_value = quantity x unit_price.
6. classify_lines: put every row in one line type (sale, cancellation...).

The input DataFrame is never modified; a new one is returned.
"""

import numpy as np
import pandas as pd

from src.analytics.definitions import (
    ACCOUNTING_ADJUSTMENT, CANCELLATION, CUSTOMER_ID, INVOICE, INVOICE_DATE, IS_DUPLICATE,
    LINE_TYPE, LINE_VALUE, NON_PRODUCT, OPTIONAL_COLUMNS, PRODUCT_ID, PRODUCT_NAME, QUANTITY,
    REQUIRED_COLUMNS, SALE, STOCK_ADJUSTMENT, UNIT_COST, UNIT_PRICE, ZERO_PRICE, LineRules,
)
from src.analytics.errors import InvalidDataError, InvalidParameterError, MissingColumnError

ID_COLUMNS = (INVOICE, PRODUCT_ID, CUSTOMER_ID)
NUMBER_COLUMNS = (QUANTITY, UNIT_PRICE, UNIT_COST)


def _to_id_text(values: pd.Series) -> pd.Series:
    """Convert identifiers to text. Whole numbers lose the '.0' that Excel adds."""
    if pd.api.types.is_numeric_dtype(values):
        present = values.dropna()
        if (present % 1 == 0).all():
            values = values.astype("Int64")
    return values.astype("str").str.strip()


def to_number(values: pd.Series) -> pd.Series:
    """Convert to numbers; values that are not numbers become missing."""
    return pd.to_numeric(values, errors="coerce")


def to_datetime(values: pd.Series, dayfirst: bool = False) -> pd.Series:
    """Convert to dates; values that are not dates become missing.

    dayfirst=True reads 03/04/2011 as 3 April (UK style) instead of 4 March.
    """
    if pd.api.types.is_datetime64_any_dtype(values):
        return values
    return pd.to_datetime(values, errors="coerce", dayfirst=dayfirst)


def _raise_if_invalid(values: pd.Series, converted: pd.Series, source: str, what: str) -> None:
    bad = converted.isna() & values.notna()
    if bad.any():
        examples = values[bad].astype(str).unique()[:3].tolist()
        raise InvalidDataError(
            f"{bad.sum():,} values in column '{source}' are not {what} (e.g. {examples})."
        )


def standardise_columns(raw: pd.DataFrame, mapping: dict[str, str], dayfirst: bool = False) -> pd.DataFrame:
    """Return a new table with canonical column names and types.

    mapping: {canonical name: column name in the uploaded file}.
    Raises MissingColumnError if a required column is not mapped or not in the file,
    and InvalidDataError if required values are missing or cannot be converted.
    """
    unknown = set(mapping) - set(REQUIRED_COLUMNS) - set(OPTIONAL_COLUMNS)
    if unknown:
        raise InvalidParameterError(f"Unknown canonical column(s) in mapping: {sorted(unknown)}")
    unmapped = [c for c in REQUIRED_COLUMNS if c not in mapping]
    if unmapped:
        raise MissingColumnError(f"Required column(s) not mapped: {unmapped}")
    absent = [src for src in mapping.values() if src not in raw.columns]
    if absent:
        raise MissingColumnError(f"Column(s) not found in the file: {absent}")

    df = pd.DataFrame({canonical: raw[source] for canonical, source in mapping.items()})
    for column in df.columns:
        source = mapping[column]
        if column in ID_COLUMNS:
            df[column] = _to_id_text(df[column])
        elif column in NUMBER_COLUMNS:
            converted = to_number(df[column])
            _raise_if_invalid(df[column], converted, source, "numbers")
            df[column] = converted
        elif column == INVOICE_DATE:
            converted = to_datetime(df[column], dayfirst)
            _raise_if_invalid(df[column], converted, source, "valid dates")
            df[column] = converted
        else:
            df[column] = df[column].astype("str").str.strip()

    for column in REQUIRED_COLUMNS:
        missing = df[column].isna().sum()
        if missing:
            raise InvalidDataError(
                f"Required column '{mapping[column]}' has {missing:,} missing values."
            )
    return df


def canonical_product_names(df: pd.DataFrame) -> pd.Series:
    """Most common description per product; ties go to the alphabetically first one.

    Products with no description at all use their product ID as the name.
    """
    if PRODUCT_NAME not in df.columns:
        return df[PRODUCT_ID].copy()
    counts = (
        df.dropna(subset=[PRODUCT_NAME])
        .groupby([PRODUCT_ID, PRODUCT_NAME]).size().rename("n").reset_index()
        .sort_values(["n", PRODUCT_NAME], ascending=[False, True])
    )
    best = counts.drop_duplicates(PRODUCT_ID).set_index(PRODUCT_ID)[PRODUCT_NAME]
    return df[PRODUCT_ID].map(best).fillna(df[PRODUCT_ID])


def classify_lines(df: pd.DataFrame, rules: LineRules) -> pd.Series:
    """Return the line type of every row. The first matching rule wins."""
    invoice, code = df[INVOICE], df[PRODUCT_ID]
    quantity, price = df[QUANTITY], df[UNIT_PRICE]
    no = pd.Series(False, index=df.index)

    accounting = invoice.str.startswith(rules.accounting_prefixes) if rules.accounting_prefixes else no
    non_product = code.isin(rules.non_product_codes)
    if rules.non_product_prefixes:
        non_product |= code.str.startswith(rules.non_product_prefixes)
    if rules.cancellation_prefix:
        cancellation = invoice.str.startswith(rules.cancellation_prefix)
    else:
        cancellation = quantity < 0

    line_type = np.select(
        [accounting, non_product, cancellation, (quantity > 0) & (price > 0), quantity <= 0],
        [ACCOUNTING_ADJUSTMENT, NON_PRODUCT, CANCELLATION, SALE, STOCK_ADJUSTMENT],
        default=ZERO_PRICE,
    )
    return pd.Series(line_type, index=df.index, name=LINE_TYPE)


def prepare_transactions(
    raw: pd.DataFrame,
    mapping: dict[str, str],
    rules: LineRules = LineRules(),
    drop_duplicates: bool = False,
    dayfirst: bool = False,
) -> pd.DataFrame:
    """Run all preparation steps and return the analysis-ready table."""
    df = standardise_columns(raw, mapping, dayfirst)

    df[IS_DUPLICATE] = df.duplicated(keep="first")
    if drop_duplicates:
        df = df.loc[~df[IS_DUPLICATE]].reset_index(drop=True)

    df[PRODUCT_NAME] = canonical_product_names(df)
    df[INVOICE_DATE] = df.groupby(INVOICE)[INVOICE_DATE].transform("min")
    df[LINE_VALUE] = df[QUANTITY] * df[UNIT_PRICE]
    df[LINE_TYPE] = classify_lines(df, rules)
    return df
