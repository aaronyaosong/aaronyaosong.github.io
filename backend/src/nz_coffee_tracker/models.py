from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class CoffeeListing:
    # Normalized record shape used across scrapers, storage, and frontend payloads.
    source: str
    product_id: int
    title: str
    category: str
    handle: str
    product_url: str
    available: bool
    price_min_nzd: float
    price_max_nzd: float
    updated_at: str
    scraped_at: str
    varietal: str = "unknown"
    size_prices: list[dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def now_utc_iso() -> str:
    # Use a consistent UTC timestamp format for snapshots and test determinism.
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
