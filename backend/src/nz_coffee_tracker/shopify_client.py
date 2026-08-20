import re
from html import unescape
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

        # If description is empty or missing, fetch page HTML to extract rich text metafields
        desc = str(product.get("body_html") or product.get("description") or "").strip()
        if not desc:
            try:
                page_resp = self.session.get(
                    f"{self.base_url}/products/{product_handle}",
                    headers={"Accept": "text/html,application/xhtml+xml"},
                    timeout=self.timeout,
                )
                if getattr(page_resp, "ok", False) and getattr(page_resp, "text", None):
                    blocks = re.findall(
                        r'<div[^>]*class=\"[^\"]*metafield[^\"]*\"[^>]*>(.*?)</div>',
                        page_resp.text,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if blocks:
                        clean_blocks = [
                            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(b))).strip()
                            for b in blocks
                        ]
                        product["body_html"] = " ".join(clean_blocks)
            except Exception:
                pass

        return product
