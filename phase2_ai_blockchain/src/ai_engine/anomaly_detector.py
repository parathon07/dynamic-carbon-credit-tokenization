"""
Anomaly Detection — Step 2.3
==============================
Detects abnormal emission spikes, sensor malfunctions, and
pattern anomalies using Isolation Forest and statistical thresholds.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from src.config import (
    ANOMALY_ZSCORE_THRESHOLD,
    ISOLATION_FOREST_CONTAMINATION,
    SENSOR_FIELDS,
)

logger = logging.getLogger("ai_engine.anomaly_detector")


class AnomalyDetector:
    """
    Detects anomalies in sensor readings using two methods:

      1. Isolation Forest (multivariate — catches complex patterns)
      2. Z-score thresholding (per-sensor — catches individual spikes)

    Output per reading:
      {
        "anomaly_flag": bool,
        "anomaly_type": "normal" | "emission_spike" | "sensor_malfunction" | "pattern_anomaly",
        "severity_score": 0.0–1.0,
        "details": {field: z_score, ...}
      }
    """

    def __init__(self, contamination: float = ISOLATION_FOREST_CONTAMINATION):
        self._iforest = IsolationForest(
            contamination=contamination,
            random_state=42, n_jobs=-1,
        )
        self._mean: Optional[np.ndarray] = None
        self._std: Optional[np.ndarray] = None
        self._fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def fit(self, X: np.ndarray) -> "AnomalyDetector":
        """
        Fit the Isolation Forest and compute per-feature statistics.

        Args:
            X: Feature matrix (n_samples, n_features) — sensor values only.
        """
        sensor_X = X[:, :len(SENSOR_FIELDS)]
        self._iforest.fit(sensor_X)
        self._mean = np.mean(sensor_X, axis=0)
        self._std = np.std(sensor_X, axis=0) + 1e-8
        self._fitted = True
        logger.info("AnomalyDetector fitted on %d samples", len(X))
        return self

    def detect(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect anomalies in a single reading.

        Returns anomaly result dict.
        """
        assert self._fitted, "Call fit() before detect()"

        values = np.array([reading[f] for f in SENSOR_FIELDS], dtype=float)

        # Z-score per sensor
        z_scores = np.abs((values - self._mean) / self._std)
        z_dict = {f: round(float(z), 3) for f, z in zip(SENSOR_FIELDS, z_scores)}

        # Isolation Forest score
        iforest_pred = self._iforest.predict(values.reshape(1, -1))[0]
        iforest_score = -self._iforest.score_samples(values.reshape(1, -1))[0]

        # Classify anomaly
        high_z_fields = [f for f, z in z_dict.items() if z > ANOMALY_ZSCORE_THRESHOLD]
        is_iforest_anomaly = iforest_pred == -1

        # Classification logic
        if not high_z_fields and not is_iforest_anomaly:
            return {
                "anomaly_flag": False,
                "anomaly_type": "normal",
                "severity_score": 0.0,
                "details": z_dict,
            }

        # Determine type
        if len(high_z_fields) >= 3:
            anomaly_type = "sensor_malfunction"
        elif any(f in high_z_fields for f in ("co2_ppm", "ch4_ppm", "nox_ppb")):
            anomaly_type = "emission_spike"
        elif is_iforest_anomaly:
            anomaly_type = "pattern_anomaly"
        else:
            anomaly_type = "emission_spike"

        severity = min(1.0, max(float(np.max(z_scores)) / 10.0, iforest_score / 2.0))

        return {
            "anomaly_flag": True,
            "anomaly_type": anomaly_type,
            "severity_score": round(severity, 4),
            "details": z_dict,
        }

    def detect_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in a batch."""
        return [self.detect(r) for r in readings]
