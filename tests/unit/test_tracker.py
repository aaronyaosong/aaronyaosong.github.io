from __future__ import annotations

import pytest

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker import tracker


def _listing(title: str, category: str, available: bool = True) -> CoffeeListing:
    return CoffeeListing(
        source="example.co.nz",
        product_id=1,
        title=title,
        category=category,
        handle="sample",
        product_url="https://example.co.nz/products/sample",
        available=available,
        price_min_nzd=20.0,
        price_max_nzd=20.0,
        updated_at="2026-08-17T00:00:00+00:00",
        scraped_at="2026-08-17T00:00:00+00:00",
    )


@pytest.mark.unit
def test_collect_listings_default_filters_categories_and_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tracker,
        "scrape_rocket",
        lambda: [
            _listing("Filter A", "filter roast", available=True),
            _listing("Other A", "other", available=True),
        ],
    )
    monkeypatch.setattr(
        tracker,
        "scrape_atomic",
        lambda: [
            _listing("Espresso A", "espresso roast", available=True),
            _listing("Espresso B", "espresso roast", available=False),
        ],
    )

    rows = tracker.collect_listings()

    assert [item.title for item in rows] == ["Filter A", "Espresso A"]


@pytest.mark.unit
def test_collect_listings_include_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracker, "scrape_rocket", lambda: [_listing("Filter A", "filter roast", available=False)])
    monkeypatch.setattr(tracker, "scrape_atomic", lambda: [])

    rows = tracker.collect_listings(include_unavailable=True)

    assert len(rows) == 1
    assert rows[0].available is False


@pytest.mark.unit
def test_collect_listings_without_category_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracker, "scrape_rocket", lambda: [_listing("Other A", "other", available=True)])
    monkeypatch.setattr(tracker, "scrape_atomic", lambda: [])

    rows = tracker.collect_listings(allowed_categories=None)

    assert len(rows) == 1
    assert rows[0].category == "other"
