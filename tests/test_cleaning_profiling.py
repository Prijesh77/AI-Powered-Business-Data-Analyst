import pandas as pd
import pytest

from src.analytics import kpis
from src.analytics.definitions import ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES
from src.data.cleaning import (
    CROSS_SHEET, EXACT_DUPLICATES, INVALID_ROWS, apply_cleaning, cross_sheet_duplicate_mask, propose_cleaning,
)
from src.data.profiling import column_profile, invalid_values, line_type_summary, outliers, quality_summary


@pytest.fixture
def two_sheets(raw_sample):
    """Sheet A = rows 0-4, sheet B = rows 3-12: rows 3 and 4 (identical MUG lines) are in both."""
    return pd.concat([raw_sample.iloc[0:5].assign(SourceSheet="A"),
                      raw_sample.iloc[3:13].assign(SourceSheet="B")], ignore_index=True)


def test_cross_sheet_copies_are_matched_one_for_one(two_sheets):
    mask = cross_sheet_duplicate_mask(two_sheets)
    # Sheet A holds the MUG line twice and sheet B holds it twice: both B copies are repeats.
    assert mask.sum() == 2
    assert two_sheets.loc[mask, "SourceSheet"].eq("B").all()


def test_single_sheet_has_no_cross_sheet_duplicates(raw_sample):
    assert not cross_sheet_duplicate_mask(raw_sample).any()


def test_proposed_steps_and_defaults(two_sheets):
    steps = {s.key: s for s in propose_cleaning(two_sheets, ONLINE_RETAIL_II_MAPPING)}
    assert steps[CROSS_SHEET].rows_affected == 2 and steps[CROSS_SHEET].default
    assert steps[EXACT_DUPLICATES].rows_affected == 1 and not steps[EXACT_DUPLICATES].default
    assert INVALID_ROWS not in steps


def test_cleaning_two_sheets_gives_the_single_sheet_answer(two_sheets):
    tx, log = apply_cleaning(two_sheets, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES, {})
    assert len(tx) == 13
    assert kpis.net_sales(tx) == pytest.approx(185)
    assert log[0]["step"].startswith("Remove rows repeated") and log[0]["rows_after"] == 13


def test_keeping_cross_sheet_rows_double_counts(two_sheets):
    tx, _ = apply_cleaning(two_sheets, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES, {CROSS_SHEET: False})
    assert kpis.net_sales(tx) == pytest.approx(185 + 90)


def test_rows_with_bad_required_values_are_removed(raw_sample):
    bad = raw_sample.copy()
    bad["Price"] = bad["Price"].astype(object)
    extra = pd.DataFrame([
        {**bad.iloc[0].to_dict(), "Invoice": "9001", "Price": "abc"},
        {**bad.iloc[0].to_dict(), "Invoice": "9002", "Quantity": None},
    ])
    bad = pd.concat([bad, extra], ignore_index=True)
    table, mask = invalid_values(bad, ONLINE_RETAIL_II_MAPPING)
    assert mask.sum() == 2
    assert table.set_index("used_as").loc["unit_price", "invalid"] == 1
    steps = {s.key: s for s in propose_cleaning(bad, ONLINE_RETAIL_II_MAPPING)}
    assert steps[INVALID_ROWS].required
    tx, _ = apply_cleaning(bad, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES, {})
    assert kpis.net_sales(tx) == pytest.approx(185)


def test_duplicate_removal_choice(raw_sample):
    tx, log = apply_cleaning(raw_sample, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES, {EXACT_DUPLICATES: True})
    assert kpis.net_sales(tx) == pytest.approx(140)
    assert any(entry["step"] == "Remove exact duplicate lines" and entry["applied"] for entry in log)


def test_original_upload_is_not_modified(two_sheets):
    before = two_sheets.copy()
    apply_cleaning(two_sheets, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES, {EXACT_DUPLICATES: True})
    pd.testing.assert_frame_equal(two_sheets, before)


def test_column_profile(raw_sample):
    profile = column_profile(raw_sample).set_index("column")
    assert profile.loc["Description", "missing"] == 1
    assert profile.loc["Customer ID", "missing"] == 3
    assert profile.loc["Invoice", "distinct"] == 9   # 1001, 1002, C1003, 1004-1006, A1007, 1008, 1009


def test_line_type_summary(transactions):
    summary = line_type_summary(transactions).set_index("line_type")
    assert summary["lines"].to_dict() == {
        "sale": 8, "cancellation": 1, "stock_adjustment": 1, "zero_price": 1,
        "non_product": 1, "accounting_adjustment": 1,
    }
    assert summary.loc["sale", "value"] == pytest.approx(205)
    assert summary.loc["sale", "counts_in_revenue"] and not summary.loc["non_product", "counts_in_revenue"]


def test_iqr_outliers(transactions):
    # Sale line values: 5,10,10,20,30,40,45,45 -> Q1 = 10, Q3 = 41.25, fence = 88.125: nothing flagged.
    flagged, rule = outliers(transactions, "iqr")
    assert flagged.empty
    assert "88.12" in rule


def test_quality_summary(transactions):
    summary = quality_summary(transactions)
    assert summary["exact_duplicates"] == 1
    assert summary["rows_outside_revenue"] == 4
    assert summary["partial_months"] == ["2024-01", "2024-03"]
    assert summary["sales_without_customer_pct"] == pytest.approx(30 / 205 * 100)
