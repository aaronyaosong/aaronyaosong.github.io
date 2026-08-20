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

METADATA_EXTRACTION_PROMPT = """You are an expert specialty coffee analyst. Extract the metadata from the following coffee listing:
1. flavour_notes: List of specific taste/flavour descriptors (e.g. fruits, spices, chocolate).
2. origin_country: Country where the coffee was grown (e.g. "Ethiopia", "Colombia", "Kenya", or "unknown").
3. producer: Producer, farmer, washing station, estate, or exporter name (or "unknown").
4. process: Processing method (e.g. "Washed", "Natural", "Honey", "Anaerobic Natural", "Decaf", or "unknown").
5. varietal: Botanical variety of the coffee tree (e.g. "Geisha", "Caturra", "Heirloom", "SL28", or "unknown").

Output JSON format:
{
  "flavour_notes": ["..."],
  "origin_country": "...",
  "producer": "...",
  "process": "...",
  "varietal": "..."
}"""


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


def _parse_metadata_json(text: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try extracting JSON object substring
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    if not isinstance(data, dict):
        return None

    raw_notes = data.get("flavour_notes") or data.get("notes") or []
    if isinstance(raw_notes, str):
        notes_list = [n.strip() for n in raw_notes.split(",") if n.strip()]
    elif isinstance(raw_notes, list):
        notes_list = [str(n).strip() for n in raw_notes if str(n).strip()]
    else:
        notes_list = []

    cleaned_notes = []
    seen = set()
    for item in notes_list:
        desc = _clean_descriptor(item)
        if desc and len(desc) > 2 and desc not in seen:
            seen.add(desc)
            cleaned_notes.append(desc)

    def clean_field(val: Any) -> str:
        s = str(val or "").strip(" {}[]'\",.:;`")
        if not s or s.lower() in ("unknown", "n/a", "none", "null"):
            return "unknown"
        return s

    return {
        "flavour_notes": ", ".join(n.title() for n in cleaned_notes) if cleaned_notes else "unknown",
        "origin_country": clean_field(data.get("origin_country") or data.get("origin")),
        "producer": clean_field(data.get("producer") or data.get("farm")),
        "process": clean_field(data.get("process")),
        "varietal": clean_field(data.get("varietal") or data.get("variety")),
    }


def extract_flavour_notes_llm(
    description: str,
    title: str = "",
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 15.0,
) -> list[str] | None:
    if not description and not title:
        return None

    local_url = base_url or os.getenv("LOCAL_LLM_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
    local_url = local_url.rstrip("/")
    model_name = model or os.getenv("LOCAL_LLM_MODEL") or "llama3.2:1b"

    content_to_analyze = f"Title: {title}\nDescription: {description}".strip()

    # 1. Native Ollama API
    ollama_endpoint = f"{local_url}/api/generate"
    ollama_payload = {
        "model": model_name,
        "prompt": f"{EXTRACTION_PROMPT}\n\nCoffee Listing:\n{content_to_analyze}\n\nJSON array:",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 80,
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

    # 2. OpenAI-compatible local endpoint
    openai_compat_endpoint = f"{local_url}/v1/chat/completions"
    chat_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": content_to_analyze},
        ],
        "temperature": 0.1,
        "max_tokens": 80,
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


def extract_coffee_metadata_llm(
    description: str,
    title: str = "",
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 15.0,
) -> dict[str, Any] | None:
    """
    Extracts process, origin_country, producer, varietal, and flavour_notes in a single LLM call.
    """
    if not description and not title:
        return None

    local_url = base_url or os.getenv("LOCAL_LLM_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
    local_url = local_url.rstrip("/")
    model_name = model or os.getenv("LOCAL_LLM_MODEL") or "llama3.2:1b"

    content_to_analyze = f"Title: {title}\nDescription: {description}".strip()

    # 1. Native Ollama API
    ollama_endpoint = f"{local_url}/api/generate"
    ollama_payload = {
        "model": model_name,
        "prompt": f"{METADATA_EXTRACTION_PROMPT}\n\nCoffee Title: {title}\nDescription: {description}\n\nOutput JSON:",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 150,
        },
    }

    try:
        response = requests.post(ollama_endpoint, json=ollama_payload, timeout=timeout)
        if response.status_code == 200:
            body = response.json()
            raw_response = body.get("response", "")
            meta = _parse_metadata_json(raw_response)
            if meta:
                return meta
    except (requests.RequestException, ValueError):
        pass

    # 2. OpenAI-compatible local endpoint
    openai_compat_endpoint = f"{local_url}/v1/chat/completions"
    chat_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": METADATA_EXTRACTION_PROMPT},
            {"role": "user", "content": content_to_analyze},
        ],
        "temperature": 0.1,
        "max_tokens": 150,
    }

    try:
        response = requests.post(openai_compat_endpoint, json=chat_payload, timeout=timeout)
        if response.status_code == 200:
            body = response.json()
            choices = body.get("choices", [])
            if choices:
                raw_response = choices[0].get("message", {}).get("content", "")
                meta = _parse_metadata_json(raw_response)
                if meta:
                    return meta
    except (requests.RequestException, ValueError):
        pass

    return None
