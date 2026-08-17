from __future__ import annotations

import pytest

from nz_coffee_tracker.scaffold import scaffold_scraper


@pytest.mark.unit
def test_scaffold_scraper_creates_module_and_test(tmp_path) -> None:
    scraper_path, test_path = scaffold_scraper(
        "new_roaster",
        "newroaster.example",
        "coffee",
        tmp_path,
    )

    assert scraper_path.exists()
    assert test_path.exists()
    scraper_text = scraper_path.read_text(encoding="utf-8")
    assert 'SOURCE = "newroaster.example"' in scraper_text
    assert 'COLLECTION_HANDLE = "coffee"' in scraper_text
    assert "def scrape_new_roaster" in scraper_text
    assert "fetch_product(handle)" in scraper_text
    assert "def test_scrape_new_roaster" in test_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_scaffold_scraper_refuses_overwrite(tmp_path) -> None:
    scaffold_scraper("new_roaster", "newroaster.example", "coffee", tmp_path)

    with pytest.raises(FileExistsError):
        scaffold_scraper("new_roaster", "newroaster.example", "coffee", tmp_path)
