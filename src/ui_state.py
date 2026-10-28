"""Names and helpers for the data kept in each user's Streamlit session.

st.session_state is private to one browser session, so one user's dataset is
never visible to another. Nothing here is written to disk. (We deliberately do
not use st.cache_data for uploads: that cache is shared by all sessions.)
"""

import streamlit as st

RAW = "raw"                  # uploaded table, never modified
FILE_NAME = "file_name"
LOAD_NOTES = "load_notes"
MAPPING = "mapping"          # {canonical column: file column}
RULES = "rules"              # LineRules
DAYFIRST = "dayfirst"
CURRENCY = "currency"
TRANSACTIONS = "transactions"  # prepared, cleaned analysis table
CLEANING_LOG = "cleaning_log"
UPLOAD_ID = "upload_id"      # changes with every new file, so widgets reset


def set_raw(raw, file_name: str, notes: list[str]) -> None:
    for key in (MAPPING, RULES, TRANSACTIONS, CLEANING_LOG):
        st.session_state.pop(key, None)
    st.session_state[RAW] = raw
    st.session_state[FILE_NAME] = file_name
    st.session_state[LOAD_NOTES] = notes
    st.session_state[UPLOAD_ID] = st.session_state.get(UPLOAD_ID, 0) + 1


def clear_analysis() -> None:
    """Forget the cleaned table (e.g. after the mapping changes)."""
    for key in (TRANSACTIONS, CLEANING_LOG):
        st.session_state.pop(key, None)


def require(key: str, message: str, page: str, label: str):
    """Return the session value, or show a hint with a link and stop the page."""
    if key not in st.session_state:
        st.info(message)
        st.page_link(page, label=label, icon=":material/arrow_forward:")
        st.stop()
    return st.session_state[key]


def money(value, currency: str) -> str:
    if value is None:
        return "n/a"
    return f"{currency} {value:,.2f}".strip()
