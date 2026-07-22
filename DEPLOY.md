# Deploying PriceScout

PriceScout is a Flask app backed by MySQL/MariaDB. All configuration is read
from environment variables (see `.env.example`), so the same code runs locally,
in Docker, or on a hosted platform.

By default `ENABLE_LIVE_SCRAPING=false`, so prices are estimated by training the
model on the bundled market dataset (`new_cars.csv`). This means **no browser is
required** and the app works on browserless free tiers. Live Selenium scraping
is an opt-in path for machines that have Firefox installed.

## Option 1: Vercel (free, serverless)

The app ships with `api/index.py` (a WSGI entrypoint) and `vercel.json` that
routes all traffic to it via the `@vercel/python` runtime. `vercel.json` already
sets `ENABLE_LIVE_SCRAPING=false` (serverless hosts have no browser) and
`DATA_DIR=/tmp` (the only writable path), and `.vercelignore` trims the bundle.

1. Provision a free external MySQL (Vercel has no managed MySQL - see providers
   below) and import the schema: `mysql -h <host> -u <user> -p <db> < capstone.sql`
2. Push this repo to GitHub and "Import Project" in Vercel.
3. In Project Settings -> Environment Variables add: `DB_HOST`, `DB_PORT`,
   `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and a strong `SECRET_KEY`.
4. Deploy. Health check: `https://<app>.vercel.app/health`.

Constraints on Vercel/serverless: no live Selenium scraping (pricing uses the
bundled-dataset model), the filesystem is read-only except `/tmp`, and requests
have execution-time limits - all handled by the defaults above.

## Note on Netlify

Netlify Functions support JavaScript/TypeScript and Go, **not** Python, so a
Flask backend cannot run on Netlify Functions. Use Vercel (above) for the Python
app, or the Docker/Render options below for a persistent server. Netlify is only
suitable here if you later split off a separate static frontend that calls the
API hosted elsewhere.

## Option 2: Docker Compose (easiest, fully free / self-host)

Runs the app and a MySQL database together. The schema in `capstone.sql` is
imported automatically on first boot.

```bash
cp .env.example .env      # optional: adjust values
docker compose up --build
```

App: http://localhost:5000  ·  Health check: http://localhost:5000/health

## Option 3: Render (free web tier)

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
| `SCRAPER_SOURCE` | `cars24` | Live scraper source: `cars24` or `facebook_marketplace` |
| `SELENIUM_HEADLESS` | `true` | Run Firefox headless when live scraping is enabled |
| `DATA_DIR` | app dir | Writable dir for CSV logs; set to `/tmp` on serverless hosts |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Dev server bind address |
