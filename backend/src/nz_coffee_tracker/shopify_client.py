from __future__ import annotations

from typing import Any

import requests


DEFAULT_HEADERS = {
    "User-Agent": "nz-coffee-release-tracker/0.1 (+https://github.com)",
    "Accept": "application/json",
}


class ShopifyClient:
    def __init__(self, base_url: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_collection_products(self, collection_handle: str, limit: int = 250) -> list[dict[str, Any]]:
        url = f"{self.base_url}/collections/{collection_handle}/products.json"
        params = {"limit": limit}
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        return payload.get("products", [])
