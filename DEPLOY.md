# Deploying PriceScout

PriceScout is a Flask app backed by MySQL/MariaDB. All configuration is read
from environment variables (see `.env.example`), so the same code runs locally,
in Docker, or on a hosted platform.

By default `ENABLE_LIVE_SCRAPING=false`, so prices are estimated by training the
model on the bundled market dataset (`new_cars.csv`). This means **no browser is
required** and the app works on browserless free tiers. Live Selenium scraping
is an opt-in path for machines that have Firefox installed.

## Option 1: Docker Compose (easiest, fully free / self-host)

Runs the app and a MySQL database together. The schema in `capstone.sql` is
imported automatically on first boot.

```bash
cp .env.example .env      # optional: adjust values
docker compose up --build
```

App: http://localhost:5000  ·  Health check: http://localhost:5000/health

## Option 2: Render (free web tier)

Render has a free web service tier but no managed MySQL, so provision a free
MySQL first (see providers below) and set its credentials as env vars.

1. Create a free MySQL database and note host/port/user/password/db name.
2. Import the schema: `mysql -h <host> -u <user> -p <db> < capstone.sql`
3. Push this repo to GitHub and create a new Render Blueprint from `render.yaml`.
4. Set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in the Render dashboard.

## Free MySQL providers

- Railway (trial credits) — https://railway.app
- Aiven (free MySQL plan) — https://aiven.io
- Clever Cloud (free MySQL) — https://clever-cloud.com

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python app.py
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `3306` | Database port |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | (empty) | Database password |
| `DB_NAME` | `capstone` | Database name |
| `SECRET_KEY` | `dev-insecure-change-me` | Flask session secret (set a strong value in prod) |
| `ENABLE_LIVE_SCRAPING` | `false` | Use live Selenium scraping instead of the cached-dataset model |
| `SELENIUM_HEADLESS` | `true` | Run Firefox headless when live scraping is enabled |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Dev server bind address |
