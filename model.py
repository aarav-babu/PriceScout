"""Bundled vehicle-model fallback.

The hosted market model lives in ``market_model.py``. This module keeps the
browserless demo functional and caches its fitted estimator per web process so
request handling does not retrain for every valuation.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


CATEGORICAL_FEATURES = ["Model", "Fuel_Type", "Transmission", "Owner_Type"]
NUMERIC_FEATURES = [
    "Year",
    "Kilometers_Driven",
    "Engine",
    "Power",
    "Seats",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
_MODEL_CACHE: dict[tuple, Pipeline] = {}


def _normalize(value) -> str:
    return str(value or "unknown").strip().lower()


def _training_frame(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    if "Name" in data:
        extracted = data["Name"].astype(str).str.extract(r"^\s*\d{4}\s+\S+\s+(\S+)")
        data["Model"] = extracted[0].fillna("unknown")
    for feature in CATEGORICAL_FEATURES:
        if feature not in data:
            data[feature] = "unknown"
        data[feature] = data[feature].map(_normalize)
    for feature in NUMERIC_FEATURES + ["Price"]:
        if feature not in data:
            data[feature] = None
        data[feature] = pd.to_numeric(data[feature], errors="coerce")
    return data.dropna(subset=["Price"])


def _cache_key(frame: pd.DataFrame) -> tuple:
    return (
        len(frame),
        tuple(frame.columns),
        float(pd.to_numeric(frame.get("Price"), errors="coerce").fillna(0).sum()),
    )


def train(frame: pd.DataFrame) -> Pipeline:
    data = _training_frame(frame)
    if data.empty:
        raise ValueError("Vehicle training dataset contains no valid prices")
    estimator = Pipeline(
        [
            (
                "features",
                ColumnTransformer(
                    [
                        (
                            "categorical",
                            Pipeline(
                                [
                                    ("missing", SimpleImputer(strategy="most_frequent")),
                                    ("encode", OneHotEncoder(handle_unknown="ignore")),
                                ]
                            ),
                            CATEGORICAL_FEATURES,
                        ),
                        (
                            "numeric",
                            SimpleImputer(strategy="median"),
                            NUMERIC_FEATURES,
                        ),
                    ]
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
    return estimator.fit(data[FEATURES], data["Price"])


def model_call(train_df: pd.DataFrame, user_input: dict) -> float:
    key = _cache_key(train_df)
    estimator = _MODEL_CACHE.get(key)
    if estimator is None:
        estimator = train(train_df)
        _MODEL_CACHE.clear()
        _MODEL_CACHE[key] = estimator

    row = {
        "Model": _normalize(user_input.get("Model")),
        "Fuel_Type": _normalize(user_input.get("Fuel_Type")),
        "Transmission": _normalize(user_input.get("Transmission")),
        "Owner_Type": _normalize(user_input.get("Owner_Type")),
    }
    for feature in NUMERIC_FEATURES:
        row[feature] = pd.to_numeric(user_input.get(feature), errors="coerce")
    prediction = float(estimator.predict(pd.DataFrame([row], columns=FEATURES))[0])
    if prediction <= 0:
        raise ValueError("Vehicle model produced an invalid price")
    return prediction
