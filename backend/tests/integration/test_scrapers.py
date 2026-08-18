from __future__ import annotations

import pytest

from nz_coffee_tracker.scrapers import atomic, rocket
from nz_coffee_tracker.scrapers import coffee_embassy, eternal, grey_roasting_co, ozone
from nz_coffee_tracker.database import write_database
from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.shopify_client import ShopifyClient


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"variants": [{"price": 2800, "title": "250g"}]}


@pytest.mark.integration
def test_scrape_rocket_maps_product_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    # Integration-level mapping check from Shopify payload to CoffeeListing.
    product = {
        "id": 111,
        "title": "Rocket Espresso Blend",
        "handle": "rocket-espresso-blend",
        "updated_at": "2026-08-17T00:00:00+12:00",
        "body_html": "<p>Origin: Colombia</p><p>Producer: Elena Farm</p><p>Flavour notes: plum, cocoa</p>",
        "variants": [
            {"available": False, "price": "22.00", "title": "250g"},
            {"available": True, "price": "60.00", "title": "1kg"},
        ],
    }

    monkeypatch.setattr(rocket.ShopifyClient, "fetch_collection_products", lambda self, handle: [product])
    monkeypatch.setattr(rocket.ShopifyClient, "fetch_product", lambda self, handle: product)
    monkeypatch.setattr(rocket, "now_utc_iso", lambda: "2026-08-17T01:02:03+00:00")

    rows = rocket.scrape_rocket()

    assert len(rows) == 1
    row = rows[0]
    assert row.source == "rocketcoffee.co.nz"
    assert row.product_id == 111
    assert row.available is True
    assert row.category == "espresso roast"
    assert row.varietal == "unknown"
    assert row.price_min_nzd == 22.0
    assert row.price_max_nzd == 60.0
    assert row.size_prices == [{"size_grams": 1000.0, "price_nzd": 60.0}]
    assert row.product_url.endswith("/rocket-espresso-blend")
    assert row.origin_country == "Colombia"
    assert row.producer == "Elena Farm"
    assert row.flavour_notes == "plum, cocoa"


@pytest.mark.integration
def test_fetch_product_converts_shopify_cents_to_nzd(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ShopifyClient("https://example.com")
    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: _Response())

    product = client.fetch_product("coffee")

    assert product["variants"][0]["price"] == 28.0


@pytest.mark.integration
def test_scrape_atomic_handles_missing_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    # Missing prices should gracefully fall back to 0.0 values.
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
    monkeypatch.setattr(atomic.ShopifyClient, "fetch_product", lambda self, handle: product)
    monkeypatch.setattr(atomic, "now_utc_iso", lambda: "2026-08-17T01:02:03+00:00")

    rows = atomic.scrape_atomic()

    assert len(rows) == 1
    row = rows[0]
    assert row.source == "atomiccoffee.co.nz"
    assert row.category == "filter roast"
    assert row.varietal == "unknown"
    assert row.available is True
    assert row.price_min_nzd == 0.0
    assert row.price_max_nzd == 0.0
    assert row.size_prices == []


@pytest.mark.integration
def test_scrape_rocket_reuses_detail_for_available_cached_item(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    product = {
        "id": 333,
        "title": "Cached Coffee",
        "handle": "cached-coffee",
        "updated_at": "2026-08-17T00:00:00+00:00",
        "variants": [{"available": True, "price": "22.00", "title": "250g"}],
    }
    cached = CoffeeListing(
        source="rocketcoffee.co.nz",
        product_id=333,
        title="Cached Coffee",
        category="filter roast",
        handle="cached-coffee",
        product_url="https://rocketcoffee.co.nz/products/cached-coffee",
        available=True,
        price_min_nzd=20.0,
        price_max_nzd=20.0,
        updated_at="2026-08-17T00:00:00+00:00",
        scraped_at="2026-08-17T00:00:00+00:00",
        size_prices=[{"size_grams": 250.0, "price_nzd": 20.0}],
        description="Cached description",
        flavour_notes="chocolate",
    )
    database_path = tmp_path / "history.sqlite3"
    write_database([cached], database_path)

    monkeypatch.setattr(rocket.ShopifyClient, "fetch_collection_products", lambda self, handle: [product])
    monkeypatch.setattr(rocket.ShopifyClient, "fetch_product", lambda self, handle: pytest.fail("detail should not be fetched"))

    rows = rocket.scrape_rocket(database_path=database_path)

    assert rows[0].size_prices == [{"size_grams": 250.0, "price_nzd": 20.0}]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("module", "function_name", "expected_source", "expected_collection"),
    [
        (ozone, "scrape_ozone", "ozonecoffee.co.nz", "coffee"),
        (coffee_embassy, "scrape_coffee_embassy", "coffeeembassy.co.nz", "coffee"),
        (eternal, "scrape_eternal", "eternalcoffee.co.nz", "all"),
        (grey_roasting_co, "scrape_grey_roasting_co", "greyroastingco.com", "all"),
    ],
)
def test_additional_scrapers_use_expected_shopify_collection(
    monkeypatch: pytest.MonkeyPatch,
    module,
    function_name: str,
    expected_source: str,
    expected_collection: str,
) -> None:
    calls = []
    monkeypatch.setattr(
        module,
        "scrape_shopify_collection",
        lambda source, collection, database_path=None: calls.append((source, collection, database_path)) or [],
    )

    rows = getattr(module, function_name)()

    assert rows == []
    assert calls == [(expected_source, expected_collection, None)]


@pytest.mark.integration
def test_scrape_grey_roasting_co_excludes_subscriptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def listing(title: str, handle: str) -> CoffeeListing:
        return CoffeeListing(
            source="greyroastingco.com",
            product_id=1,
            title=title,
            category="espresso roast",
            handle=handle,
            product_url=f"https://greyroastingco.com/products/{handle}",
            available=True,
            price_min_nzd=20.0,
            price_max_nzd=20.0,
            updated_at="2026-08-17T00:00:00+00:00",
            scraped_at="2026-08-17T00:00:00+00:00",
        )

    monkeypatch.setattr(
        grey_roasting_co,
        "scrape_shopify_collection",
        lambda source, collection, database_path=None: [
            listing("Daily Blend", "daily-blend"),
            listing("Daily Blend Subscription", "daily-blend-subscription"),
        ],
    )

    rows = grey_roasting_co.scrape_grey_roasting_co()

    assert [row.title for row in rows] == ["Daily Blend"]
