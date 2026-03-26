"""
Inference Module — Step 2.2
============================
Loads trained models from disk and provides real-time
prediction with confidence scoring.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import joblib

from src.config import MODELS_DIR
from src.ai_engine.emission_model import EmissionEstimator
from src.ai_engine.anomaly_detector import AnomalyDetector

logger = logging.getLogger("ai_engine.inference")


class InferenceEngine:
    """
    Loads pre-trained models and runs real-time inference.

    Usage:
        engine = InferenceEngine()
        engine.load_models()
        result = engine.infer(reading_dict)
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self._dir = models_dir or MODELS_DIR
        self._estimator: Optional[EmissionEstimator] = None
        self._detector: Optional[AnomalyDetector] = None

    @property
    def is_ready(self) -> bool:
        return self._estimator is not None and self._detector is not None

    def load_models(self) -> "InferenceEngine":
        """Load serialised models from disk."""
        est_path = self._dir / "emission_estimator.pkl"
        det_path = self._dir / "anomaly_detector.pkl"

        if est_path.exists():
            self._estimator = joblib.load(str(est_path))
            logger.info("Loaded emission estimator from %s", est_path)
        else:
            raise FileNotFoundError(f"Emission model not found: {est_path}")

        if det_path.exists():
            self._detector = joblib.load(str(det_path))
            logger.info("Loaded anomaly detector from %s", det_path)
        else:
            raise FileNotFoundError(f"Anomaly model not found: {det_path}")

        return self

    def infer(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run full inference: emission estimation + anomaly detection.

        Returns combined result dict.
        """
        assert self.is_ready, "Models not loaded — call load_models() first"

        emission = self._estimator.predict(reading)
        anomaly = self._detector.detect(reading)

        return {
            "facility_id": reading.get("facility_id"),
            "timestamp_utc": reading.get("timestamp_utc"),
            "co2e_emission": emission["co2e_emission"],
            "confidence_score": emission["confidence_score"],
            "model_version": emission["model_version"],
            "anomaly_flag": anomaly["anomaly_flag"],
            "anomaly_type": anomaly["anomaly_type"],
            "severity_score": anomaly["severity_score"],
        }

    def set_models(self, estimator: EmissionEstimator, detector: AnomalyDetector):
        """Inject models directly (for testing without disk I/O)."""
        self._estimator = estimator
        self._detector = detector
