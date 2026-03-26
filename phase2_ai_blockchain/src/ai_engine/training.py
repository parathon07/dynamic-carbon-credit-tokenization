"""
AI Training Workflow — Step 2.2
================================
Generates synthetic training data from Phase 1 simulators,
trains emission models, and persists them to disk.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np

from src.config import MODELS_DIR, FACILITY_TYPES, SENSOR_BASELINES, SENSOR_FIELDS
from src.ai_engine.emission_model import (
    EmissionEstimator, compute_co2e_ground_truth, extract_features,
)
from src.ai_engine.anomaly_detector import AnomalyDetector

logger = logging.getLogger("ai_engine.training")


def generate_synthetic_data(
    n_facilities: int = 50,
    readings_per_facility: int = 200,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], np.ndarray, np.ndarray]:
    """
    Generate synthetic training data mimicking Phase 1 simulators.

    Returns:
        (readings, X_features, y_co2e)
    """
    rng = np.random.RandomState(seed)
    readings = []
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for fac_idx in range(n_facilities):
        facility_id = f"FAC_{fac_idx + 1:03d}"
        facility_type = FACILITY_TYPES[fac_idx % len(FACILITY_TYPES)]
        baselines = SENSOR_BASELINES[facility_type]

        t = base_time
        for _ in range(readings_per_facility):
            # Generate correlated sensor values
            hour = t.hour
            day = t.weekday()
            diurnal = 0.8 + 0.4 * np.sin(np.pi * hour / 12)  # peak at noon
            weekly = 1.0 if day < 5 else 0.7  # weekday vs weekend

            reading = {
                "facility_id": facility_id,
                "facility_type": facility_type,
                "timestamp_utc": t.isoformat(),
            }
            for field in SENSOR_FIELDS:
                lo, hi = baselines[field]
                base = (lo + hi) / 2
                noise = rng.normal(0, (hi - lo) * 0.1)
                reading[field] = round(base * diurnal * weekly + noise, 4)

            readings.append(reading)
            t += timedelta(seconds=15)

    # Extract features and labels
    X = np.array([extract_features(r) for r in readings])
    y = np.array([compute_co2e_ground_truth(r) for r in readings])

    logger.info(
        "Generated %d synthetic readings across %d facilities",
        len(readings), n_facilities,
    )
    return readings, X, y


def train_and_save(
    n_facilities: int = 50,
    readings_per_facility: int = 200,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Full training pipeline: generate data → train models → save to disk.

    Returns training metrics.
    """
    readings, X, y = generate_synthetic_data(n_facilities, readings_per_facility, seed)

    # Train emission estimator
    estimator = EmissionEstimator()
    metrics = estimator.train(X, y)

    # Train anomaly detector
    detector = AnomalyDetector()
    detector.fit(X)

    # Save models
    joblib.dump(estimator, str(MODELS_DIR / "emission_estimator.pkl"))
    joblib.dump(detector, str(MODELS_DIR / "anomaly_detector.pkl"))

    metrics["samples"] = len(readings)
    metrics["facilities"] = n_facilities
    metrics["feature_importance"] = estimator.feature_importance()

    logger.info("Models saved to %s", MODELS_DIR)
    return metrics
