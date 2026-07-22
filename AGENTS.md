# PriceScout

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
- `docker compose up --build` runs web + worker + scheduler + Redis + MariaDB and auto-imports `capstone.sql`. `render.yaml` targets the fallback web tier. See `DEPLOY.md`.

### Notes

- There is no automated test suite or linter configured. Use `.venv/bin/python -m py_compile *.py` as a basic syntax check.
- The hosted market model covers all categories after enough authorized observations exist. The bundled fallback covers vehicles only.
