from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest
import requests

from nz_coffee_tracker.categorization import infer_flavour_notes
from nz_coffee_tracker.database import get_cached_flavour_notes, set_cached_flavour_notes
from nz_coffee_tracker.llm import (
    _parse_llm_json,
    compute_content_hash,
    extract_flavour_notes_llm,
)


@pytest.mark.unit
def test_compute_content_hash_consistency() -> None:
    h1 = compute_content_hash("Veloce Blend", "Dark chocolate and stone fruit.")
    h2 = compute_content_hash("veloce blend ", "  dark chocolate and stone fruit. ")
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.unit
def test_parse_llm_json_variants() -> None:
    # Clean JSON array
    assert _parse_llm_json('["raspberry", "rhubarb", "irish whiskey"]') == [
        "raspberry",
        "rhubarb",
        "irish whiskey",
    ]
    # Markdown-wrapped JSON
    assert _parse_llm_json('```json\n["peach", "jasmine"]\n```') == ["peach", "jasmine"]
    # JSON object
    assert _parse_llm_json('{"notes": ["vanilla", "honey"]}') == ["vanilla", "honey"]
    # Invalid JSON string
    assert _parse_llm_json("Not json at all") == []


@pytest.mark.unit
def test_extract_flavour_notes_ollama_mocked() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": '["blood orange", "caramel apple", "almond praline"]'
    }

    with patch("requests.post", return_value=mock_response):
        notes = extract_flavour_notes_llm("Tastes of blood orange and almond praline.", title="Pink Bourbon")
        assert notes == ["blood orange", "caramel apple", "almond praline"]


@pytest.mark.unit
def test_extract_flavour_notes_fallback_when_server_down() -> None:
    with patch("requests.post", side_effect=requests.RequestException("Connection refused")):
        notes = extract_flavour_notes_llm("Delicious filter coffee.", title="Single Origin")
        assert notes is None


@pytest.mark.unit
def test_infer_flavour_notes_sqlite_caching(tmp_path) -> None:
    db_path = tmp_path / "test_history.sqlite3"
    product = {
        "title": "Colombia Pink Bourbon",
        "body_html": "<p>Flavour notes: Blood Orange, Caramel Apple, Almond Praline</p>",
    }

    # First call extracts and writes to cache
    notes1 = infer_flavour_notes(product, database_path=db_path, use_llm=False)
    assert "Blood Orange" in notes1

    # Verify cached in database
    content_hash = compute_content_hash(product["title"], "Flavour notes: Blood Orange, Caramel Apple, Almond Praline")
    cached = get_cached_flavour_notes(content_hash, db_path)
    assert cached == notes1

    # Second call reads from cache without calling extractor
    notes2 = infer_flavour_notes(product, database_path=db_path, use_llm=False)
    assert notes2 == notes1
