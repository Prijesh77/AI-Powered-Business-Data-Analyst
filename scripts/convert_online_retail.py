"""Convert the UCI Online Retail II Excel workbook into a single Parquet file.

Why: reading the 45 MB .xlsx takes minutes, while Parquet loads in about a
second and keeps column types. The original Excel file is never modified.

Usage:
    python scripts/convert_online_retail.py
"""

from pathlib import Path

import pandas as pd

RAW_FILE = Path("data/raw/online_retail_ii/online_retail_II.xlsx")
OUT_FILE = Path("data/processed/online_retail_ii.parquet")

# Invoice and StockCode mix numbers and letters (e.g. "C489449", "POST"),
# so they must be read as text, otherwise Excel numbers and strings get mixed.
TEXT_COLUMNS = {"Invoice": str, "StockCode": str, "Description": str, "Country": str}


def main() -> None:
    if not RAW_FILE.exists():
        raise SystemExit(f"Raw file not found: {RAW_FILE}")

    sheets = pd.read_excel(RAW_FILE, sheet_name=None, dtype=TEXT_COLUMNS, engine="openpyxl")
    print(f"Sheets found: {list(sheets)}")

    frames = []
    for name, df in sheets.items():
        print(f"  {name}: {len(df):,} rows, columns = {list(df.columns)}")
        frames.append(df.assign(SourceSheet=name))

    combined = pd.concat(frames, ignore_index=True)
    print(f"Combined: {len(combined):,} rows")
    print(combined.dtypes)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUT_FILE, index=False)
    print(f"Saved {OUT_FILE}")


if __name__ == "__main__":
    main()
