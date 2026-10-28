import pytest

from src.analytics import breakdowns, kpis
from src.analytics.errors import InvalidParameterError, MissingColumnError


def test_sales_by_product(transactions):
    table = breakdowns.sales_by(transactions, "product")
    # MUG 10+45+45+5 = 105; PLATE 20+40-20 = 40; BOWL 30+10 = 40 (tie: lower ID first)
    assert table["product_id"].tolist() == ["10001", "10002", "10003"]
    assert table["product_name"].tolist() == ["MUG", "PLATE", "BOWL"]
    assert table["net_sales"].tolist() == pytest.approx([105, 40, 40])
    assert table["cancellations"].tolist() == pytest.approx([0, -20, 0])
    assert table["orders"].tolist() == [3, 2, 2]
    assert table["units_sold"].tolist() == [23, 3, 4]


def test_group_totals_add_up_to_kpi(transactions):
    for dimension in ("product", "country"):
        table = breakdowns.sales_by(transactions, dimension)
        assert table["net_sales"].sum() == pytest.approx(kpis.net_sales(transactions))
        assert table["share_of_net_sales"].sum() == pytest.approx(1)


def test_sales_by_country(transactions):
    table = breakdowns.sales_by(transactions, "country").set_index("country")
    assert table.loc["France", "net_sales"] == pytest.approx(135)
    assert table.loc["United Kingdom", "net_sales"] == pytest.approx(40)
    assert table.loc["Germany", "net_sales"] == pytest.approx(10)


def test_top_product(transactions):
    top = breakdowns.top_n(transactions, "product", n=1)
    assert top.loc[0, "product_name"] == "MUG"
    assert top.loc[0, "net_sales"] == pytest.approx(105)


def test_ties_share_a_rank(transactions):
    top = breakdowns.top_n(transactions, "product", n=3)
    assert top["rank"].tolist() == [1, 2, 2]


def test_bottom_products(transactions):
    bottom = breakdowns.top_n(transactions, "product", n=2, bottom=True)
    assert bottom["product_id"].tolist() == ["10002", "10003"]
    assert bottom["rank"].tolist() == [1, 1]


def test_top_by_units(transactions):
    top = breakdowns.top_n(transactions, "product", n=1, metric="units_sold")
    assert top.loc[0, "product_name"] == "MUG"
    assert top.loc[0, "units_sold"] == 23


@pytest.mark.parametrize("n", [0, -1, 2.5, True])
def test_invalid_n_is_rejected(transactions, n):
    with pytest.raises(InvalidParameterError):
        breakdowns.top_n(transactions, "product", n=n)


def test_unknown_metric_and_dimension_are_rejected(transactions):
    with pytest.raises(InvalidParameterError):
        breakdowns.top_n(transactions, "product", metric="profit")
    with pytest.raises(InvalidParameterError):
        breakdowns.sales_by(transactions, "category")


def test_dimension_needs_its_column(transactions):
    with pytest.raises(MissingColumnError):
        breakdowns.sales_by(transactions.drop(columns="country"), "country")


def test_monthly_sales(transactions):
    table = breakdowns.sales_over_time(transactions, "month")
    assert table["period"].tolist() == ["2024-01", "2024-02", "2024-03"]
    assert table["gross_sales"].tolist() == pytest.approx([120, 40, 45])
    assert table["cancellations"].tolist() == pytest.approx([0, -20, 0])
    assert table["net_sales"].tolist() == pytest.approx([120, 20, 45])
    assert table["orders"].tolist() == [2, 2, 1]
    assert table["average_order_value"].tolist() == pytest.approx([60, 20, 45])
    # Data starts on 5 Jan and ends on 3 Mar, so those months are partial.
    assert table["is_partial"].tolist() == [True, False, True]


def test_periods_without_sales_appear_as_zero(transactions):
    table = breakdowns.sales_over_time(transactions, "week")
    assert table["net_sales"].sum() == pytest.approx(185)
    assert (table["orders"] == 0).any()
    assert len(table) == 9  # Mon 1 Jan .. Sun 3 Mar 2024


def test_coverage_controls_partial_flag(transactions):
    table = breakdowns.sales_over_time(transactions, "month",
                                       coverage_start="2024-01-01", coverage_end="2024-03-31")
    assert not table["is_partial"].any()


def test_unknown_frequency_is_rejected(transactions):
    with pytest.raises(InvalidParameterError):
        breakdowns.sales_over_time(transactions, "quarter")


def test_empty_data_gives_empty_trend(transactions):
    empty = kpis.filter_transactions(transactions, start="2030-01-01")
    assert breakdowns.sales_over_time(empty).empty


def test_customer_summary(transactions):
    table = breakdowns.customer_summary(transactions).set_index("customer_id")
    assert list(table.index) == ["2", "1", "3"]
    assert table.loc["2", "net_sales"] == pytest.approx(135)
    assert table.loc["2", "orders"] == 2
    assert table.loc["1", "net_sales"] == pytest.approx(10)  # 30 bought - 20 cancelled
    assert str(table.loc["3", "first_purchase"]) == "2024-02-15 16:00:00"
