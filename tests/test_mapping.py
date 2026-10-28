import pandas as pd

from src.analytics.definitions import ONLINE_RETAIL_II_MAPPING
from src.data.mapping import (
    RULE_PRESETS, codes_as_text, mapping_problems, rules_with_codes, suggest_mapping, suggest_rule_preset,
)


def test_suggests_online_retail_mapping(raw_sample):
    assert suggest_mapping(raw_sample.columns) == ONLINE_RETAIL_II_MAPPING


def test_suggests_generic_names():
    columns = ["Order ID", "SKU", "Product Name", "Qty", "Order Date", "Unit Price", "Unit Cost", "Region"]
    mapping = suggest_mapping(columns)
    assert mapping == {
        "invoice": "Order ID", "product_id": "SKU", "product_name": "Product Name", "quantity": "Qty",
        "invoice_date": "Order Date", "unit_price": "Unit Price", "unit_cost": "Unit Cost",
    }


def test_missing_required_and_repeated_columns_are_problems():
    problems = mapping_problems({"invoice": "A", "product_id": "A"}, ["A", "B"])
    assert any("Quantity" in p for p in problems)
    assert any("only be used once" in p for p in problems)


def test_complete_mapping_has_no_problems(raw_sample):
    assert mapping_problems(ONLINE_RETAIL_II_MAPPING, raw_sample.columns) == []


def test_rule_preset_follows_invoice_style(raw_sample):
    names = list(RULE_PRESETS)
    assert suggest_rule_preset(raw_sample, ONLINE_RETAIL_II_MAPPING) == names[0]
    plain = pd.DataFrame({"Invoice": ["1", "2"]})
    assert suggest_rule_preset(plain, {"invoice": "Invoice"}) == names[1]


def test_codes_text_round_trip():
    rules = rules_with_codes(RULE_PRESETS[list(RULE_PRESETS)[0]], "POST, DOT\nfee_*")
    assert rules.non_product_codes == frozenset({"POST", "DOT"})
    assert rules.non_product_prefixes == ("fee_",)
    assert rules.cancellation_prefix == "C"
    assert codes_as_text(rules) == "DOT, POST, fee_*"
