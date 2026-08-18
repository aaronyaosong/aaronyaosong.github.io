from __future__ import annotations

import pytest

from nz_coffee_tracker.scrapers.shopify_roaster import (
    _filter_whole_bean_variants,
    _size_prices,
    _variant_size_grams,
)


def test_variant_size_grams_parses_various_weight_units() -> None:
    assert _variant_size_grams("250g") == 250.0
    assert _variant_size_grams("250GM / WHOLE BEANS") == 250.0
    assert _variant_size_grams("200GM / FILTER") == 200.0
    assert _variant_size_grams("500GM") == 500.0
    assert _variant_size_grams("250gms") == 250.0
    assert _variant_size_grams("250 gram") == 250.0
    assert _variant_size_grams("250 grams") == 250.0
    assert _variant_size_grams("1kg / WHOLE BEANS") == 1000.0
    assert _variant_size_grams("1KG") == 1000.0
    assert _variant_size_grams("1.5kg") == 1500.0
    assert _variant_size_grams("1 kgs") == 1000.0
    assert _variant_size_grams("60gm") == 60.0
    assert _variant_size_grams("No weight here") is None


def test_size_prices_extracts_all_valid_variants() -> None:
    variants = [
        {"available": True, "price": "26.50", "title": "250GM / WHOLE BEANS", "option1": "250GM"},
        {"available": True, "price": "95.40", "title": "1KG / WHOLE BEANS", "option1": "1KG"},
        {"available": False, "price": "26.50", "title": "250GM / FILTER", "option1": "250GM"},
    ]
    sizes = _size_prices(variants)
    assert sizes == [
        {"size_grams": 250.0, "price_nzd": 26.5},
        {"size_grams": 1000.0, "price_nzd": 95.4},
    ]


def test_size_prices_falls_back_to_product_title_when_variant_is_default() -> None:
    variants = [
        {"available": True, "price": "95.00", "title": "Default Title"},
    ]
    sizes = _size_prices(variants, product_title="Finca Nuguo Geisha 60gm")
    assert sizes == [{"size_grams": 60.0, "price_nzd": 95.0}]


def test_filter_whole_bean_variants_filters_out_preground_grinds() -> None:
    variants = [
        {"title": "250GM / WHOLE BEANS", "option1": "250GM", "option2": "WHOLE BEANS"},
        {"title": "250GM / ESPRESSO", "option1": "250GM", "option2": "ESPRESSO"},
        {"title": "250GM / FILTER", "option1": "250GM", "option2": "FILTER"},
        {"title": "1KG / WHOLE BEANS", "option1": "1KG", "option2": "WHOLE BEANS"},
        {"title": "1KG / ESPRESSO", "option1": "1KG", "option2": "ESPRESSO"},
    ]
    wb = _filter_whole_bean_variants(variants)
    assert [v["title"] for v in wb] == ["250GM / WHOLE BEANS", "1KG / WHOLE BEANS"]


def test_filter_whole_bean_variants_keeps_unspecified_grind_variants() -> None:
    variants = [
        {"title": "250g"},
        {"title": "1kg"},
    ]
    wb = _filter_whole_bean_variants(variants)
    assert wb == variants

