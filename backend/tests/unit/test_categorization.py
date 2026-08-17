from __future__ import annotations

import pytest

from nz_coffee_tracker.categorization import (
    ESPRESSO_ROAST,
    FILTER_ROAST,
    OTHER_CATEGORY,
    category_values,
    infer_roast_category,
)


@pytest.mark.unit
def test_infer_roast_category_filter_only() -> None:
    # Filter keyword in title should map to filter roast category.
    product = {
        "title": "Colombia Single Origin Filter Roast",
        "variants": [{"title": "250g"}],
    }
    assert infer_roast_category(product) == FILTER_ROAST


@pytest.mark.unit
def test_infer_roast_category_espresso_only() -> None:
    # Espresso keyword in tags should still be discovered.
    product = {
        "title": "House Blend",
        "tags": "espresso,blend",
        "variants": [{"title": "1kg"}],
    }
    assert infer_roast_category(product) == ESPRESSO_ROAST


@pytest.mark.unit
def test_infer_roast_category_both() -> None:
    # Dual-use roast descriptions should carry both category values.
    product = {
        "title": "Omni Roast",
        "body_html": "Works as filter and espresso.",
        "variants": [{"title": "200g"}],
    }
    assert infer_roast_category(product) == f"{FILTER_ROAST},{ESPRESSO_ROAST}"


@pytest.mark.unit
def test_infer_roast_category_other() -> None:
    # Non-coffee merch should not be tagged as a roast category.
    product = {
        "title": "Tea Towel",
        "tags": "merch,home",
        "variants": [{"title": "Standard"}],
    }
    assert infer_roast_category(product) == OTHER_CATEGORY


@pytest.mark.unit
def test_category_values_split_and_trim() -> None:
    assert category_values("filter roast, espresso roast") == {"filter roast", "espresso roast"}
