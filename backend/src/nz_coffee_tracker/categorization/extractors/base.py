from __future__ import annotations

from typing import Any

class BaseExtractor:
    @staticmethod
    def extract(product: dict[str, Any]) -> str:
        raise NotImplementedError
