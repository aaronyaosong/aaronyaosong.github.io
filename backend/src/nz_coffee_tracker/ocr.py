from __future__ import annotations

import io
import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)


try:
    from PIL import Image
    import pytesseract

    HAS_OCR = True
except ImportError:
    Image = None  # type: ignore
    pytesseract = None  # type: ignore
    HAS_OCR = False


def extract_text_from_image_url(image_url: str, timeout: float = 10.0) -> str:
    """
    Downloads an image from a URL and extracts text using Tesseract OCR.
    Safely returns an empty string if OCR or network request fails.
    """
    if not image_url or not isinstance(image_url, str):
        return ""

    if not image_url.startswith("http://") and not image_url.startswith("https://"):
        if image_url.startswith("//"):
            image_url = f"https:{image_url}"
        else:
            return ""

    if not HAS_OCR or Image is None or pytesseract is None:
        return ""

    try:
        resp = requests.get(image_url, timeout=timeout, headers={"User-Agent": "nz-coffee-release-tracker/0.1"})
        resp.raise_for_status()

        img = Image.open(io.BytesIO(resp.content))
        raw_text = pytesseract.image_to_string(img)

        # Clean extra whitespace
        cleaned = re.sub(r"[ \t]+", " ", raw_text)
        cleaned = re.sub(r"\n\s*\n+", "\n", cleaned).strip()
        return cleaned
    except Exception as exc:
        logger.debug("Failed to perform OCR on %s: %s", image_url, exc)
        return ""


def extract_text_from_product_images(
    product: dict[str, Any],
    max_images: int = 3,
    timeout: float = 10.0,
) -> str:
    """
    Extracts OCR text from the first N product images in a Shopify product payload.
    """
    if not isinstance(product, dict):
        return ""

    image_urls: list[str] = []

    # 1. Check 'images' list (dicts with 'src' or strings)
    raw_images = product.get("images", [])
    if isinstance(raw_images, list):
        for img in raw_images:
            if isinstance(img, dict) and img.get("src"):
                image_urls.append(str(img["src"]))
            elif isinstance(img, str) and img.strip():
                image_urls.append(img.strip())

    # 2. Check 'image' dict/str fallback
    if not image_urls:
        single_img = product.get("image")
        if isinstance(single_img, dict) and single_img.get("src"):
            image_urls.append(str(single_img["src"]))
        elif isinstance(single_img, str) and single_img.strip():
            image_urls.append(single_img.strip())

    extracted_texts: list[str] = []
    for url in image_urls[:max_images]:
        text = extract_text_from_image_url(url, timeout=timeout)
        if text:
            extracted_texts.append(text)

    return "\n".join(extracted_texts).strip()
