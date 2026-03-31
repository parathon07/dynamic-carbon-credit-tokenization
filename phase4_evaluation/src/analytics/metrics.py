"""
Research Validation Metrics — Step 4.2
=========================================
Computes exact analytical metrics requested in the paper for
model accuracy, blockchain performance, and pricing stability.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("analytics.metrics")


class ResearchMetricsEvaluator:
    """Computes final R² / TPS / F1 / Stackelberg KPIs."""
    
    @staticmethod
    def evaluate_emission_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculates prediction accuracy of LSTM/XGBoost."""
        mse = np.mean((y_true - y_pred) ** 2)
        rmse = np.sqrt(mse)
        
        # Mean Absolute Percentage Error (avoid div-zero)
        mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1e-8))) * 100.0
        
        # R-squared
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / max(ss_tot, 1e-8))
        
        return {
            "RMSE": round(float(rmse), 4),
            "MAPE_pct": round(float(mape), 2),
            "R2_Score": round(float(r2), 4)
        }

    @staticmethod
    def evaluate_fraud_detection(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculates classification metrics for Ensemble Voting."""
        tp = np.sum((y_true == 1) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        
        accuracy = (tp + tn) / max(len(y_true), 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1_score = 2 * (precision * recall) / max(precision + recall, 1e-8)
        
        return {
            "Accuracy": round(float(accuracy), 4),
            "Precision": round(float(precision), 4),
            "Recall": round(float(recall), 4),
            "F1_Score": round(float(f1_score), 4)
        }

    @staticmethod
    def evaluate_blockchain_performance(block_timestamps: List[float], total_txs: int) -> Dict[str, float]:
        """Evaluates PoA Ledger TPS and confirmation times."""
        if len(block_timestamps) < 2 or total_txs == 0:
            return {"TPS": 0.0, "Avg_Confirmation_Sec": 0.0}
            
        time_elapsed = block_timestamps[-1] - block_timestamps[0]
        tps = total_txs / max(time_elapsed, 0.1)
        
        # Confirmation time roughly average delta between blocks
        deltas = np.diff(block_timestamps)
        avg_conf = np.mean(deltas)
        
        return {
            "TPS": round(float(tps), 2),
            "Avg_Confirmation_Sec": round(float(avg_conf), 2)
        }

    @staticmethod
    def evaluate_pricing_stability(price_history: List[float]) -> Dict[str, float]:
        """Evaluates Stackelberg Equilibrium stability."""
        if len(price_history) < 2:
            return {"Coefficient_of_Variation": 0.0, "Mean_Reversion_Sim": 0.0}
            
        prices = np.array(price_history)
        mean_p = np.mean(prices)
        std_p = np.std(prices)
        
        cv = std_p / max(mean_p, 1e-8)
        
        # Simple Mean Reversion check: correlation of price drop vs distance from mean
        deltas = np.diff(prices)
        dist_from_mean = prices[:-1] - mean_p
        # If price is far above mean, delta should be negative
        reversion_corr = np.corrcoef(dist_from_mean, deltas)[0, 1] if len(prices) > 2 else 0.0
        
        return {
            "Coefficient_of_Variation": round(float(cv), 4),
            "Mean_Reversion_Corr": round(float(reversion_corr), 4),
            "Stability_Status": "Stable" if cv < 0.15 else "Volatile"
        }
