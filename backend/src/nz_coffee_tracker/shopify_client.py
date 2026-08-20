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

        # Extract additional page-level metadata (metafield blocks and flavour badge pills)
        try:
            desc = str(product.get("body_html") or product.get("description") or "").strip()
            needs_html = not desc or any(r in self.base_url for r in ("slowcoffee", "wolfcoffee", "atomiccoffee", "ozonecoffee"))
            if needs_html:
                page_resp = self.session.get(
                    f"{self.base_url}/products/{product_handle}",
                    headers={"Accept": "text/html,application/xhtml+xml"},
                    timeout=self.timeout,
                )
                if getattr(page_resp, "ok", False) and getattr(page_resp, "text", None):
                    extra_sections = []
                    # 1. Metafields (e.g. Wolf Coffee)
                    blocks = re.findall(
                        r'<div[^>]*class=\"[^\"]*metafield[^\"]*\"[^>]*>(.*?)</div>',
                        page_resp.text,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if blocks:
                        extra_sections.extend(blocks)

                    # 2. Accordions / Collapsible content (e.g. Atomic Coffee)
                    accordion_blocks = re.findall(
                        r'<div[^>]*class=\"[^\"]*(?:collapsible-content|accordion__content)[^\"]*\"[^>]*>(.*?)</div>',
                        page_resp.text,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if accordion_blocks:
                        extra_sections.extend(accordion_blocks)

                    # 3. Subheadings & Location data (e.g. Ozone Coffee)
                    ozone_locs = re.findall(
                        r'<div[^>]*class=[\"\'][^\"\']*locationData[^\"\']*[\"\'][^>]*>(.*?)</div>',
                        page_resp.text,
                        re.DOTALL | re.IGNORECASE,
                    )
                    for loc in ozone_locs:
                        clean_loc = re.sub(r"<[^>]+>", "", unescape(loc)).strip()
                        if clean_loc:
                            extra_sections.append(f"<p><strong>Origin:</strong> {clean_loc}</p>")

                    ozone_subheadings = re.findall(
                        r'<h3[^>]*class=[\"\'][^\"\']*(?:tw-text-base|subheading)[^\"\']*[\"\'][^>]*>(.*?)</h3>',
                        page_resp.text,
                        re.DOTALL | re.IGNORECASE,
                    )
                    for sub in ozone_subheadings:
                        clean_sub = re.sub(r"<[^>]+>", "", unescape(sub)).strip()
                        if clean_sub and len(clean_sub) > 3:
                            # Strip leading product title or repeated words
                            clean_sub = re.sub(
                                r"^(?:popay[aá]n\s*decaf|cascadia\s*(?:organic)?\s*decaf|atenas\s*cooperative)\s*",
                                "",
                                clean_sub,
                                flags=re.I,
                            ).strip()
                            extra_sections.append(f"<p><strong>Tasting notes:</strong> {clean_sub}</p>")

                    # 4. Pill/Badge flavor notes (e.g. Slow Coffee)
                    pill_matches = re.findall(
                        r'<li[^>]*class=[\"\'][^\"\']*(?:slh-pill|slc__pill)[^\"\']*[\"\'][^>]*>(.*?)</li>',
                        page_resp.text,
                        re.IGNORECASE,
                    )
                    clean_pills = []
                    for p in pill_matches:
                        t = re.sub(r"<[^>]+>", "", unescape(p)).strip()
                        if t and t.lower() not in ("latest release", "sold out", "featured", "new release", "filter", "espresso"):
                            if t not in clean_pills:
                                clean_pills.append(t)
                    if clean_pills:
                        extra_sections.append(f"<p><strong>Tasting notes:</strong> {', '.join(clean_pills)}</p>")

                    if extra_sections:
                        existing_body = str(product.get("body_html") or product.get("description") or "").strip()
                        product["body_html"] = f"{'\n\n'.join(extra_sections)}\n\n{existing_body}".strip()
        except Exception:
            pass

        return product
