# NZ Coffee Release Tracker

Track what coffee is currently available in New Zealand, starting with:

- Rocket Coffee (`rocketcoffee.co.nz`)
- Atomic Coffee (`atomiccoffee.co.nz`)
- Ozone Coffee (`ozonecoffee.co.nz`)
- Coffee Embassy (`coffeeembassy.co.nz`)
- Eternal Coffee (`eternalcoffee.co.nz`)

This tracker uses the Shopify product JSON feeds exposed by the supported roasters and exports snapshots to JSON/CSV plus a SQLite history database.

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
- `history.sqlite3` (append-only historical database)

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
- `--database path/to/history.sqlite3` choose the SQLite history database path

Create a new Shopify scraper scaffold:

```bash
PYTHONPATH=backend/src python -m nz_coffee_tracker.cli \
	--new-scraper example_coffee \
	--website examplecoffee.co.nz \
	--collection coffee
```

This creates a site scraper in `backend/src/nz_coffee_tracker/scrapers/` and an integration-test stub in `backend/tests/integration/`. Review the generated field mapping and register the scraper in `tracker.py` before running it.

When the matching database run and requested latest output files already contain data from today (UTC), the CLI skips scraping. If the database or requested output is missing or empty, it scrapes again.

## Testing

Run backend tests:

```bash
PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests
```

Run frontend tests:

```bash
cd frontend
npm install
npm run test:unit
npm run test:integration
npm run test:e2e
```

Run integrated backend + frontend tests:

```bash
bash scripts/test_all.sh
```

The integrated test script automatically uses `.venv/bin/python` when present and otherwise falls back to the active `python`/`python3` on your `PATH`.

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

## CI

Continuous integration runs from `.github/workflows/ci.yml` and includes:

- backend pytest suite
- frontend unit tests
- frontend integration tests
- frontend Playwright e2e tests

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
- `origin_country`
- `producer`
- `process`
- `decaf`
- `description`
- `flavour_notes`

The SQLite database contains `scrape_runs`, `listings`, and `size_prices` tables. Each tracker run appends a new scrape run and its listing and size-price observations, making historical availability and price analysis possible without parsing snapshot files.

## Notes

- This is an initial version optimized for availability tracking.
- Future steps can add more NZ roasters, scheduling, and change alerts.
