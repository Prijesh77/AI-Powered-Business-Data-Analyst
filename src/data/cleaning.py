"""Reviewable cleaning steps and the cleaning log.

Workflow:
1. propose_cleaning() lists the steps that apply to this file, how many rows
   each one affects and whether it is on by default.
2. The user reviews them and switches optional steps on or off.
3. apply_cleaning() builds the analysis table and returns a log of what was done.

The uploaded data itself is never modified; a cleaned copy is created.
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.analytics.definitions import PRODUCT_ID, PRODUCT_NAME, LineRules
from src.analytics.prepare import prepare_transactions
from src.data.loader import SHEET_COLUMN
from src.data.profiling import invalid_values

CROSS_SHEET = "cross_sheet_duplicates"
INVALID_ROWS = "invalid_required_values"
EXACT_DUPLICATES = "exact_duplicates"


@dataclass
class CleaningStep:
    key: str
    title: str
    explanation: str
    rows_affected: int
    default: bool
    required: bool = False   # required steps cannot be switched off


def cross_sheet_duplicate_mask(raw: pd.DataFrame) -> pd.Series:
    """Rows that repeat a row already present in an earlier sheet.

    Copies are matched one-for-one: if a row appears twice in sheet 1 and twice
    in sheet 2, both sheet-2 copies are flagged; if it appears once in sheet 1
    and twice in sheet 2, only one sheet-2 copy is flagged.
    """
    if SHEET_COLUMN not in raw.columns or raw[SHEET_COLUMN].nunique() < 2:
        return pd.Series(False, index=raw.index)
    row_hash = pd.Series(
        pd.util.hash_pandas_object(raw.drop(columns=SHEET_COLUMN), index=False).to_numpy(),
        index=raw.index,
    )
    occurrence = row_hash.groupby([row_hash, raw[SHEET_COLUMN]], sort=False).cumcount()
    return pd.DataFrame({"hash": row_hash, "occurrence": occurrence}).duplicated(keep="first")


def _exact_duplicate_count(raw: pd.DataFrame, mapping: dict[str, str]) -> int:
    return int(raw[list(mapping.values())].duplicated().sum())


def propose_cleaning(raw: pd.DataFrame, mapping: dict[str, str], dayfirst: bool = False) -> list[CleaningStep]:
    steps = []
    current = raw

    cross = cross_sheet_duplicate_mask(current)
    if cross.any():
        steps.append(CleaningStep(
            CROSS_SHEET, "Remove rows repeated across sheets",
            "These rows already appear in an earlier sheet (for example, overlapping date ranges "
            "in yearly sheets). Keeping them would count the same transactions twice.",
            int(cross.sum()), default=True,
        ))
        current = current.loc[~cross]

    _, bad = invalid_values(current, mapping, dayfirst)
    if bad.any():
        steps.append(CleaningStep(
            INVALID_ROWS, "Remove rows with missing or unreadable required values",
            "Rows without a usable invoice, product, quantity, date or price cannot be analysed.",
            int(bad.sum()), default=True, required=True,
        ))
        current = current.loc[~bad]

    duplicates = _exact_duplicate_count(current, mapping)
    if duplicates:
        steps.append(CleaningStep(
            EXACT_DUPLICATES, "Remove exact duplicate lines",
            "Lines identical in every column. They may be data-entry errors or genuine repeat "
            "purchases of the same item on one invoice, so they are kept unless you choose otherwise.",
            duplicates, default=False,
        ))
    return steps


def apply_cleaning(
    raw: pd.DataFrame,
    mapping: dict[str, str],
    rules: LineRules,
    choices: dict[str, bool],
    dayfirst: bool = False,
) -> tuple[pd.DataFrame, list[dict]]:
    """Build the analysis table. choices maps step key -> apply? (missing = default)."""
    log = []
    timestamp = datetime.now().isoformat(timespec="seconds")

    def record(step: str, applied: bool, before: int, after: int, details: str) -> None:
        log.append({"time": timestamp, "step": step, "applied": applied,
                    "rows_before": before, "rows_after": after, "details": details})

    current = raw
    cross = cross_sheet_duplicate_mask(current)
    if cross.any():
        apply = choices.get(CROSS_SHEET, True)
        before = len(current)
        if apply:
            current = current.loc[~cross]
        record("Remove rows repeated across sheets", apply, before, len(current),
               f"{int(cross.sum()):,} repeated rows found.")

    _, bad = invalid_values(current, mapping, dayfirst)
    if bad.any():
        before = len(current)
        current = current.loc[~bad]
        record("Remove rows with missing or unreadable required values", True, before, len(current),
               f"{int(bad.sum()):,} rows could not be used.")

    drop_duplicates = choices.get(EXACT_DUPLICATES, False)
    duplicates = _exact_duplicate_count(current, mapping)
    tx = prepare_transactions(current, mapping, rules, drop_duplicates=drop_duplicates, dayfirst=dayfirst)
    if duplicates:
        record("Remove exact duplicate lines", drop_duplicates, len(current), len(tx),
               f"{duplicates:,} duplicate lines {'removed' if drop_duplicates else 'kept and flagged'}.")

    if PRODUCT_NAME in mapping:
        names = current.groupby(mapping[PRODUCT_ID])[mapping[PRODUCT_NAME]].nunique()
        record("Standardise product names", True, len(tx), len(tx),
               f"{int((names > 1).sum()):,} products had several descriptions; "
               "each now uses its most common one.")
    record("Classify lines (sale, cancellation, fee...)", True, len(tx), len(tx),
           "No rows removed. Only sale and cancellation lines count towards revenue.")
    return tx, log
