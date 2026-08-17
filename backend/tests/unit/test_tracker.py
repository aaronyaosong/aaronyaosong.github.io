from __future__ import annotations

import sqlite3

import pytest

from nz_coffee_tracker import tracker
from nz_coffee_tracker.database import has_current_data, write_database
from nz_coffee_tracker.models import CoffeeListing


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
        description="Coffee description",
        flavour_notes="chocolate",
    )


@pytest.mark.unit
def test_collect_listings_default_filters_categories_and_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Default behavior should keep only available filter/espresso roasts.
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
    # --all behavior keeps otherwise filtered unavailable rows.
    monkeypatch.setattr(tracker, "scrape_rocket", lambda: [_listing("Filter A", "filter roast", available=False)])
    monkeypatch.setattr(tracker, "scrape_atomic", lambda: [])

    rows = tracker.collect_listings(include_unavailable=True)

    assert len(rows) == 1
    assert rows[0].available is False


@pytest.mark.unit
def test_collect_listings_without_category_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    # Disabling category filtering should allow non-roast categories through.
    monkeypatch.setattr(tracker, "scrape_rocket", lambda: [_listing("Other A", "other", available=True)])
    monkeypatch.setattr(tracker, "scrape_atomic", lambda: [])

    rows = tracker.collect_listings(allowed_categories=None)

    assert len(rows) == 1
    assert rows[0].category == "other"


@pytest.mark.unit
def test_write_database_stores_run_listings_and_size_prices(tmp_path) -> None:
    listing = _listing("Historical Coffee", "filter roast")
    listing.size_prices = [{"size_grams": 250.0, "price_nzd": 22.0}]

    database_path = tmp_path / "history.sqlite3"
    write_database([listing], database_path, category_filter={"filter roast"})
    write_database([listing], database_path, category_filter={"filter roast"})

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 2
        assert connection.execute("SELECT title FROM listings LIMIT 1").fetchone()[0] == "Historical Coffee"
        assert connection.execute("SELECT size_grams, price_nzd FROM size_prices LIMIT 1").fetchone() == (250.0, 22.0)


@pytest.mark.unit
def test_has_current_data_requires_today_and_non_empty_output(tmp_path) -> None:
    listing = _listing("Historical Coffee", "filter roast")
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    (out_dir / "latest.json").write_text('{"items": [{"title": "Historical Coffee"}]}', encoding="utf-8")
    (out_dir / "latest.csv").write_text("title\nHistorical Coffee\n", encoding="utf-8")
    database_path = out_dir / "history.sqlite3"
    write_database([listing], database_path, category_filter={"filter roast"})

    assert has_current_data(
        database_path,
        out_dir,
        "both",
        category_filter={"filter roast"},
        today=listing.scraped_at[:10],
    ) is True
    assert has_current_data(
        database_path,
        out_dir,
        "both",
        category_filter={"espresso roast"},
        today=listing.scraped_at[:10],
    ) is False
