from __future__ import annotations

import re
from collections.abc import Callable
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


def _variant_prices(variants: list[dict[str, Any]]) -> list[float]:
    prices = []
    for variant in variants:
        try:
            prices.append(float(variant["price"]))
        except (KeyError, TypeError, ValueError):
            continue
    return prices


def _variant_size_grams(title: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|grams?)\b", title.lower())
    if not match:
        return None
    value = float(match.group(1))
    return value * 1000 if match.group(2) == "kg" else value


def _size_prices(variants: list[dict[str, Any]]) -> list[dict[str, float]]:
    rows = []
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


def scrape_shopify_collection(
    source: str,
    collection_handle: str,
    database_path: Path | None = None,
    product_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> list[CoffeeListing]:
    client = ShopifyClient(f"https://{source}")
    products = client.fetch_collection_products(collection_handle)
    if product_filter is not None:
        products = [product for product in products if product_filter(product)]
    scraped_at = now_utc_iso()
    listings = []

    for product in products:
        handle = str(product.get("handle", "")).strip()
        product_id = int(product.get("id", 0))
        collection_available = any(bool(v.get("available")) for v in product.get("variants", []))
        cached = latest_listing(database_path, source, product_id) if database_path else None
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

        variants = product.get("variants", [])
        prices = _variant_prices(variants) or [0.0]
        size_prices = cached["size_prices"] if cached and not needs_detail else _size_prices(variants)
        listings.append(
            CoffeeListing(
                source=source,
                product_id=product_id,
                title=str(product.get("title", "")).strip(),
                category=infer_roast_category(product),
                handle=handle,
                product_url=f"https://{source}/products/{handle}",
                available=any(bool(v.get("available")) for v in variants),
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
