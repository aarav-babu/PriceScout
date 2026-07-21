# PriceScout

Flask web app that estimates resale prices for mobiles, laptops, and vehicles using web scraping (Selenium/Firefox against cars24.com) plus a scikit-learn model. Data is stored in a MySQL/MariaDB database named `capstone`.

## Cursor Cloud specific instructions

### Services

- Web app (`app.py`): Flask dev server on `http://127.0.0.1:5000`. This is the primary product. `GET /health` returns JSON and is used as the deploy health check.
- Database: MariaDB serving the `capstone` schema. Connection is configured via `DB_*` env vars (see `.env.example`), defaulting to `root`@`127.0.0.1:3306` with an empty password and db `capstone` — matching the VM snapshot. The connection is lazy/reconnecting, so the app boots even if the DB is down (`/health` reports `database: down`).
- Pricing: by default `ENABLE_LIVE_SCRAPING=false`, so `/postdata/price` estimates the price by training the scikit-learn model on the bundled `new_cars.csv` dataset. This path is browserless and works here end-to-end (only the vehicle/car flow has a model). Set `ENABLE_LIVE_SCRAPING=true` only on a machine with Firefox to use live Selenium scraping (`UserInput.py`); it falls back to the cached-dataset model on any failure.
- Optional Celery/Redis worker (`celery_worker.py`, `runscraper.py`) is NOT used by the default flow and needs Redis + a browser.

### Running

- Python deps live in `.venv` (created by the update script). Run the app with `.venv/bin/python app.py` (debug mode + hot reload are already enabled in `app.py`).
- MariaDB is installed via apt but there is no systemd here. Start it manually before running the app: `sudo mariadbd-safe &` then confirm with `sudo mysqladmin ping`. The data directory (including the imported `capstone` schema) persists in the snapshot.
- If the `capstone` database is ever missing, recreate it with `sudo mysql -e "CREATE DATABASE IF NOT EXISTS capstone;"` and import `sudo mysql capstone < capstone.sql`.

### Deployment

- All config is env-driven (`.env.example`). `gunicorn app:app` is the production server (`Procfile`, `Dockerfile`).
- `docker compose up --build` runs the app + a MySQL that auto-imports `capstone.sql` — the easiest full-stack/local run. `render.yaml` targets Render's free web tier (bring your own free MySQL). See `DEPLOY.md`.

### Notes

- There is no automated test suite or linter configured. Use `.venv/bin/python -m py_compile *.py` as a basic syntax check.
- The pricing model only covers vehicles/cars; mobiles and laptops persist data but have no price model yet.
