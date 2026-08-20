from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from collections.abc import Callable
from typing import Any

import requests

from nz_coffee_tracker.categorization import (
    ESPRESSO_ROAST,
    FILTER_ROAST,
    OMNI_ROAST,
    category_values,
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


GROUND_PATTERN = re.compile(
    r"\b(espresso|plunger|filter|aeropress|stovetop|chemex|french\s*press|v60|pour\s*over|drip|coarse|medium|fine|grind|ground)\b",
    re.IGNORECASE,
)
BEAN_PATTERN = re.compile(r"\b(whole\s*beans?|wholebean|beans)\b", re.IGNORECASE)


def _filter_whole_bean_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    has_grind_spec = False
    for v in variants:
        v_text = " ".join(
            [str(v.get("title", ""))] + [str(v.get(f"option{i}", "")) for i in (1, 2, 3) if v.get(f"option{i}")]
        )
        if GROUND_PATTERN.search(v_text) or BEAN_PATTERN.search(v_text):
            has_grind_spec = True
            break

    if not has_grind_spec:
        return variants

    wb_variants = []
    for v in variants:
        v_text = " ".join(
            [str(v.get("title", ""))] + [str(v.get(f"option{i}", "")) for i in (1, 2, 3) if v.get(f"option{i}")]
        )
        if BEAN_PATTERN.search(v_text) and not GROUND_PATTERN.search(v_text):
            wb_variants.append(v)

    return wb_variants if wb_variants else variants


def _variant_prices(variants: list[dict[str, Any]]) -> list[float]:
    prices = []
    for variant in variants:
        try:
            prices.append(float(variant["price"]))
        except (KeyError, TypeError, ValueError):
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
    rows = []
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

        variants = _filter_whole_bean_variants(product.get("variants", []))
        prices = _variant_prices(variants) or [0.0]
        size_prices = cached["size_prices"] if cached and not needs_detail else _size_prices(variants, str(product.get("title", "")))
        listings.append(
            CoffeeListing(
                source=source,
                product_id=product_id,
                title=str(product.get("title", "")).strip(),
                category=infer_roast_category(product, collection_handle=collection_handle, source=source),
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
                flavour_notes=infer_flavour_notes(product, database_path=database_path),
            )
        )

    return listings


def scrape_shopify_collections(
    source: str,
    collection_handles: list[str],
    database_path: Path | None = None,
    product_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> list[CoffeeListing]:
    by_product_id: dict[int, CoffeeListing] = {}
    for handle in collection_handles:
        for listing in scrape_shopify_collection(
            source=source,
            collection_handle=handle,
            database_path=database_path,
            product_filter=product_filter,
        ):
            if listing.product_id not in by_product_id:
                by_product_id[listing.product_id] = listing
            else:
                existing = by_product_id[listing.product_id]
                cats = set(category_values(existing.category)) | set(category_values(listing.category))
                if cats - {"other"}:
                    cats = cats - {"other"}
                if OMNI_ROAST in cats or (FILTER_ROAST in cats and ESPRESSO_ROAST in cats):
                    combined_cat = OMNI_ROAST
                else:
                    combined_cat = ",".join(sorted(cats))
                by_product_id[listing.product_id] = CoffeeListing(
                    source=existing.source,
                    product_id=existing.product_id,
                    title=existing.title,
                    category=combined_cat,
                    handle=existing.handle,
                    product_url=existing.product_url,
                    available=existing.available or listing.available,
                    price_min_nzd=min(existing.price_min_nzd, listing.price_min_nzd),
                    price_max_nzd=max(existing.price_max_nzd, listing.price_max_nzd),
                    updated_at=existing.updated_at,
                    scraped_at=existing.scraped_at,
                    varietal=existing.varietal if existing.varietal != "unknown" else listing.varietal,
                    size_prices=existing.size_prices or listing.size_prices,
                    origin_country=existing.origin_country if existing.origin_country != "unknown" else listing.origin_country,
                    producer=existing.producer if existing.producer != "unknown" else listing.producer,
                    process=existing.process if existing.process != "unknown" else listing.process,
                    decaf=existing.decaf or listing.decaf,
                    description=existing.description or listing.description,
                    flavour_notes=existing.flavour_notes if existing.flavour_notes != "unknown" else listing.flavour_notes,
                )
    return list(by_product_id.values())
