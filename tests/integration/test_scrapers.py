from __future__ import annotations

import pytest

from nz_coffee_tracker.scrapers import atomic, rocket


@pytest.mark.integration
def test_scrape_rocket_maps_product_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    product = {
        "id": 111,
        "title": "Rocket Espresso Blend",
        "handle": "rocket-espresso-blend",
        "updated_at": "2026-08-17T00:00:00+12:00",
        "variants": [
            {"available": False, "price": "22.00", "title": "250g"},
            {"available": True, "price": "60.00", "title": "1kg"},
        ],
    }

    monkeypatch.setattr(rocket.ShopifyClient, "fetch_collection_products", lambda self, handle: [product])
    monkeypatch.setattr(rocket, "now_utc_iso", lambda: "2026-08-17T01:02:03+00:00")

    rows = rocket.scrape_rocket()

    assert len(rows) == 1
    row = rows[0]
    assert row.source == "rocketcoffee.co.nz"
    assert row.product_id == 111
    assert row.available is True
    assert row.category == "espresso roast"
    assert row.price_min_nzd == 22.0
    assert row.price_max_nzd == 60.0
    assert row.product_url.endswith("/rocket-espresso-blend")


@pytest.mark.integration
def test_scrape_atomic_handles_missing_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    product = {
        "id": 222,
        "title": "Atomic Filter Special",
        "handle": "atomic-filter-special",
        "updated_at": "2026-08-17T00:00:00+12:00",
        "variants": [
            {"available": True, "price": None, "title": "250g"},
            {"available": False, "title": "1kg"},
        ],
    }

    monkeypatch.setattr(atomic.ShopifyClient, "fetch_collection_products", lambda self, handle: [product])
    monkeypatch.setattr(atomic, "now_utc_iso", lambda: "2026-08-17T01:02:03+00:00")

    rows = atomic.scrape_atomic()

    assert len(rows) == 1
    row = rows[0]
    assert row.source == "atomiccoffee.co.nz"
    assert row.category == "filter roast"
    assert row.available is True
    assert row.price_min_nzd == 0.0
    assert row.price_max_nzd == 0.0
