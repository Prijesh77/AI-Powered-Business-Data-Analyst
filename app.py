"""Streamlit entry point.

Run from the project folder:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="AI Business Data Analyst", page_icon=":material/analytics:", layout="wide")

pages = [
    st.Page("pages/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("pages/upload.py", title="Upload & map", icon=":material/upload_file:"),
    st.Page("pages/data_quality.py", title="Data quality", icon=":material/fact_check:"),
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
]
st.navigation(pages).run()
