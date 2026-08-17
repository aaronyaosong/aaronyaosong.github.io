# NZ Coffee Release Tracker

Track what coffee is currently available in New Zealand, starting with:

- Rocket Coffee (`rocketcoffee.co.nz`)
- Atomic Coffee (`atomiccoffee.co.nz`)

This tracker uses the Shopify product JSON feeds exposed by both stores and exports snapshots to JSON/CSV.

## Project Layout

- `frontend/` static website files for GitHub Pages
- `backend/` Python scraper code and tests

## Frontend (GitHub Pages)

This repo includes a static frontend:

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`

The app reads `frontend/data/latest.json` and renders searchable/filterable coffee cards.

To host on GitHub Pages:

1. Push this repo to GitHub.
2. In repo settings, enable Pages and set source to `Deploy from a branch`.
3. Select your main branch and root folder (`/`).
4. Open `https://<your-user>.github.io/<repo>/frontend/`.

Your site will load `frontend/data/latest.json` from the same repo.

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Run the tracker:

```bash
PYTHONPATH=backend/src python -m nz_coffee_tracker.cli --out-dir frontend/data
```

3. Check output files in `frontend/data/`:

- `latest.json`
- `latest.csv`
- timestamped snapshots (for history)

## Command Options

```bash
PYTHONPATH=backend/src python -m nz_coffee_tracker.cli --help
```

Useful flags:

- `--out-dir frontend/data` (recommended for the website)
- `--format json|csv|both` (default: `both`)
- `--all` include unavailable products (default is available-only)
- `--categories "filter roast,espresso roast"` include only selected categories
- `--no-category-filter` include all product categories

## Testing

Run all tests:

```bash
PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests
```

Run by layer:

```bash
PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests -m unit
PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests -m integration
PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests -m e2e
```

## Daily Backend Run (GitHub Actions)

A scheduled workflow is included at `.github/workflows/daily-scrape.yml`.

- Runs once per day (`0 18 * * *` UTC) and also supports manual trigger.
- Generates fresh data via the scraper.
- Keeps only `frontend/data/latest.json` for GitHub Pages.
- Commits and pushes updates automatically when the snapshot changes.

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
