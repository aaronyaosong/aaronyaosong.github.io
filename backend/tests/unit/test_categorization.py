from __future__ import annotations

import pytest

from nz_coffee_tracker.categorization import (
    ESPRESSO_ROAST,
    FILTER_ROAST,
    OTHER_CATEGORY,
    category_values,
    description_text,
    infer_flavour_notes,
    infer_origin_country,
    infer_process,
    infer_producer,
    infer_roast_category,
    infer_varietal,
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


@pytest.mark.unit
def test_infer_varietal_detects_multiple_varieties() -> None:
    product = {"title": "Don Claudio Project - Caturra - Catuai - Obata"}
    assert infer_varietal(product) == "caturra,catuai,obata"


@pytest.mark.unit
def test_infer_varietal_unknown_when_not_present() -> None:
    assert infer_varietal({"title": "House Espresso Blend"}) == "unknown"


@pytest.mark.unit
def test_extracts_metadata_and_flavour_notes_from_description() -> None:
    product = {
        "title": "Elena Coffee",
        "body_html": "<p>Origin: Colombia</p><p>Producer: Elena Farm</p><p>Process: washed</p><p>Flavour notes: plum, cocoa and caramel</p>",
    }
    assert description_text(product) == "Origin: Colombia Producer: Elena Farm Process: washed Flavour notes: plum, cocoa and caramel"
    assert infer_origin_country(product) == "Colombia"
    assert infer_producer(product) == "Elena Farm"
    assert infer_process(product) == "washed"
    assert infer_flavour_notes(product) == "plum, cocoa and caramel"
