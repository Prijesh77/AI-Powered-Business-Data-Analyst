"""Consistency check against the Phase 2 EDA figures on the real dataset.

These tests are skipped when the dataset has not been downloaded. Note: the
EDA script and this engine were written by the same person, so agreement shows
consistency, not independent correctness. Independent checks are the
hand-calculated unit tests and the manual Excel check in docs/phase3_analytics_engine.md.
"""

import pytest

from src.analytics import breakdowns, kpis
from src.analytics.definitions import ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES
from src.analytics.prepare import prepare_transactions
from src.data.online_retail import DEFAULT_PATH, load_online_retail_ii

pytestmark = [
    pytest.mark.dataset,
    pytest.mark.skipif(not DEFAULT_PATH.exists(), reason="Online Retail II not downloaded"),
]


@pytest.fixture(scope="module")
def retail():
    return prepare_transactions(load_online_retail_ii(), ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES)


def test_row_count_after_overlap_removal(retail):
    assert len(retail) == 1_044_848


def test_revenue_matches_phase2(retail):
    assert kpis.gross_sales(retail) == pytest.approx(19_700_954.46, abs=0.01)
    assert kpis.cancellations(retail) == pytest.approx(-719_692.94, abs=0.01)
    assert kpis.net_sales(retail) == pytest.approx(18_981_261.52, abs=0.01)


def test_revenue_without_duplicates_matches_phase2():
    deduplicated = prepare_transactions(load_online_retail_ii(), ONLINE_RETAIL_II_MAPPING,
                                        ONLINE_RETAIL_RULES, drop_duplicates=True)
    assert kpis.net_sales(deduplicated) == pytest.approx(18_927_399.07, abs=0.01)


def test_top_product_matches_phase2(retail):
    top = breakdowns.top_n(retail, "product", n=3)
    assert top["product_id"].tolist() == ["22423", "85123A", "85099B"]
    assert top.loc[0, "net_sales"] == pytest.approx(314_513.47, abs=0.01)


def test_cancelled_bulk_order_is_not_a_top_product(retail):
    table = breakdowns.sales_by(retail, "product").set_index("product_id")
    assert table.loc["23843", "net_sales"] == pytest.approx(0, abs=0.01)


def test_november_sales_and_partial_last_month(retail):
    monthly = breakdowns.sales_over_time(retail, "month").set_index("period")
    assert monthly.loc["2010-11", "net_sales"] == pytest.approx(1_400_559.24, abs=0.01)
    assert monthly.loc["2011-11", "net_sales"] == pytest.approx(1_432_734.99, abs=0.01)
    assert monthly.loc["2011-12", "is_partial"]
    assert not monthly.loc["2009-12", "is_partial"]


def test_customer_figures_match_phase2(retail):
    assert kpis.active_customers(retail) == 5_852
    assert kpis.identified_sales_share(retail) == pytest.approx(0.869, abs=0.0005)
