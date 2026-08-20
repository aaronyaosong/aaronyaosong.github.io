from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any
import requests


def compute_content_hash(title: str, description: str) -> str:
    payload = f"{title.strip().lower()}\n{description.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


EXTRACTION_PROMPT = """Read the coffee description below and list ONLY the specific taste and aroma notes (such as fruits, chocolate, florals, spices, sweets).
Do not include origins, farms, brew equipment, or processing methods.
Return only a JSON array of the extracted tasting notes found in the text.
"""


NON_FLAVOUR_WORDS = {
    "coffee",
    "espresso",
    "filter",
    "roast",
    "beans",
    "natural",
    "washed",
    "blend",
    "origin",
    "ethiopia",
    "colombia",
    "brazil",
    "kenya",
    "flavor",
    "flavour",
    "aroma",
    "tasting",
    "notes",
    "taste",
}


def _clean_descriptor(raw: str) -> str:
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"^(?:a\s+|an\s+|the\s+|twist\s+of\s+|deep\s+hit\s+of\s+|notes?\s+of\s+|hints?\s+of\s+|flavou?rs?\s+of\s+)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" {}[]'\",.:;`")
    if cleaned in NON_FLAVOUR_WORDS:
        return ""
    return cleaned


def _parse_llm_json(text: str) -> list[str]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    raw_list: list[str] = []

    # 1. Standard JSON parsing
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            raw_list = [str(item) for item in data]
        elif isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, list):
                    raw_list.extend([str(item) for item in val])
                elif isinstance(val, str) and len(val) > 2:
                    raw_list.append(key if len(key) > 2 else val)
    except json.JSONDecodeError:
        pass

    # 2. Bracket or curly brace list fallback: ["a", "b"] or {"a", "b"}
    if not raw_list:
        quoted_items = re.findall(r'["\']([^"\']{2,40})["\']', cleaned)
        if quoted_items:
            raw_list = quoted_items

    # 3. Comma-separated fallback
    if not raw_list and "," in cleaned:
        raw_list = [part.strip() for part in cleaned.split(",") if part.strip()]

    seen = set()
    result = []
    for item in raw_list:
        desc = _clean_descriptor(item)
        if desc and len(desc) > 2 and desc not in seen:
            seen.add(desc)
            result.append(desc)

    return result


def extract_flavour_notes_llm(
    description: str,
    title: str = "",
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 15.0,
) -> list[str] | None:
    """
    Extracts tasting notes using a 100% local LLM (e.g. Ollama or LM Studio).
    No API keys required, completely offline and private.
    """
    if not description and not title:
        return None

    # Default to local Ollama instance (or user-defined LOCAL_LLM_URL / OLLAMA_HOST)
    local_url = base_url or os.getenv("LOCAL_LLM_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
    local_url = local_url.rstrip("/")
    model_name = model or os.getenv("LOCAL_LLM_MODEL") or "llama3.2:1b"

    content_to_analyze = f"Title: {title}\nDescription: {description}".strip()

    # 1. Try Native Ollama API (/api/generate with JSON format)
    ollama_endpoint = f"{local_url}/api/generate"
    ollama_payload = {
        "model": model_name,
        "prompt": f"{EXTRACTION_PROMPT}\n\nCoffee Listing:\n{content_to_analyze}\n\nJSON array:",
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 100,
        },
    }

    try:
        response = requests.post(ollama_endpoint, json=ollama_payload, timeout=timeout)
        if response.status_code == 200:
            body = response.json()
            raw_response = body.get("response", "")
            notes = _parse_llm_json(raw_response)
            if notes:
                return notes
    except (requests.RequestException, ValueError):
        pass

    # 2. Try OpenAI-compatible local endpoint (/v1/chat/completions, e.g. LM Studio, LocalAI)
    openai_compat_endpoint = f"{local_url}/v1/chat/completions"
    chat_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": content_to_analyze},
        ],
        "temperature": 0.1,
        "max_tokens": 100,
    }

    try:
        response = requests.post(openai_compat_endpoint, json=chat_payload, timeout=timeout)
        if response.status_code == 200:
            body = response.json()
            choices = body.get("choices", [])
            if choices:
                raw_response = choices[0].get("message", {}).get("content", "")
                notes = _parse_llm_json(raw_response)
                if notes:
                    return notes
    except (requests.RequestException, ValueError):
        pass

    return None
