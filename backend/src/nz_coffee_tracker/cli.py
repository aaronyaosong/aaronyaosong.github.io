from __future__ import annotations

import argparse
from pathlib import Path

from nz_coffee_tracker.tracker import collect_listings, persist_snapshots


def _parse_categories(raw: str) -> set[str]:
    # Accept comma-separated CLI input such as "filter roast,espresso roast".
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track NZ coffee availability from selected roasters.")
    parser.add_argument(
        "--out-dir",
        default="data",
        help="Directory for output files (default: data)",
    )
    parser.add_argument(
        "--format",
        default="both",
        choices=["json", "csv", "both"],
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include unavailable products (default: only currently available)",
    )
    parser.add_argument(
        "--categories",
        default="filter roast,espresso roast",
        help="Comma-separated roast categories to include (default: filter roast,espresso roast)",
    )
    parser.add_argument(
        "--no-category-filter",
        action="store_true",
        help="Disable category filtering and include all categories",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # `None` means "include all categories" in the tracker pipeline.
    allowed_categories = None if args.no_category_filter else _parse_categories(args.categories)
    listings = collect_listings(include_unavailable=args.all, allowed_categories=allowed_categories)
    written = persist_snapshots(listings, Path(args.out_dir), output_format=args.format)

    print(f"Collected {len(listings)} products.")
    if allowed_categories is None:
        print("Category filter: disabled")
    else:
        print(f"Category filter: {', '.join(sorted(allowed_categories))}")
    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
