from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from nz_coffee_tracker import cli, tracker
from nz_coffee_tracker.models import CoffeeListing

_TODAY_ISO = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _listing(title: str, category: str, available: bool) -> CoffeeListing:
    return CoffeeListing(
        source="example.co.nz",
        product_id=42,
        title=title,
        category=category,
        handle="sample",
        product_url="https://example.co.nz/products/sample",
        available=available,
        price_min_nzd=19.0,
        price_max_nzd=25.0,
        updated_at=_TODAY_ISO,
        scraped_at=_TODAY_ISO,
        description="Coffee description",
        flavour_notes="chocolate",
    )


@pytest.mark.e2e
def test_cli_writes_filtered_csv_and_json(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    # E2E check: CLI should apply filters and persist both output formats.
    monkeypatch.setattr(
        tracker,
        "scrape_rocket",
        lambda **kwargs: [
            _listing("Filter Coffee", "filter roast", available=True),
            _listing("Merch Item", "other", available=True),
        ],
    )
    monkeypatch.setattr(
        tracker,
        "scrape_atomic",
        lambda **kwargs: [
            _listing("Espresso Coffee", "espresso roast", available=True),
            _listing("Unavailable Espresso", "espresso roast", available=False),
        ],
    )
    monkeypatch.setattr(tracker, "scrape_ozone", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_coffee_embassy", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_eternal", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_vanguard", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_c4", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_slow", lambda **kwargs: [])

    out_dir = tmp_path / "output"
    monkeypatch.setattr("sys.argv", ["prog", "--out-dir", str(out_dir), "--format", "both"])

    exit_code = cli.main()

    assert exit_code == 0
    assert (out_dir / "latest.csv").exists()
    assert (out_dir / "latest.json").exists()
    assert (out_dir / "history.sqlite3").exists()
    assert len(list(out_dir.glob("*.csv"))) >= 2
    assert len(list(out_dir.glob("*.json"))) >= 2

    csv_text = (out_dir / "latest.csv").read_text(encoding="utf-8")
    assert "category" in csv_text.splitlines()[0]
    assert "Filter Coffee" in csv_text
    assert "Espresso Coffee" in csv_text
    assert "Merch Item" not in csv_text
    assert "Unavailable Espresso" not in csv_text

    payload = json.loads((out_dir / "latest.json").read_text(encoding="utf-8"))
    assert payload["count"] == 2

    output = capsys.readouterr().out
    assert "Category filter: espresso roast, filter roast" in output


@pytest.mark.e2e
def test_cli_skips_second_scrape_when_today_data_exists(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    listing = _listing("Filter Coffee", "filter roast", available=True)
    monkeypatch.setattr(tracker, "scrape_rocket", lambda **kwargs: [listing])
    monkeypatch.setattr(tracker, "scrape_atomic", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_ozone", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_coffee_embassy", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_eternal", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_vanguard", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_c4", lambda **kwargs: [])
    monkeypatch.setattr(tracker, "scrape_slow", lambda **kwargs: [])
    out_dir = tmp_path / "output"
    monkeypatch.setattr("sys.argv", ["prog", "--out-dir", str(out_dir), "--format", "both"])

    assert cli.main() == 0
    monkeypatch.setattr(tracker, "scrape_rocket", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_atomic", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_ozone", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_coffee_embassy", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_eternal", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_vanguard", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_c4", lambda **kwargs: pytest.fail("scraper should not run"))
    monkeypatch.setattr(tracker, "scrape_slow", lambda **kwargs: pytest.fail("scraper should not run"))

    assert cli.main() == 0
    assert "Data already scraped today; skipping scrape." in capsys.readouterr().out
