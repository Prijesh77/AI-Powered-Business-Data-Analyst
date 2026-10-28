"""Loader for the UCI Online Retail II development dataset.

Run scripts/convert_online_retail.py first to create the Parquet file.
"""

from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path("data/processed/online_retail_ii.parquet")

# Both workbook sheets contain 2010-12-01 .. 2010-12-09 (an exact copy, verified
# in Phase 2), so the first sheet's copy of those days is dropped.
OVERLAP_SHEET = "Year 2009-2010"
OVERLAP_START = pd.Timestamp("2010-12-01")


def remove_sheet_overlap(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop the duplicated 1-9 Dec 2010 rows and the SourceSheet helper column."""
    overlap = (raw["SourceSheet"] == OVERLAP_SHEET) & (raw["InvoiceDate"] >= OVERLAP_START)
    return raw.loc[~overlap].drop(columns="SourceSheet").reset_index(drop=True)


def load_online_retail_ii_workbook(path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Both sheets as stored in the workbook (overlap included, SourceSheet column kept).

    This is what a user would get by uploading the .xlsx with both sheets; the
    app's cleaning step then finds and removes the overlap.
    """
    if not Path(path).exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'python scripts/convert_online_retail.py' first."
        )
    return pd.read_parquet(path)


def load_online_retail_ii(path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Return the raw transactions (original column names) without the sheet overlap."""
    if not Path(path).exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'python scripts/convert_online_retail.py' first."
        )
    return remove_sheet_overlap(pd.read_parquet(path))
