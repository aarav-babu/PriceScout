# PriceScout

Flask web app that estimates resale prices for mobiles, laptops, and vehicles using web scraping (Selenium/Firefox against cars24.com) plus a scikit-learn model. Data is stored in a MySQL/MariaDB database named `capstone`.

## Cursor Cloud specific instructions

### Services

- Web app (`app.py`): Flask dev server on `http://127.0.0.1:5000`. This is the primary product.
- Database: MariaDB serving the `capstone` schema. The app connects as `root` with an empty password over TCP (`127.0.0.1:3306`); this is already configured in the VM snapshot.
- Selenium scraper (`UserInput.py` / `runscraper.py`) and the optional Celery/Redis worker (`celery_worker.py`) are NOT runnable here: they require a Firefox GUI and live external access to cars24.com. The core register/login/post flows work without them. The `/postdata/price` route triggers the scraper, so it will not complete in this environment.

### Running

- Python deps live in `.venv` (created by the update script). Run the app with `.venv/bin/python app.py` (debug mode + hot reload are already enabled in `app.py`).
- MariaDB is installed via apt but there is no systemd here. Start it manually before running the app: `sudo mariadbd-safe &` then confirm with `sudo mysqladmin ping`. The data directory (including the imported `capstone` schema) persists in the snapshot.
- If the `capstone` database is ever missing, recreate it with `sudo mysql -e "CREATE DATABASE IF NOT EXISTS capstone;"` and import `sudo mysql capstone < capstone.sql`.

### Notes

- There is no automated test suite or linter configured. Use `.venv/bin/python -m py_compile *.py` as a basic syntax check.
- Database credentials are hardcoded in `app.py`, `runscraper.py` (host `localhost`, user `root`, empty password, db `capstone`).
