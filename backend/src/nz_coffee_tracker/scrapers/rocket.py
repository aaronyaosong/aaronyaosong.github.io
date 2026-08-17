from __future__ import annotations

from typing import Any

from nz_coffee_tracker.categorization import infer_roast_category
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


def scrape_rocket() -> list[CoffeeListing]:
    # Rocket exposes coffee products via Shopify collection handle "coffee".
    client = ShopifyClient("https://rocketcoffee.co.nz")
    products = client.fetch_collection_products("coffee")

    scraped_at = now_utc_iso()
    listings: list[CoffeeListing] = []
    for product in products:
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
                handle=str(product.get("handle", "")).strip(),
                product_url=f"https://rocketcoffee.co.nz/products/{product.get('handle', '')}",
                available=available,
                price_min_nzd=min(prices),
                price_max_nzd=max(prices),
                updated_at=str(product.get("updated_at", "")),
                scraped_at=scraped_at,
            )
        )

    return listings
