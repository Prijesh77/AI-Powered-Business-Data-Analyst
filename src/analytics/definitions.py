"""Shared column names, business rules and metric definitions.

Every other analytics module imports its names from here, so a rule is
defined exactly once. The METRICS dictionary is also the text the app (and
later the AI layer) shows when explaining how a number was calculated.
"""

from dataclasses import dataclass

# --- Canonical column names -------------------------------------------------
# Uploaded files use their own column names. They are renamed to these names
# once (see prepare.standardise_columns), so the KPI code never depends on a
# particular dataset.
INVOICE = "invoice"
PRODUCT_ID = "product_id"
PRODUCT_NAME = "product_name"
QUANTITY = "quantity"
INVOICE_DATE = "invoice_date"
UNIT_PRICE = "unit_price"
CUSTOMER_ID = "customer_id"
COUNTRY = "country"
UNIT_COST = "unit_cost"

REQUIRED_COLUMNS = (INVOICE, PRODUCT_ID, QUANTITY, INVOICE_DATE, UNIT_PRICE)
OPTIONAL_COLUMNS = (PRODUCT_NAME, CUSTOMER_ID, COUNTRY, UNIT_COST)

# Columns added by prepare.prepare_transactions.
LINE_VALUE = "line_value"
LINE_TYPE = "line_type"
IS_DUPLICATE = "is_exact_duplicate"

# --- Line types ---------------------------------------------------------------
# Every row is put in exactly one class. Only SALE and CANCELLATION lines
# count towards product revenue.
SALE = "sale"                                  # normal invoice, quantity > 0, price > 0
CANCELLATION = "cancellation"                  # cancelled / returned product line
STOCK_ADJUSTMENT = "stock_adjustment"          # normal invoice, quantity <= 0 (damages, losses...)
ZERO_PRICE = "zero_price"                      # quantity > 0 but price <= 0 (free items, samples)
NON_PRODUCT = "non_product"                    # postage, fees, manual entries, vouchers
ACCOUNTING_ADJUSTMENT = "accounting_adjustment"  # e.g. "Adjust bad debt" invoices

LINE_TYPES = (SALE, CANCELLATION, STOCK_ADJUSTMENT, ZERO_PRICE, NON_PRODUCT, ACCOUNTING_ADJUSTMENT)


@dataclass(frozen=True)
class LineRules:
    """Dataset conventions used to classify lines.

    cancellation_prefix: invoices starting with this are cancellations.
        If None, a negative quantity marks a cancellation instead.
    accounting_prefixes: invoices starting with these are accounting entries.
    non_product_codes / non_product_prefixes: product codes that are not
        merchandise (postage, fees, vouchers...).
    """

    cancellation_prefix: str | None = None
    accounting_prefixes: tuple[str, ...] = ()
    non_product_codes: frozenset[str] = frozenset()
    non_product_prefixes: tuple[str, ...] = ()


# --- UCI Online Retail II -----------------------------------------------------
# Source column for each canonical column (the real file's names, which differ
# from the UCI documentation: see docs/phase2_data_exploration.md, section 2).
ONLINE_RETAIL_II_MAPPING = {
    INVOICE: "Invoice",
    PRODUCT_ID: "StockCode",
    PRODUCT_NAME: "Description",
    QUANTITY: "Quantity",
    INVOICE_DATE: "InvoiceDate",
    UNIT_PRICE: "Price",
    CUSTOMER_ID: "Customer ID",
    COUNTRY: "Country",
}

# Reviewed by hand in Phase 2 (docs/eda/nonstandard_stockcodes.csv).
ONLINE_RETAIL_RULES = LineRules(
    cancellation_prefix="C",
    accounting_prefixes=("A",),
    non_product_codes=frozenset({
        "POST", "DOT", "C2", "M", "m", "D", "S", "B", "BANK CHARGES", "AMAZONFEE",
        "CRUK", "ADJUST", "ADJUST2", "TEST001", "TEST002", "GIFT",
    }),
    non_product_prefixes=("gift_",),
)

ONLINE_RETAIL_CURRENCY = "GBP"

# --- Metric definitions -------------------------------------------------------
METRICS = {
    "gross_sales": "Gross product sales = sum of Quantity x Unit Price over sale lines "
                   "(normal invoices, quantity > 0, price > 0, product codes only).",
    "cancellations": "Cancellations = sum of Quantity x Unit Price over cancellation lines of "
                     "product codes (a negative amount), dated by the cancellation date.",
    "net_sales": "Net product sales (revenue) = gross product sales + cancellations.",
    "orders": "Orders = number of distinct invoices that contain at least one sale line.",
    "average_order_value": "Average order value = gross product sales / orders.",
    "units_sold": "Units sold = sum of Quantity over sale lines.",
    "cancellation_rate": "Cancellation rate = -cancellations / gross product sales.",
    "active_customers": "Active customers = distinct customer IDs on sale lines "
                        "(lines without a customer ID are not counted).",
    "repeat_customer_rate": "Repeat customer rate = customers with 2 or more orders / active customers.",
    "gross_profit": "Gross profit = net product sales - cost of goods sold, where cost of goods "
                    "sold = sum of Quantity x Unit Cost over sale and cancellation lines. "
                    "Only available when a unit cost column is mapped.",
}
