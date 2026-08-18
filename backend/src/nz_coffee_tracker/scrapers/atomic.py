from __future__ import annotations

import re
from typing import Any

import requests
from pathlib import Path

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


def _variant_prices(variants: list[dict[str, Any]]) -> list[float]:
    # Variants may include non-numeric or missing prices; keep only valid floats.
    prices: list[float] = []
    for variant in variants:
        raw = variant.get("price")
        if raw is None:
            continue
        try:
            prices.append(float(raw))
        except (TypeError, ValueError):
            continue
    return prices


def _variant_size_grams(title: str) -> float | None:
    if not title:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(kgs?|kilos?|kilograms?|grams?|gms?|gm|gr|g)\b", title.lower())
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    return value * 1000 if unit.startswith("k") else value


def _size_prices(variants: list[dict[str, Any]], product_title: str = "") -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for variant in variants:
        if not variant.get("available"):
            continue
        v_title = str(variant.get("title", ""))
        size_grams = _variant_size_grams(v_title)
        if not size_grams:
            opts = " ".join(str(variant.get(f"option{i}", "")) for i in (1, 2, 3) if variant.get(f"option{i}"))
            size_grams = _variant_size_grams(opts)
        if not size_grams and product_title:
            size_grams = _variant_size_grams(product_title)
        try:
            price_nzd = float(variant["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if size_grams:
            rows.append({"size_grams": size_grams, "price_nzd": price_nzd})
    return rows


def scrape_atomic(database_path: Path | None = None) -> list[CoffeeListing]:
    # Atomic exposes beans under the Shopify collection handle "coffee-beans".
    client = ShopifyClient("https://atomiccoffee.co.nz")
    products = client.fetch_collection_products("coffee-beans")

    scraped_at = now_utc_iso()
    listings: list[CoffeeListing] = []
    for product in products:
        handle = str(product.get("handle", "")).strip()
        product_id = int(product.get("id", 0))
        collection_available = any(bool(v.get("available")) for v in product.get("variants", []))
        cached = latest_listing(database_path, "atomiccoffee.co.nz", product_id) if database_path else None
        needs_detail = (
            cached is None
            or not cached["size_prices"]
            or not cached.get("description")
            or cached.get("flavour_notes") in (None, "", "unknown")
            or not collection_available
            or not cached["available"]
        )
        if needs_detail:
            try:
                product = {**product, **client.fetch_product(handle)}
            except requests.RequestException:
                pass
        # Collapse variant-level availability and price into one listing row.
        variants = product.get("variants", [])
        prices = _variant_prices(variants)
        available = any(bool(v.get("available")) for v in variants)
        category = infer_roast_category(product)

        if not prices:
            prices = [0.0]

        size_prices = cached["size_prices"] if cached and not needs_detail else _size_prices(variants, str(product.get("title", "")))
        listings.append(
            CoffeeListing(
                source="atomiccoffee.co.nz",
                product_id=int(product.get("id", 0)),
                title=str(product.get("title", "")).strip(),
                category=category,
                handle=handle,
                product_url=f"https://atomiccoffee.co.nz/products/{product.get('handle', '')}",
                available=available,
                price_min_nzd=min(prices),
                price_max_nzd=max(prices),
                updated_at=str(product.get("updated_at", "")),
                scraped_at=scraped_at,
                varietal=infer_varietal(product),
                size_prices=size_prices,
                origin_country=infer_origin_country(product),
                producer=infer_producer(product),
                process=infer_process(product),
                decaf=infer_decaf(product),
                description=description_text(product),
                flavour_notes=infer_flavour_notes(product),
            )
        )

    return listings
