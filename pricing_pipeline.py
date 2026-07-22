"""Collection, training, and inference orchestration for PriceScout."""

from __future__ import annotations

import os
import statistics
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

import mysql.connector

from market_model import predict_price, train_model
from marketplace_providers import ProviderError, pricing_providers

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "capstone"),
}
TARGET_CURRENCY = os.getenv("TARGET_CURRENCY", "USD").upper()
MINIMUM_MODEL_ROWS = int(os.getenv("MODEL_MINIMUM_ROWS", "25"))
OBSERVATION_RETENTION_DAYS = int(os.getenv("OBSERVATION_RETENTION_DAYS", "7"))

CADENCE_MINUTES = {
    "vehicle": (
        int(os.getenv("VEHICLE_MIN_REFRESH_MINUTES", "240")),
        int(os.getenv("VEHICLE_BASE_REFRESH_MINUTES", "720")),
        int(os.getenv("VEHICLE_MAX_REFRESH_MINUTES", "1440")),
    ),
    "mobiles": (
        int(os.getenv("MOBILE_MIN_REFRESH_MINUTES", "60")),
        int(os.getenv("MOBILE_BASE_REFRESH_MINUTES", "360")),
        int(os.getenv("MOBILE_MAX_REFRESH_MINUTES", "1440")),
    ),
    "laptops": (
        int(os.getenv("LAPTOP_MIN_REFRESH_MINUTES", "180")),
        int(os.getenv("LAPTOP_BASE_REFRESH_MINUTES", "720")),
        int(os.getenv("LAPTOP_MAX_REFRESH_MINUTES", "2880")),
    ),
}


@contextmanager
def database() -> Iterator[mysql.connector.MySQLConnection]:
    connection = mysql.connector.connect(**DB_CONFIG)
    try:
        yield connection
    finally:
        connection.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS market_queries (
      id BIGINT NOT NULL AUTO_INCREMENT,
      category VARCHAR(32) NOT NULL,
      brand VARCHAR(255) NOT NULL,
      model VARCHAR(255) NOT NULL,
      query_text VARCHAR(512) NOT NULL,
      active BOOLEAN NOT NULL DEFAULT TRUE,
      refresh_minutes INT NOT NULL,
      volatility DOUBLE NOT NULL DEFAULT 0,
      last_collected_at DATETIME NULL,
      next_collection_at DATETIME NOT NULL,
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL,
      PRIMARY KEY (id),
      UNIQUE KEY market_query_item (category, brand, model)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
      id CHAR(36) NOT NULL,
      job_type VARCHAR(32) NOT NULL,
      status VARCHAR(16) NOT NULL,
      details TEXT NULL,
      started_at DATETIME NOT NULL,
      finished_at DATETIME NULL,
      PRIMARY KEY (id),
      KEY pipeline_run_started (started_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS market_observations (
      id BIGINT NOT NULL AUTO_INCREMENT,
      query_id BIGINT NOT NULL,
      collection_id CHAR(36) NOT NULL,
      provider VARCHAR(64) NOT NULL,
      external_id VARCHAR(255) NOT NULL,
      title TEXT NOT NULL,
      item_condition VARCHAR(128) NULL,
      price DECIMAL(14, 2) NOT NULL,
      currency CHAR(3) NOT NULL,
      listing_url TEXT NULL,
      observed_at DATETIME NOT NULL,
      expires_at DATETIME NOT NULL,
      PRIMARY KEY (id),
      KEY observations_query_time (query_id, observed_at),
      KEY observations_expiry (expires_at),
      CONSTRAINT observations_query_fk FOREIGN KEY (query_id)
        REFERENCES market_queries (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS model_versions (
      id BIGINT NOT NULL AUTO_INCREMENT,
      version CHAR(36) NOT NULL,
      target_currency CHAR(3) NOT NULL,
      row_count INT NOT NULL,
      median_absolute_percentage_error DOUBLE NULL,
      artifact LONGBLOB NOT NULL,
      active BOOLEAN NOT NULL DEFAULT FALSE,
      trained_at DATETIME NOT NULL,
      PRIMARY KEY (id),
      UNIQUE KEY model_version (version),
      KEY active_model (active, trained_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

PRICE_COLUMNS = {
    "pricing_status": "VARCHAR(16) NOT NULL DEFAULT 'pending'",
    "price_source": "VARCHAR(64) NULL",
    "price_confidence": "DOUBLE NULL",
    "priced_at": "DATETIME NULL",
    "model_version": "CHAR(36) NULL",
}


def ensure_pipeline_schema() -> None:
    """Create additive pipeline tables/columns for old and new deployments."""
    with database() as connection:
        cursor = connection.cursor()
        for statement in CREATE_STATEMENTS:
            cursor.execute(statement)
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'price'",
            (DB_CONFIG["database"],),
        )
        existing = {row[0] for row in cursor.fetchall()}
        for name, definition in PRICE_COLUMNS.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE price ADD COLUMN {name} {definition}")
        connection.commit()


def register_query(category: str, brand: str, model: str) -> int:
    if category not in CADENCE_MINUTES:
        raise ValueError(f"Unsupported category: {category}")
    brand = brand.strip()
    model = model.strip()
    if not brand or not model:
        raise ValueError("Brand and model are required")
    now = _utcnow()
    base_refresh = CADENCE_MINUTES[category][1]
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO market_queries
              (category, brand, model, query_text, refresh_minutes,
               next_collection_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              active = TRUE, query_text = VALUES(query_text), updated_at = VALUES(updated_at),
              id = LAST_INSERT_ID(id)
            """,
            (category, brand, model, f"{brand} {model}", base_refresh, now, now, now),
        )
        query_id = cursor.lastrowid
        connection.commit()
        return int(query_id)


def _volatility_and_interval(connection, query_id: int, category: str) -> tuple[float, int]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT collection_id, price
        FROM market_observations
        WHERE query_id = %s AND currency = %s
        ORDER BY observed_at DESC
        LIMIT 400
        """,
        (query_id, TARGET_CURRENCY),
    )
    batches: dict[str, list[float]] = {}
    for collection_id, price in cursor.fetchall():
        batches.setdefault(collection_id, []).append(float(price))
    medians = [statistics.median(values) for values in list(batches.values())[:6] if values]
    changes = [
        abs(current - previous) / previous
        for current, previous in zip(medians, medians[1:])
        if previous > 0
    ]
    volatility = statistics.median(changes) if changes else 0.0
    minimum, base, maximum = CADENCE_MINUTES[category]
    interval = round(base / (1 + 8 * volatility))
    return volatility, max(minimum, min(maximum, interval))


def collect_query(query_id: int) -> int:
    ensure_pipeline_schema()
    run_id = str(uuid.uuid4())
    now = _utcnow()
    with database() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM market_queries WHERE id = %s AND active = TRUE", (query_id,))
        query = cursor.fetchone()
        if not query:
            return 0
        cursor.execute(
            "INSERT INTO pipeline_runs (id, job_type, status, started_at) VALUES (%s, 'collect', 'running', %s)",
            (run_id, now),
        )
        connection.commit()

    providers = pricing_providers()
    errors = []
    observations = []
    for provider in providers:
        try:
            observations.extend(provider.search(query["query_text"]))
        except ProviderError as exc:
            errors.append(f"{provider.name}: {exc}")

    with database() as connection:
        cursor = connection.cursor()
        expires_at = now + timedelta(days=OBSERVATION_RETENTION_DAYS)
        for observation in observations:
            record = observation.to_record()
            cursor.execute(
                """
                INSERT INTO market_observations
                  (query_id, collection_id, provider, external_id, title,
                   item_condition, price, currency, listing_url, observed_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    query_id,
                    run_id,
                    record["provider"],
                    record["external_id"],
                    record["title"],
                    record["condition"],
                    record["price"],
                    record["currency"],
                    record["url"],
                    record["observed_at"],
                    expires_at,
                ),
            )
        volatility, refresh_minutes = _volatility_and_interval(connection, query_id, query["category"])
        cursor.execute(
            """
            UPDATE market_queries
            SET volatility = %s, refresh_minutes = %s, last_collected_at = %s,
                next_collection_at = %s, updated_at = %s
            WHERE id = %s
            """,
            (
                volatility,
                refresh_minutes,
                now,
                now + timedelta(minutes=refresh_minutes),
                now,
                query_id,
            ),
        )
        status = "succeeded" if observations else "failed"
        details = f"{len(observations)} observations"
        if not providers:
            details = "No pricing provider is configured"
        elif errors:
            details += "; " + "; ".join(errors)
        cursor.execute(
            "UPDATE pipeline_runs SET status = %s, details = %s, finished_at = %s WHERE id = %s",
            (status, details[:65000], _utcnow(), run_id),
        )
        connection.commit()
    return len(observations)


def collect_due_queries(limit: int = 20) -> int:
    ensure_pipeline_schema()
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id FROM market_queries
            WHERE active = TRUE AND next_collection_at <= %s
            ORDER BY next_collection_at ASC LIMIT %s
            """,
            (_utcnow(), limit),
        )
        query_ids = [row[0] for row in cursor.fetchall()]
    return sum(collect_query(query_id) for query_id in query_ids)


def train_latest_model() -> str | None:
    ensure_pipeline_schema()
    with database() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT q.category, q.brand, q.model,
                   COALESCE(o.item_condition, 'used') AS `condition`, o.price
            FROM market_observations o
            JOIN market_queries q ON q.id = o.query_id
            WHERE o.currency = %s AND o.expires_at > %s
            ORDER BY o.observed_at ASC
            """,
            (TARGET_CURRENCY, _utcnow()),
        )
        rows = cursor.fetchall()
    if len(rows) < MINIMUM_MODEL_ROWS:
        return None
    result = train_model(rows, minimum_rows=MINIMUM_MODEL_ROWS)
    version = str(uuid.uuid4())
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE model_versions SET active = FALSE WHERE active = TRUE")
        cursor.execute(
            """
            INSERT INTO model_versions
              (version, target_currency, row_count, median_absolute_percentage_error,
               artifact, active, trained_at)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s)
            """,
            (
                version,
                TARGET_CURRENCY,
                result.row_count,
                result.median_absolute_percentage_error,
                result.artifact,
                result.trained_at.replace(tzinfo=None),
            ),
        )
        connection.commit()
    return version


def estimate_item(category: str, brand: str, model: str) -> dict | None:
    query_id = register_query(category, brand, model)
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT price FROM market_observations
            WHERE query_id = %s AND currency = %s AND expires_at > %s
            ORDER BY observed_at DESC LIMIT 100
            """,
            (query_id, TARGET_CURRENCY, _utcnow()),
        )
        comparable_prices = [float(row[0]) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT version, artifact, median_absolute_percentage_error
            FROM model_versions
            WHERE active = TRUE AND target_currency = %s
            ORDER BY trained_at DESC LIMIT 1
            """,
            (TARGET_CURRENCY,),
        )
        active_model = cursor.fetchone()

    if active_model:
        estimate = predict_price(
            bytes(active_model[1]),
            {"category": category, "brand": brand, "model": model, "condition": "used"},
        )
        metric = active_model[2]
        confidence = max(0.1, min(0.95, 1.0 - float(metric))) if metric is not None else 0.5
        return {
            "price": estimate,
            "source": "market_model",
            "confidence": confidence,
            "model_version": active_model[0],
            "comparables": len(comparable_prices),
        }
    if comparable_prices:
        return {
            "price": statistics.median(comparable_prices),
            "source": "comparable_median",
            "confidence": min(0.8, 0.25 + len(comparable_prices) / 100),
            "model_version": None,
            "comparables": len(comparable_prices),
        }
    return None


def clean_expired_observations() -> int:
    ensure_pipeline_schema()
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM market_observations WHERE expires_at <= %s", (_utcnow(),))
        removed = cursor.rowcount
        connection.commit()
        return removed
