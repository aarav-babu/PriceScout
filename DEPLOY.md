# Deploying PriceScout

PriceScout has four production roles:

1. Gunicorn serves Flask and reads completed valuations.
2. Redis carries pricing and scheduled collection jobs.
3. Celery workers call authorized provider APIs, store observations, and price
   listings.
4. Celery Beat checks due queries every 15 minutes, trains a versioned model
   every six hours, and removes expired observations daily.

MariaDB stores app records, query schedules, short-lived market observations,
and serialized model versions. No browser is required.

## Full pipeline with Docker Compose

This is the reference deployment and can run on any Docker-capable VM:

```bash
cp .env.example .env
# Set SECRET_KEY, DB_PASSWORD, approved eBay credentials, marketplace, currency.
docker compose up --build
```

Services are `web`, `worker`, `scheduler`, `redis`, and `db`. MariaDB imports
`capstone.sql` on first startup. Existing databases are upgraded additively by
the pipeline's `ensure_pipeline_schema()` function.

App: `http://localhost:5000`
Health: `http://localhost:5000/health`

`pricing_pipeline: configured` means pricing API credentials are present. It
does not test account approval, quota, Redis, or a worker heartbeat.

## Provider configuration

Review `DATA_SOURCES.md` and obtain the required production/data-use approval
before setting credentials.

```dotenv
PIPELINE_ENABLED=true
EBAY_CLIENT_ID=...
EBAY_CLIENT_SECRET=...
EBAY_MARKETPLACE_ID=EBAY_US
TARGET_CURRENCY=USD
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

The marketplace and target currency must match. Listings with a different
currency are discarded. Asking prices are not completed-sale prices.

## Adaptive refresh behavior

Each submitted brand/model becomes one deduplicated market query. Celery Beat
checks for due queries every 15 minutes. After collection, the scheduler
compares recent batch medians:

- high median-price movement shortens the interval;
- stable prices remain near the category baseline;
- category-specific minimum and maximum bounds prevent aggressive polling or
  stale data.

Defaults:

| Category | Minimum | Baseline | Maximum |
| --- | ---: | ---: | ---: |
| Vehicles | 4 hours | 12 hours | 24 hours |
| Mobiles | 1 hour | 6 hours | 24 hours |
| Laptops | 3 hours | 12 hours | 48 hours |

Tune the `*_REFRESH_MINUTES` variables only within the provider's quota and
contract. Collection is demand-driven: models users have not submitted are not
polled.

## Model lifecycle

The worker retains observations for `OBSERVATION_RETENTION_DAYS` (seven by
default). Once at least `MODEL_MINIMUM_ROWS` valid same-currency observations
exist, training creates a new immutable model version in MariaDB and atomically
marks it active. Predictions record source, confidence, timestamp, and model
version.

Before enough data exists, an exact brand/model median is used. If neither a
model nor comparables exist, the estimate remains pending. The old bundled
vehicle dataset is used only when `PIPELINE_ENABLED=false`; phones and laptops
correctly remain pending in that mode.

## Split hosting

The full pipeline needs persistent worker processes and Redis. Deploy the same
image in three roles:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
celery -A celery_worker.celery worker --loglevel=INFO --concurrency=2
celery -A celery_worker.celery beat --loglevel=INFO
```

All roles must share MariaDB, Redis, provider settings, and target currency.
Run exactly one Beat instance.

The included Render blueprint and Vercel configuration deploy only the
browserless web/fallback mode (`PIPELINE_ENABLED=false`). Vercel functions
cannot host a persistent Celery worker. To use either for the web tier, run the
worker, Beat, and Redis elsewhere and explicitly enable the pipeline in the web
environment.

## Database and operational checks

For a separately provisioned database:

```bash
mysql -h <host> -u <user> -p <db> < capstone.sql
```

Basic checks:

```bash
curl -fsS http://localhost:5000/health
docker compose exec worker celery -A celery_worker.celery inspect ping
docker compose logs worker scheduler
```

Monitor failed `pipeline_runs`, provider HTTP errors, queue depth, observation
age, active model age, model holdout error, and pending valuation count. Never
log API secrets or OAuth tokens.

## Serverless fallback

Vercel uses `api/index.py`, `PIPELINE_ENABLED=false`, and `DATA_DIR=/tmp`.
Supply external MySQL credentials and a strong `SECRET_KEY`. The Flask app can
serve the bundled vehicle estimate, but this mode does not collect live data or
price electronics.
