# NZ Coffee Release Tracker

Track what coffee is currently available in New Zealand, starting with:

- Rocket Coffee (`rocketcoffee.co.nz`)
- Atomic Coffee (`atomiccoffee.co.nz`)

This tracker uses the Shopify product JSON feeds exposed by both stores and exports snapshots to JSON/CSV.

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the tracker:

```bash
PYTHONPATH=src python -m nz_coffee_tracker.cli
```

3. Check output files in `data/`:

- `latest.json`
- `latest.csv`
- timestamped snapshots (for history)

## Command Options

```bash
PYTHONPATH=src python -m nz_coffee_tracker.cli --help
```

Useful flags:

- `--out-dir data` (default: `data`)
- `--format json|csv|both` (default: `both`)
- `--all` include unavailable products (default is available-only)
- `--categories "filter roast,espresso roast"` include only selected categories
- `--no-category-filter` include all product categories

## Data Fields

Each row includes:

- `source`
- `product_id`
- `title`
- `category`
- `product_url`
- `available`
- `price_min_nzd`
- `price_max_nzd`
- `updated_at`
- `scraped_at`

## Notes

- This is an initial version optimized for availability tracking.
- Future steps can add more NZ roasters, scheduling, and change alerts.
