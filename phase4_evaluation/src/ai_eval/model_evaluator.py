"""
AI Model Performance Evaluator — Step 4.2
============================================
Evaluates emission estimation (RF) and anomaly detection (IF) models
using standard ML metrics for research publication.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    precision_score, recall_score, f1_score, confusion_matrix,
    roc_auc_score, classification_report,
)
from sklearn.model_selection import cross_val_score, train_test_split

from src.config import (
    TRAIN_TEST_SPLIT, CV_FOLDS, RANDOM_STATE,
    ANOMALY_INJECTION_RATE, ANOMALY_TYPES,
    MIN_R2_SCORE, MAX_MAE_THRESHOLD, MIN_F1_SCORE,
)

logger = logging.getLogger("eval.model_evaluator")


class ModelEvaluator:
    """
    Evaluates Phase 2 AI models with publication-quality metrics.

    Emission Estimator: MAE, RMSE, R², MAPE, residual analysis
    Anomaly Detector:   Precision, Recall, F1, AUC-ROC, confusion matrix
    """

    def __init__(self):
        self._emission_results: Dict[str, Any] = {}
        self._anomaly_results: Dict[str, Any] = {}

    def evaluate_emission_model(self, estimator, X: np.ndarray,
                                 y: np.ndarray,
                                 facility_types: Optional[List[str]] = None
                                 ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of the emission estimation model.

        Args:
            estimator: Trained EmissionEstimator instance.
            X: Feature matrix (n_samples, n_features).
            y: Ground truth CO₂e values.
            facility_types: Per-sample facility type labels.
        """
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TRAIN_TEST_SPLIT, random_state=RANDOM_STATE,
        )

        # Cross-validation on training set
        cv_r2 = cross_val_score(
            estimator._rf, X_train, y_train, cv=CV_FOLDS, scoring="r2",
        )
        cv_mae = -cross_val_score(
            estimator._rf, X_train, y_train, cv=CV_FOLDS, scoring="neg_mean_absolute_error",
        )

        # Test set predictions
        y_pred = estimator._rf.predict(X_test)
        y_pred_lr = estimator._lr.predict(X_test)

        # Core metrics — Random Forest
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        mape = float(np.mean(np.abs((y_test - y_pred) / (y_test + 1e-10)))) * 100

        # Residual analysis
        residuals = y_test - y_pred
        res_mean = float(np.mean(residuals))
        res_std = float(np.std(residuals))

        # Linear Regression metrics
        mae_lr = float(mean_absolute_error(y_test, y_pred_lr))
        rmse_lr = float(np.sqrt(mean_squared_error(y_test, y_pred_lr)))
        r2_lr = float(r2_score(y_test, y_pred_lr))

        # Per-facility-type breakdown
        per_type = {}
        if facility_types is not None:
            ft_test = np.array(facility_types)[
                train_test_split(
                    range(len(y)), test_size=TRAIN_TEST_SPLIT, random_state=RANDOM_STATE,
                )[1]
            ]
            for ft in set(ft_test):
                mask = ft_test == ft
                if mask.sum() > 5:
                    per_type[ft] = {
                        "mae": round(float(mean_absolute_error(y_test[mask], y_pred[mask])), 6),
                        "rmse": round(float(np.sqrt(mean_squared_error(y_test[mask], y_pred[mask]))), 6),
                        "r2": round(float(r2_score(y_test[mask], y_pred[mask])), 4),
                        "samples": int(mask.sum()),
                    }

        self._emission_results = {
            "random_forest": {
                "mae": round(mae, 6),
                "rmse": round(rmse, 6),
                "r2": round(r2, 4),
                "mape_pct": round(mape, 4),
                "cv_r2_mean": round(float(np.mean(cv_r2)), 4),
                "cv_r2_std": round(float(np.std(cv_r2)), 4),
                "cv_mae_mean": round(float(np.mean(cv_mae)), 6),
                "cv_mae_std": round(float(np.std(cv_mae)), 6),
            },
            "linear_regression": {
                "mae": round(mae_lr, 6),
                "rmse": round(rmse_lr, 6),
                "r2": round(r2_lr, 4),
            },
            "residual_analysis": {
                "mean": round(res_mean, 6),
                "std": round(res_std, 6),
                "min": round(float(np.min(residuals)), 6),
                "max": round(float(np.max(residuals)), 6),
                "skewness": round(float(self._skew(residuals)), 4),
                "kurtosis": round(float(self._kurtosis(residuals)), 4),
            },
            "per_facility_type": per_type,
            "test_set_size": len(y_test),
            "train_set_size": len(y_train),
            "feature_importance": estimator.feature_importance(),
            "passes_threshold": r2 >= MIN_R2_SCORE and mae <= MAX_MAE_THRESHOLD,
            # Raw data for plotting
            "_plot_data": {
                "y_test": y_test.tolist(),
                "y_pred": y_pred.tolist(),
                "residuals": residuals.tolist(),
            },
        }
        return self._emission_results

    def evaluate_anomaly_detector(self, detector, X_normal: np.ndarray,
                                   readings_normal: List[Dict],
                                   sensor_fields: List[str]) -> Dict[str, Any]:
        """
        Evaluate anomaly detection model by injecting known anomalies.

        Args:
            detector: Trained AnomalyDetector instance.
            X_normal: Normal feature matrix.
            readings_normal: Normal reading dicts.
            sensor_fields: List of sensor field names.
        """
        rng = np.random.RandomState(RANDOM_STATE)

        # Create test set with injected anomalies
        n_anomalies = max(int(len(readings_normal) * ANOMALY_INJECTION_RATE), 20)
        n_normal_test = min(len(readings_normal), 500)

        test_readings = list(readings_normal[:n_normal_test])
        y_true = [0] * n_normal_test  # 0 = normal

        # Inject anomalies
        for i in range(n_anomalies):
            anom_type = ANOMALY_TYPES[i % len(ANOMALY_TYPES)]
            base = readings_normal[rng.randint(0, len(readings_normal))].copy()

            if anom_type == "emission_spike":
                base["co2_ppm"] = base.get("co2_ppm", 450) * rng.uniform(2.0, 5.0)
                base["ch4_ppm"] = base.get("ch4_ppm", 2.5) * rng.uniform(2.0, 4.0)
            elif anom_type == "sensor_malfunction":
                for f in sensor_fields[:3]:
                    base[f] = base.get(f, 100) * rng.uniform(5.0, 10.0)
            else:  # pattern_anomaly
                for f in sensor_fields:
                    base[f] = base.get(f, 100) * rng.uniform(1.5, 3.0)

            test_readings.append(base)
            y_true.append(1)  # 1 = anomaly

        # Run detector
        y_pred = []
        y_scores = []
        predictions = []
        for r in test_readings:
            try:
                result = detector.detect(r)
                predictions.append(result)
                y_pred.append(1 if result["anomaly_flag"] else 0)
                y_scores.append(result["severity_score"])
            except Exception:
                y_pred.append(0)
                y_scores.append(0.0)
                predictions.append({"anomaly_flag": False, "anomaly_type": "error"})

        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        y_scores = np.array(y_scores)

        # Metrics
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        try:
            auc_roc = float(roc_auc_score(y_true, y_scores))
        except ValueError:
            auc_roc = 0.0

        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        # Per-anomaly-type detection rate
        type_rates = {}
        anom_idx = n_normal_test
        for i in range(n_anomalies):
            atype = ANOMALY_TYPES[i % len(ANOMALY_TYPES)]
            if atype not in type_rates:
                type_rates[atype] = {"total": 0, "detected": 0}
            type_rates[atype]["total"] += 1
            if y_pred[anom_idx + i] == 1:
                type_rates[atype]["detected"] += 1

        for atype, counts in type_rates.items():
            counts["rate"] = round(counts["detected"] / max(counts["total"], 1), 4)

        self._anomaly_results = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "auc_roc": round(auc_roc, 4),
            "confusion_matrix": {
                "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            },
            "per_anomaly_type": type_rates,
            "total_test_samples": len(y_true),
            "injected_anomalies": n_anomalies,
            "normal_test_samples": n_normal_test,
            "passes_threshold": f1 >= MIN_F1_SCORE,
            "_plot_data": {
                "y_true": y_true.tolist(),
                "y_pred": y_pred.tolist(),
                "y_scores": y_scores.tolist(),
            },
        }
        return self._anomaly_results

    def get_emission_results(self) -> Dict[str, Any]:
        return self._emission_results

    def get_anomaly_results(self) -> Dict[str, Any]:
        return self._anomaly_results

    @staticmethod
    def _skew(arr):
        from scipy.stats import skew
        return skew(arr)

    @staticmethod
    def _kurtosis(arr):
        from scipy.stats import kurtosis
        return kurtosis(arr)
