import pandas as pd
import streamlit as st

from src import ui_state
from src.analytics.definitions import ONLINE_RETAIL_CURRENCY, OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from src.data.loader import MAX_FILE_MB, UploadError, list_sheets, read_upload
from src.data.mapping import (
    LABELS, RULE_PRESETS, codes_as_text, mapping_problems, rules_with_codes, suggest_mapping,
    suggest_rule_preset,
)
from src.data.online_retail import DEFAULT_PATH, load_online_retail_ii_workbook
from src.data.profiling import column_profile

NOT_IN_FILE = "(not in file)"

st.title("Upload & map")

# --- 1. Choose a file ----------------------------------------------------------
st.subheader("1. Choose your data")
uploaded = st.file_uploader(
    f"CSV or Excel (.xlsx) file, up to {MAX_FILE_MB} MB", type=["csv", "xlsx"],
    help="Macro-enabled (.xlsm) and old (.xls) Excel files are not accepted.",
)

if uploaded is not None:
    content = uploaded.getvalue()
    sheets = None
    if uploaded.name.lower().endswith(".xlsx"):
        try:
            available = list_sheets(content)
        except Exception:
            st.error("This Excel file could not be opened. It may be damaged or not a real .xlsx file.")
            st.stop()
        if len(available) > 1:
            sheets = st.multiselect("Sheets to load (they must have the same columns)", available,
                                    default=available)
    if st.button("Load file", type="primary"):
        with st.spinner("Reading the file... large Excel files can take a minute."):
            try:
                loaded = read_upload(uploaded.name, content, sheets)
            except UploadError as error:
                st.error(str(error))
                st.stop()
        ui_state.set_raw(loaded.data, loaded.name, loaded.notes)
        st.rerun()

if DEFAULT_PATH.exists():
    st.caption("No file at hand? Use the development dataset (UCI Online Retail II, both sheets).")
    if st.button("Use the Online Retail II sample"):
        with st.spinner("Loading sample..."):
            ui_state.set_raw(load_online_retail_ii_workbook(), "Online Retail II (sample)",
                             ["Loaded both workbook sheets from the local development copy."])
        st.rerun()

if ui_state.RAW not in st.session_state:
    st.stop()

raw: pd.DataFrame = st.session_state[ui_state.RAW]
upload_id = st.session_state[ui_state.UPLOAD_ID]

# --- 2. Preview ------------------------------------------------------------------
st.subheader("2. Preview")
st.success(f"**{st.session_state[ui_state.FILE_NAME]}** loaded.")
c1, c2 = st.columns(2)
c1.metric("Rows", f"{len(raw):,}")
c2.metric("Columns", raw.shape[1])
for note in st.session_state[ui_state.LOAD_NOTES]:
    st.caption(note)
st.dataframe(raw.head(100), width="stretch", height=260)
with st.expander("Column names, types and missing values"):
    st.dataframe(column_profile(raw), width="stretch", hide_index=True,
                 column_config={"missing_pct": st.column_config.NumberColumn("missing %", format="%.2f")})

# --- 3. Column mapping -----------------------------------------------------------
st.subheader("3. Tell the app which column is which")
st.caption("Suggestions are pre-filled from the column names. Required fields are marked *.")

columns = [c for c in raw.columns if c != "SourceSheet"]
suggested = st.session_state.get(ui_state.MAPPING) or suggest_mapping(columns)
options = [NOT_IN_FILE] + [str(c) for c in columns]
mapping = {}
grid = st.columns(3)
for i, canonical in enumerate(REQUIRED_COLUMNS + OPTIONAL_COLUMNS):
    label = LABELS[canonical] + (" *" if canonical in REQUIRED_COLUMNS else "")
    default = suggested.get(canonical, NOT_IN_FILE)
    choice = grid[i % 3].selectbox(label, options, index=options.index(str(default)) if str(default) in options else 0,
                                   key=f"map_{canonical}_{upload_id}")
    if choice != NOT_IN_FILE:
        mapping[canonical] = next(c for c in columns if str(c) == choice)

# --- 4. Business rules -----------------------------------------------------------
st.subheader("4. Business rules")
preset_names = list(RULE_PRESETS)
default_preset = suggest_rule_preset(raw, mapping) if not mapping_problems(mapping, columns) else preset_names[1]
preset = st.radio("How are cancellations and adjustments recorded?", preset_names,
                  index=preset_names.index(default_preset), key=f"preset_{upload_id}")
codes = st.text_area(
    "Product codes that are not products (postage, fees, vouchers...). Separate with commas; "
    "end with * for 'starts with'.",
    value=codes_as_text(RULE_PRESETS[preset]), key=f"codes_{upload_id}_{preset}",
)
r1, r2 = st.columns(2)
currency = r1.text_input("Currency of the prices", key=f"currency_{upload_id}",
                         value=ONLINE_RETAIL_CURRENCY if preset == preset_names[0] else "")
date_is_text = "invoice_date" in mapping and not pd.api.types.is_datetime64_any_dtype(raw[mapping["invoice_date"]])
dayfirst = r2.checkbox("Dates are written day first (e.g. 03/04/2011 = 3 April)", value=False,
                       disabled=not date_is_text, key=f"dayfirst_{upload_id}",
                       help="Only needed when dates are stored as text.")

problems = mapping_problems(mapping, columns)
for problem in problems:
    st.error(problem)

if st.button("Save and continue to data quality", type="primary", disabled=bool(problems)):
    st.session_state[ui_state.MAPPING] = mapping
    st.session_state[ui_state.RULES] = rules_with_codes(RULE_PRESETS[preset], codes)
    st.session_state[ui_state.DAYFIRST] = dayfirst
    st.session_state[ui_state.CURRENCY] = currency.strip()
    ui_state.clear_analysis()
    st.switch_page("pages/data_quality.py")
