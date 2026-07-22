"""Celery worker and scheduler for collection, training, and pricing."""

import os
from datetime import datetime, timezone

from celery import Celery

from pricing_pipeline import (
    clean_expired_observations,
    collect_due_queries,
    collect_query,
    database,
    ensure_pipeline_schema,
    estimate_item,
    register_query,
    train_latest_model,
)


broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)
celery = Celery("pricescout", broker=broker_url, backend=result_backend)
celery.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    beat_schedule={
        "collect-due-market-queries": {
            "task": "pipeline.collect_due",
            "schedule": 15 * 60,
        },
        "train-market-model": {
            "task": "pipeline.train",
            "schedule": 6 * 60 * 60,
        },
        "expire-old-market-observations": {
            "task": "pipeline.cleanup",
            "schedule": 24 * 60 * 60,
        },
    },
)


@celery.task(name="pipeline.collect_due", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def collect_due():
    return collect_due_queries()


@celery.task(name="pipeline.train", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def train():
    return train_latest_model()


@celery.task(name="pipeline.cleanup", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def cleanup():
    return clean_expired_observations()


@celery.task(name="pipeline.price_listing", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def price_listing(email: str, post_type: str, post_id: int):
    """Collect fresh comparables when needed and persist one listing estimate."""
    ensure_pipeline_schema()
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT brand, model FROM price
            WHERE email = %s AND post_type = %s AND post_id = %s
            LIMIT 1
            """,
            (email, post_type, post_id),
        )
        row = cursor.fetchone()
        if row is None:
            return {"status": "missing"}
        brand, model = row
        cursor.execute(
            """
            UPDATE price SET pricing_status = 'collecting'
            WHERE email = %s AND post_type = %s AND post_id = %s
            """,
            (email, post_type, post_id),
        )
        connection.commit()

    query_id = register_query(post_type, brand, model)
    estimate = estimate_item(post_type, brand, model)
    if estimate is None:
        collect_query(query_id)
        estimate = estimate_item(post_type, brand, model)

    with database() as connection:
        cursor = connection.cursor()
        if estimate is None:
            cursor.execute(
                """
                UPDATE price SET pricing_status = 'pending'
                WHERE email = %s AND post_type = %s AND post_id = %s
                """,
                (email, post_type, post_id),
            )
            status = "pending"
        else:
            cursor.execute(
                """
                UPDATE price
                SET price = %s, pricing_status = 'ready', price_source = %s,
                    price_confidence = %s, priced_at = %s, model_version = %s
                WHERE email = %s AND post_type = %s AND post_id = %s
                """,
                (
                    estimate["price"],
                    estimate["source"],
                    estimate["confidence"],
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    estimate["model_version"],
                    email,
                    post_type,
                    post_id,
                ),
            )
            status = "ready"
        connection.commit()
    return {"status": status, "estimate": estimate}


def enqueue_price(email: str, post_type: str, post_id: int) -> str:
    result = price_listing.delay(email, post_type, post_id)
    return result.id