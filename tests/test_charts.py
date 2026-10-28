"""Charts must show exactly the numbers in the tables they are built from."""

import pytest

from src.analytics import breakdowns
from src.visualization.charts import ranking_bar, sales_trend


def test_monthly_chart_matches_trend_table(transactions):
    trend = breakdowns.sales_over_time(transactions, "month")
    fig = sales_trend(trend, "month", "GBP")
    complete, partial = fig.data
    assert list(complete.y) == pytest.approx(trend.loc[~trend["is_partial"], "net_sales"].tolist())
    assert list(partial.y) == pytest.approx(trend.loc[trend["is_partial"], "net_sales"].tolist())
    assert sum(complete.y) + sum(partial.y) == pytest.approx(185)
    assert partial.marker.pattern.shape == "/"   # partial periods are not marked by colour alone


def test_weekly_chart_is_a_line_with_partial_markers(transactions):
    trend = breakdowns.sales_over_time(transactions, "week")
    line, markers = sales_trend(trend, "week").data
    assert line.mode == "lines" and len(line.y) == len(trend)
    assert len(markers.y) == trend["is_partial"].sum()


def test_ranking_chart_matches_table(transactions):
    table = breakdowns.top_n(transactions, "product", n=3)
    bar = ranking_bar(table, "product_name", "net_sales", "Top products", "GBP").data[0]
    assert list(bar.x) == pytest.approx(table["net_sales"].tolist()[::-1])
    assert list(bar.y) == table["product_name"].tolist()[::-1]
    assert bar.text[-1] == "GBP 105"


def test_numeric_looking_labels_stay_categories(transactions):
    table = breakdowns.customer_summary(transactions)
    fig = ranking_bar(table, "customer_id", "net_sales", "Top customers")
    assert fig.layout.yaxis.type == "category"
