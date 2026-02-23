# PriceScout

**A mini production data platform for real-time pricing intelligence across vehicles, mobiles, and laptops.**

PriceScout ingests listings via web forms and Playwright-based scraping, runs ML-powered price predictions, and surfaces operator-grade analytics through a Streamlit dashboard — all backed by a deduplicated, indexed MySQL data store.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Compose                           │
│                                                              │
│  ┌─────────────┐    ┌──────────┐    ┌───────────────────┐   │
│  │  Streamlit   │◄──►│  MySQL   │◄──►│ Flask + Playwright│   │
│  │  :8501       │    │  :3306   │    │  :5000            │   │
│  │  Operator    │    │          │    │  Web App +        │   │
│  │  Console     │    │ capstone │    │  Scraper +        │   │
│  │              │    │   db     │    │  ML Model         │   │
│  └─────────────┘    └──────────┘    └───────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### Data Modeling
- Normalized schema: separate `vehicle`, `mobiles`, `laptops` tables with foreign keys to `users`
- Unified `price` table links valuations across all categories
- `ingestion_log` table provides full observability into every data pipeline run

### Dedupe & Idempotency
- Unique composite constraints on each listing table prevent duplicate records at the DB level
- `INSERT ... ON DUPLICATE KEY UPDATE` upserts ensure re-submissions update rather than duplicate
- Ingestion stats track `listings_deduped` counts per run

### Retries & Rate Limiting
- `retry_with_backoff` decorator: 3 attempts with exponential backoff (2/4/8s)
- `RateLimiter` class enforces configurable minimum delay between scrape requests (`SCRAPE_RATE_LIMIT` env)
- `IngestionStats` dataclass tracks processed/inserted/error counts with computed error rate

### Customer Outcome
- End-to-end: user submits a listing, system scrapes comparable data, ML model predicts fair price
- Operator console provides real-time visibility into listing inventory, price distributions, and pipeline health

---

## Quick Start

```bash
# Start all services (Flask, Streamlit, MySQL)
docker compose up --build

# Fresh start (reset database)
docker compose down -v && docker compose up --build
```

| Service    | URL                          |
|------------|------------------------------|
| Flask App  | http://localhost:5001        |
| Streamlit  | http://localhost:8501        |

**Demo credentials:** `demo_user` / `demo123`

---

## Tech Stack

| Layer         | Technology                           |
|---------------|--------------------------------------|
| Web App       | Flask, Jinja2, Bootstrap             |
| Database      | MySQL 8.0                            |
| Scraping      | Playwright (Chromium), Pandas        |
| ML            | scikit-learn (model.py)              |
| Dashboard     | Streamlit                            |
| Auth          | Werkzeug (password hashing)          |
| Containers    | Docker, Docker Compose               |

---

## Project Structure

```
PriceScout/
├── app.py                    # Flask application (routes, upserts, ingestion logging)
├── UserInput.py              # Scraper (rate limiter, retry, ingestion stats)
├── model.py                  # ML price prediction
├── config.py                 # App configuration
├── streamlit_app.py          # Operator console (3-tab dashboard)
├── capstone.sql              # Schema (tables, indexes, unique constraints, ingestion_log)
├── seed_data.sql             # Demo data (~40 listings, ingestion history)
├── Dockerfile                # Flask container
├── Dockerfile.streamlit      # Streamlit container
├── docker-compose.yml        # Multi-service orchestration
├── requirements.txt          # Flask dependencies
├── requirements-streamlit.txt# Streamlit dependencies
├── templates/                # Jinja2 HTML templates
│   ├── home.html
│   ├── index.html
│   ├── postdata/             # Listing submission forms
│   ├── userdata/             # Auth & profile pages
│   ├── navigbar/             # Navigation components
│   ├── misc/                 # About, contact pages
│   └── errors/               # 404, 500 pages
└── static/                   # CSS, JS, images
```

---

## Environment Variables

| Variable              | Default                              | Description                     |
|-----------------------|--------------------------------------|---------------------------------|
| `FLASK_SECRET_KEY`    | `change-this-to-a-random-secret-key` | Flask session secret            |
| `DB_HOST`             | `db`                                 | MySQL hostname                  |
| `DB_USER`             | `root`                               | MySQL user                      |
| `DB_PASSWORD`         | (empty)                              | MySQL password                  |
| `DB_NAME`             | `capstone`                           | MySQL database name             |
| `WEB_PORT`            | `5001`                               | Flask exposed port              |
| `STREAMLIT_PORT`      | `8501`                               | Streamlit exposed port          |
| `SCRAPE_RATE_LIMIT`   | `2`                                  | Min seconds between scrape requests |
