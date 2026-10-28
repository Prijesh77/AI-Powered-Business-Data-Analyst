"""Shared test data: a small hand-made dataset whose answers were worked out on paper.

Rows (original Online Retail column names, so the mapping is tested too):

 #  Invoice StockCode Description      Qty  Date              Price  Cust Country  -> line type       value
 1  1001    10001     MUG                2  2024-01-05 10:00   5.00   1   UK       -> sale              10
 2  1001    10002     PLATE              1  2024-01-05 10:00  20.00   1   UK       -> sale              20
 3  1001    POST      POSTAGE            1  2024-01-05 10:00  15.00   1   UK       -> non_product       15
 4  1002    10001     MUG               10  2024-01-20 14:00   4.50   2   France   -> sale              45
 5  1002    10001     MUG               10  2024-01-20 14:00   4.50   2   France   -> sale (duplicate)  45
 6  C1003   10002     PLATE             -1  2024-02-02 09:00  20.00   1   UK       -> cancellation     -20
 7  1004    10003     (missing)          3  2024-02-10 11:00  10.00   -   UK       -> sale              30
 8  1005    10003     BOWL               1  2024-02-15 16:00  10.00   3   Germany  -> sale              10
 9  1006    10004     damaged           -5  2024-02-16 08:00   0.00   -   UK       -> stock_adjustment   0
10  A1007   B         Adjust bad debt    1  2024-02-20 10:00 -100.00  -   UK       -> accounting_adj. -100
11  1008    10005     GIFT BOX           4  2024-03-01 12:00   0.00   3   Germany  -> zero_price         0
12  1009    10002     PLATE              2  2024-03-03 13:00  20.00   2   France   -> sale              40
13  1009    10001     MUG                1  2024-03-03 13:05   5.00   2   France   -> sale               5

Hand-calculated answers (duplicates kept):
  gross sales   = 10+20+45+45+30+10+40+5 = 205
  cancellations = -20                   -> net sales = 185
  orders        = {1001,1002,1004,1005,1009} = 5 -> average order value = 205/5 = 41
  units sold    = 2+1+10+10+3+1+2+1 = 30
  customers     = {1,2,3} = 3; customer 2 has 2 orders -> repeat rate 1/3
  with the duplicate (row 5) removed: gross 160, net 140, units 20, orders still 5
"""

import pandas as pd
import pytest

from src.analytics.definitions import ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES
from src.analytics.prepare import prepare_transactions

NAN = float("nan")

ROWS = [
    ("1001", "10001", "MUG", 2, "2024-01-05 10:00", 5.00, 1.0, "United Kingdom"),
    ("1001", "10002", "PLATE", 1, "2024-01-05 10:00", 20.00, 1.0, "United Kingdom"),
    ("1001", "POST", "POSTAGE", 1, "2024-01-05 10:00", 15.00, 1.0, "United Kingdom"),
    ("1002", "10001", "MUG", 10, "2024-01-20 14:00", 4.50, 2.0, "France"),
    ("1002", "10001", "MUG", 10, "2024-01-20 14:00", 4.50, 2.0, "France"),
    ("C1003", "10002", "PLATE", -1, "2024-02-02 09:00", 20.00, 1.0, "United Kingdom"),
    ("1004", "10003", None, 3, "2024-02-10 11:00", 10.00, NAN, "United Kingdom"),
    ("1005", "10003", "BOWL", 1, "2024-02-15 16:00", 10.00, 3.0, "Germany"),
    ("1006", "10004", "damaged", -5, "2024-02-16 08:00", 0.00, NAN, "United Kingdom"),
    ("A1007", "B", "Adjust bad debt", 1, "2024-02-20 10:00", -100.00, NAN, "United Kingdom"),
    ("1008", "10005", "GIFT BOX", 4, "2024-03-01 12:00", 0.00, 3.0, "Germany"),
    ("1009", "10002", "PLATE", 2, "2024-03-03 13:00", 20.00, 2.0, "France"),
    ("1009", "10001", "MUG", 1, "2024-03-03 13:05", 5.00, 2.0, "France"),
]
COLUMNS = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]


@pytest.fixture
def raw_sample() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=COLUMNS)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


@pytest.fixture
def transactions(raw_sample) -> pd.DataFrame:
    return prepare_transactions(raw_sample, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES)


@pytest.fixture
def transactions_deduplicated(raw_sample) -> pd.DataFrame:
    return prepare_transactions(raw_sample, ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES,
                                drop_duplicates=True)
