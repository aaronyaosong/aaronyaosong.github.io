from __future__ import annotations

from collections.abc import Callable
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


RELEVANT_IMAGE_KEYWORDS = (
    "info",
    "card",
    "label",
    "bag",
    "notes",
    "tasting",
    "tasting_notes",
    "detail",
    "beans",
    "origin",
    "coffee",
)

IGNORED_IMAGE_KEYWORDS = (
    "banner",
    "lifestyle",
    "merch",
    "mug",
    "cup",
    "cafe",
    "store",
    "apparel",
    "tshirt",
    "filter_paper",
    "dripper",
)


def score_image_candidate(img: dict[str, Any] | str) -> int:
    """
    Assigns a priority score to an image metadata candidate to determine scan order.
    Higher score indicates greater likelihood of containing packaging/flavour note text.
    """
    if isinstance(img, str):
        src = img.lower()
        alt = ""
        width = 0
        height = 0
    elif isinstance(img, dict):
        src = str(img.get("src", "")).lower()
        alt = str(img.get("alt", "")).lower()
        width = int(img.get("width", 0) or 0)
        height = int(img.get("height", 0) or 0)
    else:
        return 0

    combined = f"{alt} {src}"
    score = 0

    for kw in RELEVANT_IMAGE_KEYWORDS:
        if kw in combined:
            score += 10

    for kw in IGNORED_IMAGE_KEYWORDS:
        if kw in combined:
            score -= 20

    # Square and portrait images are much more likely to be product bag renders or info cards
    if width and height:
        ratio = width / height
        if 0.7 <= ratio <= 1.3:
            score += 5
        elif ratio > 2.0:
            score -= 10  # wide banners

    return score


def get_sorted_candidate_image_urls(product: dict[str, Any]) -> list[str]:
    """
    Extracts and sorts image URLs for a product dynamically by relevance.
    """
    if not isinstance(product, dict):
        return []

    raw_candidates: list[dict[str, Any] | str] = []

    # 1. Collect all images
    raw_images = product.get("images", [])
    if isinstance(raw_images, list):
        for img in raw_images:
            if isinstance(img, (dict, str)):
                raw_candidates.append(img)

    if not raw_candidates:
        single_img = product.get("image")
        if isinstance(single_img, (dict, str)):
            raw_candidates.append(single_img)

    # 2. Score and sort candidates
    scored = []
    for idx, cand in enumerate(raw_candidates):
        url = str(cand.get("src", "")) if isinstance(cand, dict) else str(cand)
        url = url.strip()
        if not url:
            continue
        score = score_image_candidate(cand)
        # Preserve original listing position as a secondary tie-breaker
        scored.append((score, -idx, url))

    scored.sort(reverse=True)
    return [url for _, _, url in scored]


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
    stop_condition: Callable[[str], bool] | None = None,
    max_images: int = 4,
    timeout: float = 10.0,
) -> str:
    """
    Dynamically extracts OCR text from product images in prioritized order.
    If stop_condition(current_text) evaluates to True, stops scanning remaining images immediately.
    """
    if not isinstance(product, dict):
        return ""

    image_urls = get_sorted_candidate_image_urls(product)
    if not image_urls:
        return ""

    extracted_texts: list[str] = []

    for url in image_urls[:max_images]:
        text = extract_text_from_image_url(url, timeout=timeout)
        if text:
            extracted_texts.append(text)
            current_combined = "\n".join(extracted_texts).strip()
            if stop_condition is not None and stop_condition(current_combined):
                break

    return "\n".join(extracted_texts).strip()
