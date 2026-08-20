from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from nz_coffee_tracker.ocr import (
    extract_text_from_image_url,
    extract_text_from_product_images,
    get_sorted_candidate_image_urls,
    score_image_candidate,
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


def test_score_image_candidate() -> None:
    info_card = {"src": "https://cdn.shopify.com/files/Website_Info_Card_Stout.jpg", "alt": "Tasting Notes Card", "width": 1000, "height": 1000}
    lifestyle = {"src": "https://cdn.shopify.com/files/cafe_lifestyle_banner.jpg", "alt": "Cafe store banner", "width": 2000, "height": 600}
    
    assert score_image_candidate(info_card) > score_image_candidate(lifestyle)


def test_get_sorted_candidate_image_urls() -> None:
    product = {
        "title": "Stout Blend",
        "images": [
            {"src": "https://cdn.shopify.com/files/banner_store.png", "alt": "Store banner"},
            {"src": "https://cdn.shopify.com/files/Website_Info_Card_Stout.jpg", "alt": "Tasting Notes Info Card"},
            {"src": "https://cdn.shopify.com/files/bag_render.png", "alt": "Whole beans coffee bag"},
        ],
    }

    sorted_urls = get_sorted_candidate_image_urls(product)
    assert len(sorted_urls) == 3
    # Info card and bag render should be prioritized ahead of the banner
    assert sorted_urls[0] == "https://cdn.shopify.com/files/Website_Info_Card_Stout.jpg"
    assert sorted_urls[-1] == "https://cdn.shopify.com/files/banner_store.png"


def test_extract_text_from_product_images_early_stopping() -> None:
    product = {
        "title": "Ethiopia Sidama",
        "images": [
            {"src": "https://cdn.shopify.com/files/label.png", "alt": "Label"},
            {"src": "https://cdn.shopify.com/files/card.png", "alt": "Card"},
            {"src": "https://cdn.shopify.com/files/extra.png", "alt": "Extra"},
        ],
    }

    with patch("nz_coffee_tracker.ocr.extract_text_from_image_url") as mock_extract:
        mock_extract.side_effect = [
            "Tasting notes: Peach, Jasmine",
            "Recipe info",
            "Third image text",
        ]

        # Stop condition checks if 'Peach' is in the text
        stop_fn = lambda text: "Peach" in text

        result = extract_text_from_product_images(product, stop_condition=stop_fn)
        assert "Peach" in result
        # Early stopping should have terminated after image 1 without touching images 2 and 3!
        assert mock_extract.call_count == 1


def test_infer_metadata_with_ocr_flavour_notes() -> None:
    product = {
        "title": "Ethiopia Sidama",
        "body_html": "<p>Ripe cherries are hand-sorted, pulped, fermented, and washed daily.</p>",
        "images": [{"src": "https://cdn.shopify.com/files/c4_ethiopia.png", "alt": "Coffee bag label"}],
    }

    # Simulate OCR extracting tasting notes from bag label
    with patch("nz_coffee_tracker.ocr.extract_text_from_image_url", return_value="Tasting notes: Peach, Jasmine, Bergamot"):
        meta = infer_metadata(product, use_llm=False)
        assert "Peach" in meta["flavour_notes"]
        assert "Jasmine" in meta["flavour_notes"]
        assert meta["origin_country"] == "Ethiopia"
