"""
AI Emission Estimation Model — Step 2.2
========================================
Converts multi-sensor readings into CO₂-equivalent (CO₂e)
emission estimates using Random Forest and Linear Regression.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score

from src.config import (
    GWP_CO2, GWP_CH4, GWP_N2O,
    EMISSION_CONVERSION, SENSOR_FIELDS,
)

logger = logging.getLogger("ai_engine.emission_model")

FEATURE_NAMES = SENSOR_FIELDS + ["hour_of_day", "day_of_week"]


def compute_co2e_ground_truth(reading: Dict[str, Any]) -> float:
    """
    Compute ground-truth CO₂e from raw sensor values using IPCC GWP-100.

    Formula:
        CO₂e = CO₂_kg × 1.0 + CH₄_kg × 28.0 + NOₓ_kg × 265.0

    Where:
        CO₂_kg = co2_ppm × 0.044
        CH₄_kg = ch4_ppm × 0.016
        NOₓ_kg = nox_ppb × 0.000046
    """
    co2_kg = reading["co2_ppm"] * EMISSION_CONVERSION["co2_ppm_to_kg"]
    ch4_kg = reading["ch4_ppm"] * EMISSION_CONVERSION["ch4_ppm_to_kg"]
    nox_kg = reading["nox_ppb"] * EMISSION_CONVERSION["nox_ppb_to_kg"]

    co2e = co2_kg * GWP_CO2 + ch4_kg * GWP_CH4 + nox_kg * GWP_N2O
    return round(co2e, 6)


def extract_features(reading: Dict[str, Any]) -> np.ndarray:
    """Extract feature vector from a reading dict."""
    from datetime import datetime
    ts = datetime.fromisoformat(reading["timestamp_utc"])
    features = [reading[f] for f in SENSOR_FIELDS]
    features.append(ts.hour)               # hour_of_day
    features.append(ts.weekday())           # day_of_week (0=Mon)
    return np.array(features, dtype=float)


class EmissionEstimator:
    """
    Predicts CO₂e emission from multi-sensor features.

    Models:
      - Random Forest (primary, higher accuracy)
      - Linear Regression (baseline, interpretable)
    """

    def __init__(self):
        self._rf = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1,
        )
        self._lr = LinearRegression()
        self._trained = False
        self._model_version = "v1.0"

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Train both models. Returns cross-validated R² scores.

        Args:
            X: Feature matrix (n_samples, 7)
            y: CO₂e ground truth (n_samples,)
        """
        self._rf.fit(X, y)
        self._lr.fit(X, y)
        self._trained = True

        rf_scores = cross_val_score(self._rf, X, y, cv=5, scoring="r2")
        lr_scores = cross_val_score(self._lr, X, y, cv=5, scoring="r2")

        metrics = {
            "rf_r2_mean": round(float(np.mean(rf_scores)), 4),
            "rf_r2_std":  round(float(np.std(rf_scores)), 4),
            "lr_r2_mean": round(float(np.mean(lr_scores)), 4),
            "lr_r2_std":  round(float(np.std(lr_scores)), 4),
        }
        logger.info("Trained emission models: %s", metrics)
        return metrics

    def predict(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict CO₂e for a single reading.

        Returns:
            {"co2e_emission": float, "confidence_score": float,
             "model_version": str, "lr_prediction": float}
        """
        assert self._trained, "Model not trained — call train() first"
        features = extract_features(reading).reshape(1, -1)

        # Random Forest prediction + confidence from tree variance
        tree_preds = np.array([t.predict(features)[0] for t in self._rf.estimators_])
        rf_pred = float(np.mean(tree_preds))
        rf_std = float(np.std(tree_preds))
        confidence = max(0.0, min(1.0, 1.0 - rf_std / (abs(rf_pred) + 1e-8)))

        # Linear regression prediction
        lr_pred = float(self._lr.predict(features)[0])

        return {
            "co2e_emission": round(rf_pred, 6),
            "confidence_score": round(confidence, 4),
            "model_version": self._model_version,
            "lr_prediction": round(lr_pred, 6),
        }

    def predict_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict CO₂e for a batch of readings."""
        return [self.predict(r) for r in readings]

    def feature_importance(self) -> Dict[str, float]:
        """Return Random Forest feature importances."""
        assert self._trained
        return {name: round(float(imp), 4)
                for name, imp in zip(FEATURE_NAMES, self._rf.feature_importances_)}
