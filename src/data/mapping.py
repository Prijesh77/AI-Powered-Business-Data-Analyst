"""Suggest and check the column mapping (file column -> canonical column).

The suggestion is only a starting point: the user confirms it on screen.
"""

import re

import pandas as pd

from src.analytics.definitions import (
    COUNTRY, CUSTOMER_ID, INVOICE, INVOICE_DATE, LineRules, ONLINE_RETAIL_RULES, OPTIONAL_COLUMNS,
    PRODUCT_ID, PRODUCT_NAME, QUANTITY, REQUIRED_COLUMNS, UNIT_COST, UNIT_PRICE,
)

# Known column names, compared after lower-casing and removing spaces/symbols.
SYNONYMS = {
    INVOICE: ["invoice", "invoiceno", "invoicenumber", "invoiceid", "orderid", "orderno",
              "ordernumber", "transactionid", "receiptno"],
    PRODUCT_ID: ["stockcode", "productid", "productcode", "sku", "itemcode", "itemid"],
    PRODUCT_NAME: ["description", "productname", "itemname", "product", "item"],
    QUANTITY: ["quantity", "qty", "units", "unitssold"],
    INVOICE_DATE: ["invoicedate", "orderdate", "transactiondate", "date", "datetime"],
    UNIT_PRICE: ["price", "unitprice", "priceeach", "sellingprice"],
    CUSTOMER_ID: ["customerid", "customerno", "customernumber", "clientid", "customer"],
    COUNTRY: ["country"],
    UNIT_COST: ["unitcost", "costprice", "cost"],
}

LABELS = {
    INVOICE: "Invoice / order number",
    PRODUCT_ID: "Product code",
    PRODUCT_NAME: "Product name",
    QUANTITY: "Quantity",
    INVOICE_DATE: "Date",
    UNIT_PRICE: "Unit price",
    CUSTOMER_ID: "Customer ID",
    COUNTRY: "Country",
    UNIT_COST: "Unit cost",
}

RULE_PRESETS = {
    "Online Retail conventions (C = cancellation, A = adjustment, fee codes excluded)": ONLINE_RETAIL_RULES,
    "Generic (negative quantity = cancellation)": LineRules(),
}


def normalise(name) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def suggest_mapping(columns) -> dict[str, str]:
    """Best guess {canonical: file column}; unknown columns are left unmapped."""
    by_normalised = {normalise(c): c for c in columns}
    mapping, used = {}, set()
    for canonical in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
        for synonym in SYNONYMS[canonical]:
            source = by_normalised.get(synonym)
            if source is not None and source not in used:
                mapping[canonical] = source
                used.add(source)
                break
    return mapping


def mapping_problems(mapping: dict[str, str], columns) -> list[str]:
    """Plain-language problems that block preparation (empty list = OK)."""
    problems = [f"Choose a column for '{LABELS[c]}' (required)." for c in REQUIRED_COLUMNS if c not in mapping]
    sources = list(mapping.values())
    repeated = sorted({s for s in sources if sources.count(s) > 1})
    if repeated:
        problems.append(f"Each file column can only be used once: {repeated}.")
    missing = [s for s in sources if s not in set(columns)]
    if missing:
        problems.append(f"Columns not in the file: {missing}.")
    return problems


def suggest_rule_preset(raw: pd.DataFrame, mapping: dict[str, str]) -> str:
    """Use the Online Retail preset when invoices look like 'C' + digits."""
    names = list(RULE_PRESETS)
    if INVOICE in mapping:
        invoices = raw[mapping[INVOICE]].dropna().astype(str)
        if invoices.str.match(r"^C\d+$").any():
            return names[0]
    return names[1]


def rules_with_codes(base: LineRules, codes_text: str) -> LineRules:
    """Replace the non-product codes with a comma/line separated list typed by the user.

    Entries ending in '*' are prefixes (e.g. 'gift_*').
    """
    entries = [e.strip() for e in re.split(r"[,\n]", codes_text) if e.strip()]
    return LineRules(
        cancellation_prefix=base.cancellation_prefix,
        accounting_prefixes=base.accounting_prefixes,
        non_product_codes=frozenset(e for e in entries if not e.endswith("*")),
        non_product_prefixes=tuple(e[:-1] for e in entries if e.endswith("*")),
    )


def codes_as_text(rules: LineRules) -> str:
    return ", ".join(sorted(rules.non_product_codes) + [p + "*" for p in rules.non_product_prefixes])
