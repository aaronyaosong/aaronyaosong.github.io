from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from nz_coffee_tracker.ocr import (
    extract_text_from_image_url,
    extract_text_from_product_images,
)
from nz_coffee_tracker.categorization import infer_metadata


def test_extract_text_from_image_url_empty_and_invalid() -> None:
    assert extract_text_from_image_url("") == ""
    assert extract_text_from_image_url(None) == ""  # type: ignore
    assert extract_text_from_image_url("ftp://example.com/img.png") == ""


def test_extract_text_from_image_url_success() -> None:
    mock_resp = MagicMock()
    mock_resp.content = b"fake-image-bytes"
    mock_resp.raise_for_status.return_value = None

    mock_image = MagicMock()
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "  Peach   \n\n  Jasmine  "

    with patch("requests.get", return_value=mock_resp):
        with patch("nz_coffee_tracker.ocr.HAS_OCR", True):
            with patch("nz_coffee_tracker.ocr.Image", mock_image):
                with patch("nz_coffee_tracker.ocr.pytesseract", mock_pytesseract):
                    result = extract_text_from_image_url("https://c4coffee.co/img.png")
                    assert "Peach" in result
                    assert "Jasmine" in result


def test_extract_text_from_image_url_no_ocr() -> None:
    with patch("nz_coffee_tracker.ocr.HAS_OCR", False):
        assert extract_text_from_image_url("https://c4coffee.co/img.png") == ""


def test_extract_text_from_image_url_exception_handling() -> None:
    with patch("requests.get", side_effect=Exception("Network error")):
        assert extract_text_from_image_url("https://c4coffee.co/img.png") == ""


def test_extract_text_from_product_images_dict_list() -> None:
    product = {
        "title": "Ethiopia Sidama",
        "images": [
            {"src": "https://cdn.shopify.com/files/img1.png"},
            {"src": "https://cdn.shopify.com/files/img2.png"},
        ],
    }

    with patch("nz_coffee_tracker.ocr.extract_text_from_image_url") as mock_extract:
        mock_extract.side_effect = lambda url, timeout: f"Text from {url}"
        text = extract_text_from_product_images(product, max_images=1)
        assert text == "Text from https://cdn.shopify.com/files/img1.png"
        assert mock_extract.call_count == 1


def test_extract_text_from_product_images_single_fallback() -> None:
    product = {
        "title": "Ethiopia Sidama",
        "image": {"src": "https://cdn.shopify.com/files/single.png"},
    }

    with patch("nz_coffee_tracker.ocr.extract_text_from_image_url", return_value="Label Notes"):
        text = extract_text_from_product_images(product)
        assert text == "Label Notes"


def test_infer_metadata_with_ocr_flavour_notes() -> None:
    product = {
        "title": "Ethiopia Sidama",
        "body_html": "<p>Ripe cherries are hand-sorted, pulped, fermented, and washed daily.</p>",
        "images": [{"src": "https://cdn.shopify.com/files/c4_ethiopia.png"}],
    }

    # Simulate OCR extracting tasting notes from bag label
    with patch("nz_coffee_tracker.ocr.extract_text_from_image_url", return_value="Tasting notes: Peach, Jasmine, Bergamot"):
        meta = infer_metadata(product, use_llm=False)
        assert "Peach" in meta["flavour_notes"]
        assert "Jasmine" in meta["flavour_notes"]
        assert meta["origin_country"] == "Ethiopia"
