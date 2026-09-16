# PriceScout

## Active public deployment

- The live Render site runs `public_app:app`, uses `requirements-public.txt`, and
  follows `main`. GitHub Actions deploys after tests and secret scanning; native
  Render auto-deploy is off to avoid duplicate or unchecked releases.
- Public templates are under `templates/public/`; preserve the green/cream design.
- `account_pages.py` and `account_store.py` provide accounts and saved electronics.
  Production uses Neon through `DATABASE_URL`; local development uses SQLite in
  ignored `instance/`. Never configure ephemeral SQLite for hosted accounts.
- `live_prices.py` contains the existing public car search. Phones/laptops save
  product details and explicitly show unavailable pricing; do not invent prices.
- Run `python -m unittest discover -s tests -v` with both requirement files
  installed. GitHub CI includes the research-pipeline tests as well as public tests.
- The existing MySQL/Celery code is a separate research application. Preserve it;
  the instructions below describe that application, not the public Render process.

Flask web app that estimates resale prices for mobiles, laptops, and vehicles using authorized marketplace APIs plus scikit-learn models. Data is stored in a MySQL/MariaDB database named `capstone`.

## Cursor Cloud specific instructions

### Services

- Web app (`app.py`): Flask dev server on `http://127.0.0.1:5000`. This is the primary product. `GET /health` returns JSON and is used as the deploy health check.
- Database: MariaDB serving the `capstone` schema. Connection is configured via `DB_*` env vars (see `.env.example`), defaulting to `root`@`127.0.0.1:3306` with an empty password and db `capstone` — matching the VM snapshot. The connection is lazy/reconnecting, so the app boots even if the DB is down (`/health` reports `database: down`).
- Pricing: by default `PIPELINE_ENABLED=false`, so `/postdata/price` uses the cached `new_cars.csv` vehicle fallback; mobiles and laptops remain pending. With the pipeline enabled, Flask enqueues work and never calls providers or trains in the request path.
- Authorized provider clients live in `marketplace_providers.py`. eBay Browse supplies active asking-price comparables after credentials and approval; NHTSA vPIC supplies vehicle metadata only. Cars24, Facebook Marketplace, and Craigslist browser scraping are deliberately excluded. See `DATA_SOURCES.md`.
- Per-post CSV logs are written to `DATA_DIR` (default: app dir). Writes are best-effort and skipped on read-only filesystems, so pricing still works on serverless hosts.
- The hosted pipeline uses Redis, Celery worker, and Celery Beat. `pricing_pipeline.py` handles adaptive collection, retention, versioned model storage, and inference; no browser is required.

### Running

- Python deps live in `.venv` (created by the update script). Run the app with `.venv/bin/python app.py` (debug mode + hot reload are already enabled in `app.py`).
- MariaDB is installed via apt but there is no systemd here. Start it manually before running the app: `sudo mariadbd-safe &` then confirm with `sudo mysqladmin ping`. The data directory (including the imported `capstone` schema) persists in the snapshot.
- If the `capstone` database is ever missing, recreate it with `sudo mysql -e "CREATE DATABASE IF NOT EXISTS capstone;"` and import `sudo mysql capstone < capstone.sql`.

### Deployment

- All config is env-driven (`.env.example`). `gunicorn app:app` is the production server (`Procfile`, `Dockerfile`).
- Vercel: `api/index.py` is the WSGI entrypoint and `vercel.json` routes all traffic to it; `.vercelignore` trims the bundle. The included config uses fallback mode. A full pipeline requires separately hosted persistent workers and Redis.
- `docker compose up --build` runs the research web + worker + scheduler + Redis + MariaDB and auto-imports `capstone.sql`. See `DEPLOY.md` for that stack; the public Render deployment is documented in `DEPLOYMENT.md`.

### Notes

- Automated tests live in `tests/`; run the full suite as described above.
- The hosted market model covers all categories after enough authorized observations exist. The bundled fallback covers vehicles only.
