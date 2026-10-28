import pandas as pd
import pytest

from src.analytics import kpis
from src.analytics.definitions import UNIT_COST
from src.analytics.errors import InvalidParameterError, MetricUnavailableError, MissingColumnError


def test_headline_kpis_match_hand_calculation(transactions):
    assert kpis.gross_sales(transactions) == pytest.approx(205)
    assert kpis.cancellations(transactions) == pytest.approx(-20)
    assert kpis.net_sales(transactions) == pytest.approx(185)
    assert kpis.order_count(transactions) == 5
    assert kpis.average_order_value(transactions) == pytest.approx(41)
    assert kpis.units_sold(transactions) == 30
    assert kpis.cancellation_rate(transactions) == pytest.approx(20 / 205)


def test_postage_bad_debt_and_free_items_are_not_revenue(transactions):
    # Naive sum of every line would be 205 - 20 + 15 - 100 = 100.
    assert transactions["line_value"].sum() == pytest.approx(100)
    assert kpis.net_sales(transactions) == pytest.approx(185)


def test_kpis_without_duplicates(transactions_deduplicated):
    assert kpis.gross_sales(transactions_deduplicated) == pytest.approx(160)
    assert kpis.net_sales(transactions_deduplicated) == pytest.approx(140)
    assert kpis.order_count(transactions_deduplicated) == 5
    assert kpis.units_sold(transactions_deduplicated) == 20


def test_customer_kpis(transactions):
    assert kpis.active_customers(transactions) == 3
    assert kpis.repeat_customer_rate(transactions) == pytest.approx(1 / 3)
    # Row 7 (30) has no customer: identified share = 175 / 205.
    assert kpis.identified_sales_share(transactions) == pytest.approx(175 / 205)


def test_date_filter_is_inclusive_of_whole_end_day(transactions):
    january = kpis.filter_transactions(transactions, start="2024-01-01", end="2024-01-20")
    assert kpis.gross_sales(january) == pytest.approx(120)  # includes 14:00 on 20 Jan


def test_february_filter(transactions):
    february = kpis.filter_transactions(transactions, start="2024-02-01", end="2024-02-29")
    assert kpis.gross_sales(february) == pytest.approx(40)
    assert kpis.net_sales(february) == pytest.approx(20)


def test_country_filter(transactions):
    france = kpis.filter_transactions(transactions, countries=["France"])
    assert kpis.net_sales(france) == pytest.approx(135)


def test_empty_selection_gives_zero_and_undefined_average(transactions):
    empty = kpis.filter_transactions(transactions, start="2030-01-01")
    assert kpis.net_sales(empty) == 0
    assert kpis.order_count(empty) == 0
    assert kpis.average_order_value(empty) is None
    assert kpis.cancellation_rate(empty) is None


def test_start_after_end_is_rejected(transactions):
    with pytest.raises(InvalidParameterError, match="after"):
        kpis.filter_transactions(transactions, start="2024-03-01", end="2024-01-01")


def test_invalid_date_text_is_rejected(transactions):
    with pytest.raises(InvalidParameterError):
        kpis.filter_transactions(transactions, start="last Tuesday")


def test_gross_profit_unavailable_without_cost(transactions):
    with pytest.raises(MetricUnavailableError, match="no product cost"):
        kpis.gross_profit(transactions)


def test_gross_profit_with_cost(transactions):
    # Give every product a unit cost of 1: cost of goods sold = units on sale lines (30)
    # plus units on the cancellation line (-1) = 29. Profit = 185 - 29 = 156.
    with_cost = transactions.assign(**{UNIT_COST: 1.0})
    assert kpis.gross_profit(with_cost) == pytest.approx(156)


def test_gross_profit_unavailable_when_costs_missing(transactions):
    with_cost = transactions.assign(**{UNIT_COST: 1.0})
    with_cost.loc[0, UNIT_COST] = None
    with pytest.raises(MetricUnavailableError, match="no unit cost"):
        kpis.gross_profit(with_cost)


def test_customer_kpis_need_customer_column(transactions):
    with pytest.raises(MissingColumnError):
        kpis.active_customers(transactions.drop(columns="customer_id"))


def test_summary_contains_all_kpis(transactions):
    summary = kpis.kpi_summary(transactions)
    assert summary["net_sales"] == pytest.approx(185)
    assert summary["active_customers"] == 3
    assert summary["first_date"] == pd.Timestamp("2024-01-05 10:00")
