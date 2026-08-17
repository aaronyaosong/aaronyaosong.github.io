from __future__ import annotations

import argparse
from pathlib import Path

from nz_coffee_tracker.database import has_current_data
from nz_coffee_tracker.scaffold import scaffold_scraper
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
    parser.add_argument(
        "--database",
        type=Path,
        help="SQLite history database path (default: <out-dir>/history.sqlite3)",
    )
    parser.add_argument(
        "--new-scraper",
        metavar="NAME",
        help="Create a new scraper module and integration-test stub",
    )
    parser.add_argument(
        "--website",
        help="Website hostname for --new-scraper, for example roaster.example",
    )
    parser.add_argument(
        "--collection",
        help="Shopify collection handle for --new-scraper",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.new_scraper:
        if not args.website or not args.collection:
            parser.error("--new-scraper requires --website and --collection")
        try:
            scraper_path, test_path = scaffold_scraper(
                args.new_scraper,
                args.website,
                args.collection,
                Path.cwd(),
            )
        except (FileExistsError, ValueError) as error:
            parser.error(str(error))
        print(f"scraper: {scraper_path}")
        print(f"test: {test_path}")
        print("Review the generated scraper, then register it in tracker.py.")
        return 0

    # `None` means "include all categories" in the tracker pipeline.
    allowed_categories = None if args.no_category_filter else _parse_categories(args.categories)
    out_dir = Path(args.out_dir)
    database_path = args.database or out_dir / "history.sqlite3"
    if has_current_data(
        database_path,
        out_dir,
        args.format,
        include_unavailable=args.all,
        category_filter=allowed_categories,
    ):
        print("Data already scraped today; skipping scrape.")
        return 0

    listings = collect_listings(
        include_unavailable=args.all,
        allowed_categories=allowed_categories,
        database_path=database_path,
    )
    written = persist_snapshots(
        listings,
        out_dir,
        output_format=args.format,
        database_path=database_path,
        include_unavailable=args.all,
        category_filter=allowed_categories,
    )

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
