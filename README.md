# PriceScout

PriceScout estimates resale prices for **mobile phones**, **laptops**, and **vehicles** using machine learning trained on comparable market listings. Users can sign up, submit item details, and receive a valuation backed by a scikit-learn model.

The app is built with **Flask**, stores data in **MySQL/MariaDB**, and is configured entirely through environment variables so it runs the same way locally, in Docker, or on hosted platforms such as Vercel and Render.

## Features

- Guided valuation forms for cars, mobiles, and laptops
- User accounts with saved valuation history
- Vehicle price estimates via a trained regression model (mobile/laptop pricing is stored but not yet modeled)
- Pluggable live scraping sources when running on a machine with a browser (optional)
- Health check endpoint at `/health` for deploy monitoring

## Requirements

- **Python 3.10+**
- **MySQL or MariaDB** (local install, Docker, or a managed host)
- **Firefox** — only if you enable live scraping (`ENABLE_LIVE_SCRAPING=true`)

Selenium, Celery, and Redis are optional dependencies used only for live scraping and the legacy background worker; they are not needed for the default, browserless flow.

## Local setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd PriceScout
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` as needed. The defaults target a local database at `localhost:3306` with user `root`, an empty password, and database `capstone`.

### 3. Set up the database

**Option A — existing local MySQL/MariaDB**

```bash
mysql -u root -e "CREATE DATABASE IF NOT EXISTS capstone;"
mysql -u root capstone < capstone.sql
```

**Option B — Docker Compose (app + database together)**

```bash
cp .env.example .env   # optional: adjust values
docker compose up --build
```

This starts MariaDB (schema imported from `capstone.sql` on first boot) and the web app. Open http://localhost:5000.

### 4. Run the app

```bash
.venv/bin/python app.py
```

The dev server listens on http://127.0.0.1:5000 by default (`HOST` / `PORT` in `.env`). Confirm it is up:

```bash
curl http://127.0.0.1:5000/health
```

You should see JSON with `"status": "ok"` and a `"database"` field (`"up"` when MySQL is reachable).

### Optional: live scraping

By default, `ENABLE_LIVE_SCRAPING=false`. Vehicle prices are estimated by training the model on the bundled dataset (`new_cars.csv`) — no browser required.

To scrape live listings instead (local development only):

1. Install [Firefox](https://www.mozilla.org/firefox/).
2. In `.env`, set `ENABLE_LIVE_SCRAPING=true` and optionally `SCRAPER_SOURCE=cars24` or `facebook_marketplace`.
3. Read the [Web scraping ethics](#web-scraping-ethics) section before enabling this.

If live scraping fails or returns no rows, the app automatically falls back to the cached dataset.

## Deployment

PriceScout is ready for hosted environments. All configuration is env-driven; see `.env.example` for the full list.

| Platform | Notes |
| --- | --- |
| **Vercel** | Serverless Python via `api/index.py` and `vercel.json`. Requires an external MySQL. Live scraping is disabled by default (no browser on serverless). |
| **Docker Compose** | Easiest full-stack local or self-hosted run — app + MariaDB with auto schema import. |
| **Render** | Persistent web service; use `render.yaml` and an external MySQL. |
| **Netlify** | Netlify Functions do **not** support Python/Flask. Host the API on Vercel or Render instead. |

Step-by-step deploy instructions, free MySQL provider suggestions, and the environment variable reference are in **[DEPLOY.md](DEPLOY.md)**.

Production serving uses Gunicorn (`gunicorn app:app` — see `Procfile` and `Dockerfile`).

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `3306` | Database port |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | (empty) | Database password |
| `DB_NAME` | `capstone` | Database name |
| `SECRET_KEY` | `dev-insecure-change-me` | Flask session secret — set a strong value in production |
| `ENABLE_LIVE_SCRAPING` | `false` | Use live Selenium scraping instead of the bundled dataset |
| `SCRAPER_SOURCE` | `cars24` | Live scraper: `cars24` or `facebook_marketplace` |
| `CACHED_CARS_DATASET` | `new_cars.csv` | Dataset used when live scraping is off |
| `SELENIUM_HEADLESS` | `true` | Run Firefox headless when live scraping is enabled |
| `DATA_DIR` | app directory | Writable directory for CSV logs; use `/tmp` on serverless hosts |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Dev server bind address |

## Web scraping ethics

PriceScout can optionally fetch comparable listings from third-party marketplaces to refresh training data. **Live scraping is off by default** and is intended for local development or environments you control — not for unattended production scraping without explicit permission.

Before enabling `ENABLE_LIVE_SCRAPING=true`, please:

1. **Read the site's Terms of Service and `robots.txt`.** Only scrape sources that permit automated access for your use case. If a site prohibits scraping, do not enable live scraping against it.
2. **Respect rate limits and server load.** The bundled scrapers include basic delays; do not remove them or run aggressive parallel jobs against production sites.
3. **Use data responsibly.** Listing data may include personal or commercial information. Store only what you need for valuation, do not republish scraped content, and comply with applicable privacy laws.
4. **Prefer the bundled dataset for demos and hosting.** The default path (`ENABLE_LIVE_SCRAPING=false`) trains on `new_cars.csv` and works on browserless hosts (Vercel, Render, etc.) without touching external sites.
5. **Treat experimental sources with caution.** The Facebook Marketplace scraper (`SCRAPER_SOURCE=facebook_marketplace`) is unverified: Facebook requires login, restricts automated access, and may block requests. It is provided as a starting point for research, not as a supported production integration.
6. **Attribute and comply.** PriceScout started as an academic capstone project ([IEEE paper](https://ieeexplore.ieee.org/document/10574547)). If you extend scraping for research or publication, document your sources and methods and follow your institution's ethics guidelines.

Adding a new scraper: subclass `BaseScraper` in `scrapers.py`, register it in `REGISTRY`, and document any site-specific restrictions in your fork's README.

## Project structure

```
app.py              Flask routes and pricing orchestration
model.py            scikit-learn training and prediction
scrapers.py         Pluggable live scraping sources
UserInput.py        Selenium helpers for Cars24 (live mode)
capstone.sql        Database schema
new_cars.csv        Bundled vehicle market dataset
api/index.py        Vercel WSGI entrypoint
templates/          HTML templates
static/             CSS and client-side scripts
```

## Development notes

- Syntax check: `.venv/bin/python -m py_compile *.py`
- The pricing model currently covers **vehicles/cars** only; mobiles and laptops persist submissions but do not yet return ML estimates.
- Optional Celery worker (`celery_worker.py`, `runscraper.py`) is not used by the default request flow.

## License

See repository license file if present.
