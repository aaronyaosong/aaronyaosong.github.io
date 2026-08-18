from __future__ import annotations

import re
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


SCRAPER_TEMPLATE = '''from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests

from nz_coffee_tracker.categorization import (
    description_text,
    infer_decaf,
    infer_flavour_notes,
    infer_origin_country,
    infer_process,
    infer_producer,
    infer_roast_category,
    infer_varietal,
)
from nz_coffee_tracker.database import latest_listing
from nz_coffee_tracker.models import CoffeeListing, now_utc_iso
from nz_coffee_tracker.shopify_client import ShopifyClient


SOURCE = "{website}"
COLLECTION_HANDLE = "{collection}"


def _variant_size_grams(title: str) -> float | None:
    if not title:
        return None
    match = re.search(r"(\\d+(?:\\.\\d+)?)\\s*(kgs?|kilos?|kilograms?|grams?|gms?|gm|gr|g)\\b", title.lower())
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    return value * 1000 if unit.startswith("k") else value


def _size_prices(variants: list[dict[str, Any]], product_title: str = "") -> list[dict[str, float]]:
    rows = []
    for variant in variants:
        if not variant.get("available"):
            continue
        v_title = str(variant.get("title", ""))
        size_grams = _variant_size_grams(v_title)
        if not size_grams:
            opts = " ".join(str(variant.get(f"option{{i}}", "")) for i in (1, 2, 3) if variant.get(f"option{{i}}"))
            size_grams = _variant_size_grams(opts)
        if not size_grams and product_title:
            size_grams = _variant_size_grams(product_title)
        try:
            price_nzd = float(variant["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if size_grams:
            rows.append({{"size_grams": size_grams, "price_nzd": price_nzd}})
    return rows


def scrape_{name}(database_path: Path | None = None) -> list[CoffeeListing]:
    client = ShopifyClient("https://{website}")
    products = client.fetch_collection_products(COLLECTION_HANDLE)
    scraped_at = now_utc_iso()
    listings = []

    for product in products:
        # Review this mapping for site-specific fields and availability rules.
        handle = str(product.get("handle", "")).strip()
        product_id = int(product.get("id", 0))
        cached = latest_listing(database_path, SOURCE, product_id) if database_path else None
        variants = product.get("variants", [])
        if cached is None or not cached["size_prices"] or not cached.get("description"):
            try:
                product = {{**product, **client.fetch_product(handle)}}
            except requests.RequestException:
                pass
            variants = product.get("variants", [])

        prices = [float(v["price"]) for v in variants if v.get("price") is not None]
        prices = prices or [0.0]
        listings.append(CoffeeListing(
            source=SOURCE,
            product_id=product_id,
            title=str(product.get("title", "")).strip(),
            category=infer_roast_category(product),
            handle=handle,
            product_url=f"https://{{website}}/products/{{handle}}",
            available=any(bool(v.get("available")) for v in variants),
            price_min_nzd=min(prices),
            price_max_nzd=max(prices),
            updated_at=str(product.get("updated_at", "")),
            scraped_at=scraped_at,
            varietal=infer_varietal(product),
            size_prices=_size_prices(variants),
            origin_country=infer_origin_country(product),
            producer=infer_producer(product),
            process=infer_process(product),
            decaf=infer_decaf(product),
            description=description_text(product),
            flavour_notes=infer_flavour_notes(product),
        ))

    return listings
'''


TEST_TEMPLATE = '''from __future__ import annotations

import pytest

from nz_coffee_tracker.scrapers import {name}


@pytest.mark.integration
def test_scrape_{name}_maps_product_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    product = {{
        "id": 123,
        "title": "Example Coffee",
        "handle": "example-coffee",
        "updated_at": "2026-08-17T00:00:00+00:00",
        "variants": [{{"available": True, "price": "22.00", "title": "250g"}}],
    }}

    monkeypatch.setattr({name}.ShopifyClient, "fetch_collection_products", lambda self, handle: [product])
    monkeypatch.setattr({name}.ShopifyClient, "fetch_product", lambda self, handle: product)

    rows = {name}.scrape_{name}()

    assert len(rows) == 1
    assert rows[0].source == "{website}"
    assert rows[0].title == "Example Coffee"
'''


def scaffold_scraper(name: str, website: str, collection: str, root: Path) -> tuple[Path, Path]:
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError("name must use lowercase letters, numbers, and underscores and start with a letter")
    website = website.removeprefix("https://").removeprefix("http://").rstrip("/")
    if not website or "/" in website:
        raise ValueError("website must be a hostname such as roaster.example")
    if not collection:
        raise ValueError("collection must not be empty")

    scraper_path = root / "backend/src/nz_coffee_tracker/scrapers" / f"{name}.py"
    test_path = root / "backend/tests/integration" / f"test_{name}.py"
    if scraper_path.exists() or test_path.exists():
        raise FileExistsError(f"refusing to overwrite {scraper_path} or {test_path}")

    scraper_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    scraper_path.write_text(
        SCRAPER_TEMPLATE.format(name=name, website=website, collection=collection),
        encoding="utf-8",
    )
    test_path.write_text(
        TEST_TEMPLATE.format(name=name, website=website),
        encoding="utf-8",
    )
    return scraper_path, test_path
