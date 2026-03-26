"""
Comparative Analysis — Step 4.6
==================================
Compares our blockchain-AI system against Traditional ETS and
static credit models across multiple evaluation dimensions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from src.config import (
    COMPARISON_DIMENSIONS, TRADITIONAL_ETS_SCORES, STATIC_MODEL_SCORES,
)

logger = logging.getLogger("eval.system_comparator")


class SystemComparator:
    """
    Generates structured comparison data for radar charts and tables.

    Compares three systems:
      1. Proposed (Blockchain + AI + IoT)
      2. Traditional Emission Trading System (ETS)
      3. Static Credit Model
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def compute_proposed_scores(self, eval_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Derive scores (0–10) for our system from actual evaluation results.

        Args:
            eval_results: Combined results from Steps 4.1–4.5.
        """
        scores = {}

        # Transparency: blockchain-verified → 9/10
        bc = eval_results.get("blockchain", {})
        chain_valid = bc.get("validation_scaling", {}).get("results", [{}])
        all_valid = all(r.get("is_valid", False) for r in chain_valid)
        scores["transparency"] = 9.0 if all_valid else 7.0

        # Real-time: based on pipeline throughput
        scale = eval_results.get("scalability", {})
        fac_data = scale.get("facility_scaling", {}).get("data_points", [])
        if fac_data:
            avg_tps = float(np.mean([d.get("throughput", 0) for d in fac_data if d.get("success")]))
            scores["real_time_capability"] = min(9.0, max(3.0, avg_tps / 20.0 + 5.0))
        else:
            scores["real_time_capability"] = 7.0

        # Pricing accuracy: based on AI R²
        ai = eval_results.get("ai_eval", {})
        emission = ai.get("emission", {}).get("random_forest", {})
        r2 = emission.get("r2", 0.95)
        scores["pricing_accuracy"] = min(10.0, r2 * 10.0)

        # Fraud detection: based on anomaly F1
        anomaly = ai.get("anomaly", {})
        f1 = anomaly.get("f1_score", 0.7)
        scores["fraud_detection"] = min(9.0, f1 * 10.0 + 1.0)

        # Scalability: based on bottleneck analysis
        bottleneck = scale.get("bottleneck_analysis", "")
        if bottleneck == "scales_well":
            scores["scalability"] = 8.0
        elif bottleneck == "moderate_degradation":
            scores["scalability"] = 6.0
        else:
            scores["scalability"] = 5.0

        # Cost efficiency: simulated blockchain is cheaper than real Ethereum
        scores["cost_efficiency"] = 7.0

        return {k: round(v, 1) for k, v in scores.items()}

    def compare(self, eval_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate full comparative analysis.

        Args:
            eval_results: Combined results from Steps 4.1–4.5.
        """
        proposed = self.compute_proposed_scores(eval_results)

        comparison = {
            "dimensions": COMPARISON_DIMENSIONS,
            "systems": {
                "proposed": proposed,
                "traditional_ets": dict(TRADITIONAL_ETS_SCORES),
                "static_model": dict(STATIC_MODEL_SCORES),
            },
            "radar_chart_data": {
                dim: {
                    "proposed": proposed.get(dim, 5.0),
                    "traditional_ets": TRADITIONAL_ETS_SCORES.get(dim, 5),
                    "static_model": STATIC_MODEL_SCORES.get(dim, 5),
                }
                for dim in COMPARISON_DIMENSIONS
            },
            "overall_scores": {
                "proposed": round(float(np.mean(list(proposed.values()))), 2),
                "traditional_ets": round(
                    float(np.mean(list(TRADITIONAL_ETS_SCORES.values()))), 2
                ),
                "static_model": round(
                    float(np.mean(list(STATIC_MODEL_SCORES.values()))), 2
                ),
            },
        }

        # Improvement percentage over traditional ETS
        improvements = {}
        for dim in COMPARISON_DIMENSIONS:
            p = proposed.get(dim, 5)
            t = TRADITIONAL_ETS_SCORES.get(dim, 5)
            if t > 0:
                improvements[dim] = round(((p - t) / t) * 100, 1)
        comparison["improvement_vs_ets_pct"] = improvements

        self._results = comparison
        return comparison

    def get_results(self) -> Dict[str, Any]:
        return self._results
