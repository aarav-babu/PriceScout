"""Persisted cross-category model for authorized marketplace observations."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


FEATURES = ["category", "brand", "model", "condition"]


@dataclass(frozen=True)
class TrainingResult:
    artifact: bytes
    row_count: int
    median_absolute_percentage_error: float | None
    trained_at: datetime


def _frame(rows: Iterable[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    required = set(FEATURES + ["price"])
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Training rows are missing columns: {', '.join(sorted(missing))}")
    for column in FEATURES:
        frame[column] = frame[column].fillna("unknown").astype(str).str.strip().str.lower()
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["price"])
    frame = frame[frame["price"] > 0]
    return frame


def train_model(rows: Iterable[dict], minimum_rows: int = 25) -> TrainingResult:
    frame = _frame(rows)
    if len(frame) < minimum_rows:
        raise ValueError(f"Need at least {minimum_rows} observations; found {len(frame)}")

    # Marketplace feeds contain obvious placeholder/outlier prices. Apply a
    # broad global fence while retaining legitimate premium models.
    lower, upper = frame["price"].quantile([0.01, 0.99])
    filtered = frame[frame["price"].between(lower, upper)]
    if len(filtered) >= minimum_rows:
        frame = filtered

    pipeline = Pipeline(
        steps=[
            (
                "features",
                ColumnTransformer(
                    [
                        (
                            "categorical",
                            OneHotEncoder(handle_unknown="ignore"),
                            FEATURES,
                        )
                    ],
                    remainder="drop",
                ),
            ),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=160,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    # Keep the newest fifth as a lightweight temporal holdout when enough data
    # exists. The final artifact is then fitted on all accepted observations.
    split = max(int(len(frame) * 0.8), 1)
    metric = None
    if split < len(frame) and split >= 10:
        evaluation_model = pipeline.fit(frame.iloc[:split][FEATURES], frame.iloc[:split]["price"])
        predicted = evaluation_model.predict(frame.iloc[split:][FEATURES])
        actual = frame.iloc[split:]["price"].to_numpy()
        denominator = np.maximum(np.abs(actual), 1.0)
        metric = float(np.median(np.abs(actual - predicted) / denominator))
        if not math.isfinite(metric):
            metric = None

    pipeline.fit(frame[FEATURES], frame["price"])
    buffer = io.BytesIO()
    joblib.dump(pipeline, buffer)
    return TrainingResult(
        artifact=buffer.getvalue(),
        row_count=len(frame),
        median_absolute_percentage_error=metric,
        trained_at=datetime.now(timezone.utc),
    )


def predict_price(artifact: bytes, item: dict) -> float:
    pipeline = joblib.load(io.BytesIO(artifact))
    row = {
        column: str(item.get(column, "unknown")).strip().lower()
        for column in FEATURES
    }
    prediction = float(pipeline.predict(pd.DataFrame([row], columns=FEATURES))[0])
    if not math.isfinite(prediction) or prediction <= 0:
        raise ValueError("Model produced an invalid price")
    return prediction
