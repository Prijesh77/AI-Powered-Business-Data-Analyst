import pandas as pd
import streamlit as st

from src import ui_state
from src.analytics import breakdowns, kpis
from src.analytics.definitions import COUNTRY, CUSTOMER_ID, INVOICE_DATE, METRICS
from src.analytics.errors import AnalyticsError
from src.data.profiling import quality_summary
from src.visualization.charts import ranking_bar, sales_trend

st.title("Dashboard")

tx: pd.DataFrame = ui_state.require(ui_state.TRANSACTIONS, "Prepare your data on the Data quality page first.",
                                    "pages/data_quality.py", "Go to Data quality")
currency = st.session_state.get(ui_state.CURRENCY, "")

# --- Filters (one row above the charts) -----------------------------------------------
first_day, last_day = tx[INVOICE_DATE].min().date(), tx[INVOICE_DATE].max().date()
f1, f2, f3 = st.columns([2, 3, 1])
date_range = f1.date_input("Date range", value=(first_day, last_day),
                           min_value=first_day, max_value=last_day)
has_country = COUNTRY in tx.columns
countries = f2.multiselect("Countries", sorted(tx[COUNTRY].dropna().unique()), placeholder="All countries") \
    if has_country else []
freq = f3.selectbox("Trend by", ["month", "week", "day"])

if not isinstance(date_range, tuple) or len(date_range) != 2:
    st.info("Choose an end date to complete the date range.")
    st.stop()
start, end = date_range
try:
    selected = kpis.filter_transactions(tx, start=start, end=end, countries=countries or None)
except AnalyticsError as error:
    st.error(str(error))
    st.stop()

st.caption(f"Showing {start:%d %b %Y} to {end:%d %b %Y}"
           + (f", countries: {', '.join(countries)}" if countries else ", all countries")
           + f" - {len(selected):,} rows.")
if kpis.order_count(selected) == 0:
    st.warning("No sales match these filters.")
    st.stop()

# --- KPI cards --------------------------------------------------------------------------
summary = kpis.kpi_summary(selected)
cards = st.columns(3) + st.columns(3)  # two rows, so long money values are not cut off
cards[0].metric("Net sales (revenue)", ui_state.money(summary["net_sales"], currency), help=METRICS["net_sales"])
cards[1].metric("Orders", f"{summary['orders']:,}", help=METRICS["orders"])
cards[2].metric("Average order value", ui_state.money(summary["average_order_value"], currency),
                help=METRICS["average_order_value"])
cards[3].metric("Units sold", f"{summary['units_sold']:,}", help=METRICS["units_sold"])
rate = summary["cancellation_rate"]
cards[4].metric("Cancellation rate", "n/a" if rate is None else f"{rate:.1%}", help=METRICS["cancellation_rate"])
if "active_customers" in summary:
    cards[5].metric("Active customers", f"{summary['active_customers']:,}", help=METRICS["active_customers"])

# --- Trend ----------------------------------------------------------------------------
trend = breakdowns.sales_over_time(selected, freq, coverage_start=start, coverage_end=end)
st.plotly_chart(sales_trend(trend, freq, currency), width="stretch")
if trend["is_partial"].any():
    st.caption("Hatched bars / hollow markers are partial periods: the selected dates do not cover the "
               "whole period, so its total is not comparable with the others.")
with st.expander("Trend table"):
    st.dataframe(trend.drop(columns=["period_start", "period_end"]), width="stretch", hide_index=True)

# --- Products ---------------------------------------------------------------------------
st.subheader("Products")
p1, p2, p3 = st.columns(3)
direction = p1.radio("Show", ["Top", "Bottom"], horizontal=True)
metric = p2.selectbox("Rank by", list(breakdowns.RANKING_METRICS),
                      format_func=lambda m: m.replace("_", " ").capitalize())
n = p3.slider("Number of products", 5, 25, 10)
products = breakdowns.top_n(selected, "product", n=n, metric=metric, bottom=direction == "Bottom")
left, right = st.columns([3, 2])
left.plotly_chart(ranking_bar(products, "product_name", metric,
                              f"{direction} {n} products by {metric.replace('_', ' ')}", currency,
                              metric.replace("_", " ").capitalize()), width="stretch")
right.dataframe(products[["rank", "product_id", "product_name", metric, "orders"]].rename(
    columns={metric: metric.replace("_", " ")}), width="stretch", hide_index=True, height=420)
if direction == "Bottom":
    st.caption("Bottom products only include products with at least one sale in the selected period.")

# --- Countries and customers --------------------------------------------------------------
left, right = st.columns(2)
if has_country:
    by_country = breakdowns.sales_by(selected, "country").head(10)
    left.plotly_chart(ranking_bar(by_country, "country", "net_sales", "Top 10 countries by net sales", currency),
                      width="stretch")
if CUSTOMER_ID in tx.columns:
    customers = breakdowns.customer_summary(selected).head(10)
    right.plotly_chart(ranking_bar(customers, CUSTOMER_ID, "net_sales", "Top 10 customers by net sales", currency),
                       width="stretch")
    share, repeat = summary["identified_sales_share"], summary["repeat_customer_rate"]
    if repeat is None:
        right.caption("No sales in this selection have a customer ID.")
    else:
        right.caption(f"Customer figures cover {share:.1%} of gross sales: the rest has no customer ID. "
                      f"Repeat-customer rate: {repeat:.1%}.")

# --- Data quality reminder and definitions ----------------------------------------------
quality = quality_summary(tx)
st.divider()
st.caption(
    f"Data quality: {quality['exact_duplicates']:,} exact duplicate lines kept and flagged; "
    f"{quality['rows_outside_revenue']:,} rows (fees, adjustments, free items) not counted as revenue"
    + (f"; partial month(s): {', '.join(quality['partial_months'])}" if quality["partial_months"] else "")
    + ". See the Data quality page for details."
)
with st.expander("How these numbers are calculated"):
    for name, definition in METRICS.items():
        st.markdown(f"- **{name.replace('_', ' ').capitalize()}**: {definition}")
    st.markdown("- **Date filter**: start and end dates are both included. Weeks run Monday to Sunday.")
