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


EXTRACTION_PROMPT = """You are an expert coffee sensory analyst. Extract the taste, aroma, and flavour descriptors from this coffee listing.
Instructions:
1. Return ONLY specific tasting/flavour notes (e.g. "jasmine", "raspberry jam", "milk chocolate", "mandarin", "toffee", "irish whiskey").
2. Do NOT include origin names, farm/producer names, variety names (e.g. 'caturra', 'geisha'), brew equipment, or generic fluff words (e.g. 'delicious', 'clean', 'specialty coffee').
3. Keep descriptors short, clean, and lowercased (1 to 4 words per descriptor).
4. Output MUST be a valid JSON array of strings, for example: ["raspberry", "rhubarb", "dark chocolate"]. If no flavour notes exist, return [].
"""


def _parse_llm_json(text: str) -> list[str]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [str(item).strip().lower() for item in data if str(item).strip()]
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, list):
                    return [str(item).strip().lower() for item in val if str(item).strip()]
    except json.JSONDecodeError:
        pass

    # Regex fallback if JSON is embedded inside raw text
    match = re.search(r"\[\s*\"[^\"]+\"(?:\s*,\s*\"[^\"]+\")*\s*\]", cleaned)
    if match:
        try:
            items = json.loads(match.group(0))
            return [str(item).strip().lower() for item in items if str(item).strip()]
        except json.JSONDecodeError:
            pass

    return []


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
