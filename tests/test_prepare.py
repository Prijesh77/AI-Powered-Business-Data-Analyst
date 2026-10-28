import pandas as pd
import pytest

from src.analytics.definitions import (
    CUSTOMER_ID, INVOICE_DATE, IS_DUPLICATE, LINE_TYPE, LINE_VALUE, ONLINE_RETAIL_II_MAPPING,
    PRODUCT_NAME, LineRules,
)
from src.analytics.errors import InvalidDataError, InvalidParameterError, MissingColumnError
from src.analytics.prepare import classify_lines, prepare_transactions, standardise_columns

EXPECTED_LINE_TYPES = [
    "sale", "sale", "non_product", "sale", "sale", "cancellation", "sale", "sale",
    "stock_adjustment", "accounting_adjustment", "zero_price", "sale", "sale",
]


def test_every_line_gets_the_hand_checked_type(transactions):
    assert transactions[LINE_TYPE].tolist() == EXPECTED_LINE_TYPES


def test_line_value_is_quantity_times_price(transactions):
    assert transactions[LINE_VALUE].tolist() == [10, 20, 15, 45, 45, -20, 30, 10, 0, -100, 0, 40, 5]


def test_input_is_not_modified(raw_sample):
    before = raw_sample.copy()
    prepare_transactions(raw_sample, ONLINE_RETAIL_II_MAPPING)
    pd.testing.assert_frame_equal(raw_sample, before)


def test_customer_ids_become_text_without_decimal(transactions):
    assert transactions[CUSTOMER_ID].iloc[0] == "1"
    assert pd.isna(transactions[CUSTOMER_ID].iloc[6])


def test_missing_description_is_filled_with_products_usual_name(transactions):
    assert transactions[PRODUCT_NAME].iloc[6] == "BOWL"


def test_invoice_uses_its_earliest_timestamp(transactions):
    assert (transactions[INVOICE_DATE].iloc[11:13] == pd.Timestamp("2024-03-03 13:00")).all()


def test_exact_duplicates_are_flagged_but_kept_by_default(transactions):
    assert transactions[IS_DUPLICATE].tolist().count(True) == 1
    assert bool(transactions[IS_DUPLICATE].iloc[4])
    assert len(transactions) == 13


def test_duplicates_can_be_dropped(transactions_deduplicated):
    assert len(transactions_deduplicated) == 12


def test_missing_required_mapping_is_reported(raw_sample):
    mapping = {k: v for k, v in ONLINE_RETAIL_II_MAPPING.items() if k != "unit_price"}
    with pytest.raises(MissingColumnError, match="unit_price"):
        standardise_columns(raw_sample, mapping)


def test_mapped_column_absent_from_file_is_reported(raw_sample):
    with pytest.raises(MissingColumnError, match="Price"):
        standardise_columns(raw_sample.drop(columns="Price"), ONLINE_RETAIL_II_MAPPING)


def test_unknown_canonical_name_is_rejected(raw_sample):
    with pytest.raises(InvalidParameterError):
        standardise_columns(raw_sample, {**ONLINE_RETAIL_II_MAPPING, "profit": "Price"})


def test_text_in_number_column_is_reported(raw_sample):
    raw_sample["Quantity"] = raw_sample["Quantity"].astype(object)
    raw_sample.loc[0, "Quantity"] = "two"
    with pytest.raises(InvalidDataError, match="not numbers"):
        standardise_columns(raw_sample, ONLINE_RETAIL_II_MAPPING)


def test_invalid_date_is_reported(raw_sample):
    raw_sample["InvoiceDate"] = raw_sample["InvoiceDate"].astype(str)
    raw_sample.loc[0, "InvoiceDate"] = "not a date"
    with pytest.raises(InvalidDataError, match="not valid dates"):
        standardise_columns(raw_sample, ONLINE_RETAIL_II_MAPPING)


def test_missing_required_value_is_reported(raw_sample):
    raw_sample.loc[0, "Price"] = None
    with pytest.raises(InvalidDataError, match="missing"):
        standardise_columns(raw_sample, ONLINE_RETAIL_II_MAPPING)


def test_without_cancellation_prefix_negative_quantity_means_cancellation():
    df = pd.DataFrame({
        "invoice": ["1", "2"], "product_id": ["A", "A"], "quantity": [3, -1],
        "unit_price": [2.0, 2.0],
    })
    assert classify_lines(df, LineRules()).tolist() == ["sale", "cancellation"]
