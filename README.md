# PriceScout

PriceScout is a Flask app that estimates resale prices for vehicles, mobile
phones, and laptops. It stores accounts and valuations in MySQL/MariaDB and
uses an asynchronous market-data and model-training pipeline for hosted use.

## What it includes

- Guided valuation forms and saved valuation history
- Authorized active-listing collection through eBay's official Browse API
- NHTSA vPIC vehicle metadata client
- Demand-driven, volatility-adaptive collection schedules
- Versioned scikit-learn models stored in MariaDB
- Redis/Celery workers so external API calls and training never block Flask
- A bundled, browserless vehicle fallback when the pipeline is disabled
- `/health` endpoint for deployment checks

PriceScout does not ship Selenium or automate Cars24, Facebook Marketplace,
Craigslist, logins, CAPTCHAs, or undocumented endpoints. Read
[DATA_SOURCES.md](DATA_SOURCES.md) before enabling a provider.

## Quick start

The complete pipeline is easiest to run with Docker:

```bash
cp .env.example .env
# Add a strong SECRET_KEY and approved provider credentials.
docker compose up --build
```

This starts Flask, MariaDB, Redis, a Celery worker, and Celery Beat. Open
http://localhost:5000 and check http://localhost:5000/health.

To run only the browserless Flask fallback:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
mysql -u root -e "CREATE DATABASE IF NOT EXISTS capstone;"
mysql -u root capstone < capstone.sql
.venv/bin/python app.py
```

The fallback prices vehicles from `new_cars.csv`; mobile and laptop estimates
remain pending until the hosted pipeline has authorized market data.

## Pipeline

When a user submits an item, Flask registers one deduplicated brand/model query
and queues a pricing job. The worker uses fresh exact comparables when
available, otherwise collects from configured providers. Celery Beat:

- checks due queries every 15 minutes;
- trains and activates a model every six hours when enough valid observations
  exist;
- deletes observations after the configured contractual retention window.

Collection intervals are bounded by category and shorten when recent batch
median prices move more. Default baselines are six hours for mobiles and
twelve hours for vehicles and laptops.

The model learns active asking prices, not completed-sale or guaranteed
trade-in values. Marketplace geography and `TARGET_CURRENCY` must match.

## Main configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PIPELINE_ENABLED` | `false` | Queue API collection and pricing jobs |
| `CELERY_BROKER_URL` | local Redis | Celery broker |
| `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` | empty | Official Browse API credentials |
| `EBAY_MARKETPLACE_ID` | `EBAY_US` | Listing market |
| `TARGET_CURRENCY` | `USD` | Accepted and displayed market currency |
| `OBSERVATION_RETENTION_DAYS` | `7` | Raw observation retention ceiling |
| `MODEL_MINIMUM_ROWS` | `25` | Minimum rows before model activation |
| `CACHED_CARS_DATASET` | `new_cars.csv` | Vehicle fallback dataset |

See `.env.example` for cadence bounds and all database/server settings.

## Deployment

The full pipeline requires persistent web, worker, scheduler, Redis, and
MariaDB services. [DEPLOY.md](DEPLOY.md) documents Docker and split-service
hosting. Vercel and the included Render web blueprint run fallback mode unless
external workers and Redis are configured.

## Project structure

```text
app.py                     Flask routes and queue integration
marketplace_providers.py   Authorized API clients
pricing_pipeline.py        Collection, retention, scheduling, and inference
market_model.py            Versioned cross-category model
celery_worker.py           Worker tasks and Beat schedule
model.py                   Bundled vehicle fallback model
capstone.sql               Application and pipeline schema
```

Basic verification:

```bash
.venv/bin/python -m py_compile *.py api/*.py
.venv/bin/python -m unittest discover -s tests -v
```
