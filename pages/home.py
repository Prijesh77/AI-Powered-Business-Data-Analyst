import streamlit as st

from src import ui_state

st.title("AI-Powered Business Data Analyst")
st.write(
    "Upload your sales transactions, check their quality, and explore your key business "
    "figures. Every number is calculated directly from your data with documented rules."
)

st.subheader("How it works")
st.markdown(
    """
1. **Upload & map** - upload a CSV or Excel file and tell the app which column is which.
2. **Data quality** - review problems found in the data and choose which cleaning steps to apply.
3. **Dashboard** - see revenue, orders, top products, countries, customers and trends, with filters.

*Asking questions in plain English is added in a later phase.*
"""
)

st.subheader("Your data")
if ui_state.RAW in st.session_state:
    raw = st.session_state[ui_state.RAW]
    st.success(f"Loaded **{st.session_state[ui_state.FILE_NAME]}**: {len(raw):,} rows, {raw.shape[1]} columns.")
    if ui_state.TRANSACTIONS in st.session_state:
        st.page_link("pages/dashboard.py", label="Open the dashboard", icon=":material/dashboard:")
    else:
        st.page_link("pages/data_quality.py", label="Continue to data quality", icon=":material/fact_check:")
else:
    st.page_link("pages/upload.py", label="Upload a file to start", icon=":material/upload_file:")

st.caption(
    "Privacy: your file stays in this browser session's memory only. It is not saved to disk, "
    "not shared with other users, and not sent to any external service. Closing the tab discards it."
)
