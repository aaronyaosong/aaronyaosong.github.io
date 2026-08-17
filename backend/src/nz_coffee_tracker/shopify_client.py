from __future__ import annotations

from typing import Any

import requests


DEFAULT_HEADERS = {
    "User-Agent": "nz-coffee-release-tracker/0.1 (+https://github.com)",
    "Accept": "application/json",
}


class ShopifyClient:
    def __init__(self, base_url: str, timeout: int = 20) -> None:
        # Keep a session per client to reuse connections across requests.
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_collection_products(self, collection_handle: str, limit: int = 250) -> list[dict[str, Any]]:
        # Shopify exposes collection products at /collections/<handle>/products.json.
        url = f"{self.base_url}/collections/{collection_handle}/products.json"
        params = {"limit": limit}
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        return payload.get("products", [])

    def fetch_product(self, product_handle: str) -> dict[str, Any]:
        # Product JSON exposes the complete variant options and availability.
        url = f"{self.base_url}/products/{product_handle}.js"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        product = payload.get("product", payload)
        for variant in product.get("variants", []):
            raw_price = variant.get("price")
            try:
                variant["price"] = float(raw_price) / 100
            except (TypeError, ValueError):
                continue
        return product
