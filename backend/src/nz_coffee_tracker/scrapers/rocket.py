from __future__ import annotations

import re
from typing import Any

import requests

from nz_coffee_tracker.categorization import infer_roast_category, infer_varietal
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
    match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|grams?)\b", title.lower())
    if not match:
        return None
    value = float(match.group(1))
    return value * 1000 if match.group(2) == "kg" else value


def _size_prices(variants: list[dict[str, Any]]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for variant in variants:
        if not variant.get("available"):
            continue
        size_grams = _variant_size_grams(str(variant.get("title", "")))
        try:
            price_nzd = float(variant["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if size_grams:
            rows.append({"size_grams": size_grams, "price_nzd": price_nzd})
    return rows


def scrape_rocket() -> list[CoffeeListing]:
    # Rocket exposes coffee products via Shopify collection handle "coffee".
    client = ShopifyClient("https://rocketcoffee.co.nz")
    products = client.fetch_collection_products("coffee")

    scraped_at = now_utc_iso()
    listings: list[CoffeeListing] = []
    for product in products:
        handle = str(product.get("handle", "")).strip()
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

        listings.append(
            CoffeeListing(
                source="rocketcoffee.co.nz",
                product_id=int(product.get("id", 0)),
                title=str(product.get("title", "")).strip(),
                category=category,
                handle=handle,
                product_url=f"https://rocketcoffee.co.nz/products/{product.get('handle', '')}",
                available=available,
                price_min_nzd=min(prices),
                price_max_nzd=max(prices),
                updated_at=str(product.get("updated_at", "")),
                scraped_at=scraped_at,
                varietal=infer_varietal(product),
                size_prices=_size_prices(variants),
            )
        )

    return listings
