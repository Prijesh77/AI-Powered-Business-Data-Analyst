import pandas as pd
import streamlit as st

from src import ui_state
from src.analytics.errors import AnalyticsError
from src.data.cleaning import apply_cleaning, propose_cleaning
from src.data.profiling import (
    column_profile, invalid_values, line_type_summary, numeric_summary, outliers, quality_summary,
    top_values,
)
from src.visualization.charts import line_type_bar

st.title("Data quality")

raw: pd.DataFrame = ui_state.require(ui_state.RAW, "Upload a file first.", "pages/upload.py", "Go to Upload & map")
mapping = ui_state.require(ui_state.MAPPING, "Map the columns first.", "pages/upload.py", "Go to Upload & map")
rules = st.session_state[ui_state.RULES]
dayfirst = st.session_state[ui_state.DAYFIRST]
currency = st.session_state[ui_state.CURRENCY]

# --- 1. Profile of the uploaded file ------------------------------------------------
st.subheader("1. What the file contains")
with st.expander("Columns: types, missing values, distinct values", expanded=True):
    st.dataframe(column_profile(raw), width="stretch", hide_index=True,
                 column_config={"missing_pct": st.column_config.NumberColumn("missing %", format="%.2f")})
with st.expander("Numeric columns: summary statistics"):
    st.dataframe(numeric_summary(raw), width="stretch")
with st.expander("Most frequent values in a column"):
    column = st.selectbox("Column", list(raw.columns))
    st.dataframe(top_values(raw, column), width="stretch", hide_index=True,
                 column_config={"pct": st.column_config.NumberColumn("% of rows", format="%.2f")})

invalid_table, _ = invalid_values(raw, mapping, dayfirst)
if invalid_table[["missing", "invalid"]].to_numpy().sum():
    st.warning("Some required values are missing or unreadable:")
    st.dataframe(invalid_table, width="stretch", hide_index=True)
else:
    st.caption("All required columns have readable values in every row.")

# --- 2. Cleaning steps for review ------------------------------------------------------
st.subheader("2. Proposed cleaning steps")
st.caption("Nothing is changed until you press the button. Your uploaded data is kept unchanged; "
           "a cleaned copy is used for analysis.")
steps = propose_cleaning(raw, mapping, dayfirst)
choices = {}
if not steps:
    st.write("No rows need removing.")
for step in steps:
    label = f"{step.title} - **{step.rows_affected:,} rows**"
    choices[step.key] = st.checkbox(label, value=step.default, disabled=step.required,
                                    help=step.explanation, key=f"step_{step.key}")
    st.caption(step.explanation + (" (Required.)" if step.required else ""))
st.caption("Always applied (no rows removed): each product gets one name; every line is classified as "
           "sale, cancellation, fee, stock adjustment, etc. Outliers are flagged below, never removed.")

if st.button("Apply and build the analysis table", type="primary"):
    with st.spinner("Cleaning and preparing..."):
        try:
            transactions, log = apply_cleaning(raw, mapping, rules, choices, dayfirst)
        except AnalyticsError as error:
            st.error(str(error))
            st.stop()
    st.session_state[ui_state.TRANSACTIONS] = transactions
    st.session_state[ui_state.CLEANING_LOG] = log
    st.rerun()

if ui_state.TRANSACTIONS not in st.session_state:
    st.stop()

tx: pd.DataFrame = st.session_state[ui_state.TRANSACTIONS]

st.success("Analysis table ready.")
st.page_link("pages/dashboard.py", label="Open the dashboard", icon=":material/dashboard:")
with st.expander("Cleaning log", expanded=True):
    st.dataframe(pd.DataFrame(st.session_state[ui_state.CLEANING_LOG]), width="stretch", hide_index=True)

# --- 3. Quality indicators of the cleaned data --------------------------------------
st.subheader("3. Quality of the analysis table")
summary = quality_summary(tx)
m = st.columns(4)
m[0].metric("Rows", f"{summary['rows']:,}")
m[1].metric("Exact duplicates (kept, flagged)", f"{summary['exact_duplicates']:,}")
m[2].metric("Rows not counted as revenue", f"{summary['rows_outside_revenue']:,}",
            help="Postage, fees, stock adjustments, free items and accounting entries.")
if "sales_without_customer_pct" in summary:
    m[3].metric("Sales without a customer ID", f"{summary['sales_without_customer_pct']:.1f}%",
                help="Counted in revenue, but left out of customer analysis.")
st.caption(f"Dates: {summary['first_date']:%d %b %Y} to {summary['last_date']:%d %b %Y}.")
if summary["partial_months"]:
    st.info(f"Partial month(s): {', '.join(summary['partial_months'])}. The data does not cover the whole "
            "month, so sales there look lower than they really were.")

types = line_type_summary(tx)
left, right = st.columns([3, 2])
left.plotly_chart(line_type_bar(types.loc[types["lines"] > 0]), width="stretch")
right.dataframe(types, width="stretch", hide_index=True,
                column_config={"value": st.column_config.NumberColumn(f"value ({currency})", format="localized")})

st.markdown("**Unusually large sale lines (outliers)**")
st.caption("Outliers are candidates for review. In a wholesale business, large orders are often normal, "
           "so they are not removed.")
method = st.radio("Method", ["log_z", "iqr"], horizontal=True,
                  format_func={"log_z": "Strict (log z-score > 3)", "iqr": "Broad (IQR rule)"}.get)
flagged, rule = outliers(tx, method)
st.write(f"**{len(flagged):,}** sale lines flagged ({len(flagged) / max(len(tx), 1):.1%} of rows). Rule: {rule}.")
st.dataframe(flagged.head(20)[["invoice", "invoice_date", "product_name", "quantity", "unit_price", "line_value"]],
             width="stretch", hide_index=True)
