from __future__ import annotations

import pytest

from nz_coffee_tracker.categorization import (
    ESPRESSO_ROAST,
    FILTER_ROAST,
    OMNI_ROAST,
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
    # Filter keyword in title should map to filter roast category when no tags present.
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
def test_infer_roast_category_both_is_omni() -> None:
    # Dual-use roast descriptions should carry omni roast.
    product = {
        "title": "Omni Roast",
        "body_html": "Works as filter and espresso.",
        "variants": [{"title": "200g"}],
    }
    assert infer_roast_category(product) == OMNI_ROAST


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
def test_infer_roast_category_ignores_grind_options_and_variants() -> None:
    # An espresso blend that offers both Filter and Espresso grind options should remain Espresso Roast.
    product = {
        "title": "Supreme House Blend",
        "tags": ["blend"],
        "options": [
            {"name": "Grind", "values": ["Whole Bean", "Filter", "Espresso", "Plunger"]},
            {"name": "Size", "values": ["250g", "1kg"]},
        ],
        "variants": [
            {"title": "250g / Filter"},
            {"title": "250g / Espresso"},
            {"title": "1kg / Filter"},
        ],
    }
    assert infer_roast_category(product) == ESPRESSO_ROAST


@pytest.mark.unit
def test_infer_roast_category_checks_tags_first() -> None:
    # When explicit tags are present, they take priority
    assert infer_roast_category({"title": "Something", "tags": ["extraction-omni"]}) == OMNI_ROAST
    assert infer_roast_category({"title": "Something", "tags": ["extraction-filter"]}) == FILTER_ROAST
    assert infer_roast_category({"title": "Something", "tags": ["extraction-espresso"]}) == ESPRESSO_ROAST
    assert infer_roast_category({"title": "House Blend", "tags": ["Filter Roast"]}) == FILTER_ROAST


@pytest.mark.unit
def test_infer_roast_category_supports_roaster_tags() -> None:
    # Ozone tag style
    assert infer_roast_category({"title": "Popayan", "tags": ["brew method:Filter", "SINGLE ORIGIN"]}) == FILTER_ROAST
    assert infer_roast_category({"title": "Our House", "tags": ["brew method:Espresso", "blends"]}) == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Decaf", "tags": ["brew method:Espresso", "brew method:Filter"]}) == OMNI_ROAST

    # C4 tag style
    assert infer_roast_category({"title": "Santa Monica", "tags": ["extraction-filter", "micro-lot"]}) == FILTER_ROAST
    assert infer_roast_category({"title": "Stout Blend", "tags": ["extraction-espresso", "coffee-blend"]}) == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Huila Regional", "tags": ["extraction-omni", "single-origin"]}) == OMNI_ROAST


@pytest.mark.unit
def test_infer_roast_category_supports_collection_handles() -> None:
    # Subcollection context should inform roast category when tags are not explicit
    assert infer_roast_category({"title": "Narino"}, collection_handle="single-origins") == FILTER_ROAST
    assert infer_roast_category({"title": "Seasonal Blend"}, collection_handle="house-blends") == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Tropical Rush"}, collection_handle="specialty-coffee-beans-nz") == FILTER_ROAST
    assert infer_roast_category({"title": "Tropical Rush"}, collection_handle="espresso-offerings-1") == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Koke Shalaye"}, collection_handle="filter-extraction") == FILTER_ROAST


@pytest.mark.unit
def test_infer_roast_category_recommended_brewing_in_description() -> None:
    # Atomic Decaf style: recommended use with espresso and filter
    atomic_decaf = {
        "title": "Decaf",
        "body_html": "<p>Characteristics: body silky. Recommended use Espresso, stovetop, plunger, Aeropress, filter</p>",
    }
    assert infer_roast_category(atomic_decaf) == OMNI_ROAST

    # C4 suitability style
    c4_omni = {
        "title": "Terra Nova",
        "body_html": "<p>Roast Level Medium Sutiable For Espresso, Plunger & Filter</p>",
    }
    assert infer_roast_category(c4_omni) == OMNI_ROAST

    # Slow roasted for espresso style: Raspberry Kiss is explicitly labeled as espresso roast only
    slow_espresso = {
        "title": "Raspberry Kiss | Ethiopia",
        "tags": ["espresso", "filter coffee"],
        "body_html": "<p>roasted for espresso, and brought to us by Cofinet. Part of Espresso Program Vol. 1 — single origins roasted for espresso.</p>",
    }
    assert infer_roast_category(slow_espresso, collection_handle="espresso-coffee") == ESPRESSO_ROAST
    assert infer_roast_category(slow_espresso, source="slowcoffee.co.nz") == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Raspberry Kiss | Ethiopia", "tags": ["filter coffee", "espresso"]}) == ESPRESSO_ROAST


@pytest.mark.unit
def test_infer_roast_category_non_coffee_is_other() -> None:
    assert infer_roast_category({"title": "Hario V60 Filter Papers 100pk", "product_type": "Brew Gear"}) == OTHER_CATEGORY
    assert infer_roast_category({"title": "Gift Card", "product_type": "Gift Card"}) == OTHER_CATEGORY
    assert infer_roast_category({"title": "C4 Black Group Filter Brush", "product_type": "Espresso Equipment"}) == OTHER_CATEGORY


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
