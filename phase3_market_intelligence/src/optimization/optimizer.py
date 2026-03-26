"""
Emission Optimizer — Step 3.4
================================
AI-based emission reduction recommendation system.
Analyses facility emission patterns and suggests actionable optimizations.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import (
    OPTIMIZATION_LOOKBACK, FUEL_REDUCTION_COST_PER_PCT,
    ENERGY_SAVING_PER_KWH, SENSOR_FIELDS,
)

logger = logging.getLogger("optimization.optimizer")


class EmissionOptimizer:
    """
    Recommends emission reduction actions per facility.

    Analysis methods:
      - Trend analysis (are emissions increasing/decreasing?)
      - Peer comparison (how does this facility compare to its type?)
      - Operational optimization (fuel, energy efficiency opportunities)
      - Predictive forecasting (where will emissions be next period?)

    Output per recommendation:
      {recommendation, expected_emission_reduction, cost_saving, priority, confidence}
    """

    def __init__(self):
        self._facility_history: Dict[str, List[Dict]] = defaultdict(list)
        self._type_benchmarks: Dict[str, Dict[str, float]] = {}
        self._recommendations_issued: int = 0

    def record_reading(self, reading: Dict[str, Any]):
        """Ingest a processed reading for analysis."""
        fid = reading.get("facility_id", "unknown")
        self._facility_history[fid].append(reading)
        # Keep only recent history
        if len(self._facility_history[fid]) > OPTIMIZATION_LOOKBACK * 2:
            self._facility_history[fid] = self._facility_history[fid][-OPTIMIZATION_LOOKBACK:]

    def record_readings(self, readings: List[Dict[str, Any]]):
        """Ingest a batch of readings."""
        for r in readings:
            self.record_reading(r)

    def compute_benchmarks(self):
        """Compute per-type benchmarks from all recorded data."""
        type_data: Dict[str, List[Dict]] = defaultdict(list)
        for fid, history in self._facility_history.items():
            for r in history:
                ft = r.get("facility_type")
                if ft:
                    type_data[ft].append(r)

        for ft, readings in type_data.items():
            benchmarks = {}
            for field in SENSOR_FIELDS:
                vals = [r[field] for r in readings if field in r and r[field] is not None]
                if vals:
                    benchmarks[field] = {
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals)),
                        "p25": float(np.percentile(vals, 25)),
                        "p75": float(np.percentile(vals, 75)),
                    }
            if "co2e_emission" in readings[0]:
                co2e_vals = [r["co2e_emission"] for r in readings if "co2e_emission" in r]
                if co2e_vals:
                    benchmarks["co2e_emission"] = {
                        "mean": float(np.mean(co2e_vals)),
                        "std": float(np.std(co2e_vals)),
                    }
            self._type_benchmarks[ft] = benchmarks

    def generate_recommendations(self, facility_id: str) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations for a facility.

        Returns list of recommendations sorted by priority.
        """
        history = self._facility_history.get(facility_id, [])
        if len(history) < 5:
            return [{"recommendation": "Insufficient data for analysis",
                     "priority": "low", "confidence": 0.0}]

        recent = history[-OPTIMIZATION_LOOKBACK:]
        ft = recent[-1].get("facility_type", "unknown")
        recommendations = []

        # (1) Fuel usage optimization
        fuel_vals = [r.get("fuel_rate", 0) for r in recent if r.get("fuel_rate")]
        if fuel_vals:
            avg_fuel = np.mean(fuel_vals)
            benchmark = self._type_benchmarks.get(ft, {}).get("fuel_rate", {})
            bench_mean = benchmark.get("mean", avg_fuel)

            if avg_fuel > bench_mean * 1.05:
                reduction_pct = round(((avg_fuel - bench_mean) / avg_fuel) * 100, 1)
                co2e_saving = round(reduction_pct * 0.01 * avg_fuel * 0.044, 4)
                cost = round(reduction_pct * FUEL_REDUCTION_COST_PER_PCT, 2)
                recommendations.append({
                    "recommendation": f"Reduce fuel usage by {reduction_pct}% to match type average",
                    "category": "fuel_optimization",
                    "expected_emission_reduction": co2e_saving,
                    "cost_saving": round(co2e_saving * 25, 2),  # at $25/credit
                    "implementation_cost": cost,
                    "priority": "high" if reduction_pct > 10 else "medium",
                    "confidence": min(len(fuel_vals) / 20, 1.0),
                })

        # (2) Energy efficiency
        energy_vals = [r.get("energy_kwh", 0) for r in recent if r.get("energy_kwh")]
        if energy_vals:
            avg_energy = np.mean(energy_vals)
            benchmark = self._type_benchmarks.get(ft, {}).get("energy_kwh", {})
            bench_p75 = benchmark.get("p75", avg_energy)

            if avg_energy > bench_p75:
                excess_kwh = round(avg_energy - bench_p75, 1)
                saving = round(excess_kwh * ENERGY_SAVING_PER_KWH, 2)
                recommendations.append({
                    "recommendation": f"Optimize energy consumption — excess {excess_kwh:.0f} kWh/reading vs top quartile",
                    "category": "energy_efficiency",
                    "expected_emission_reduction": round(excess_kwh * 0.000046 * 265, 4),
                    "cost_saving": saving,
                    "implementation_cost": round(saving * 5, 2),
                    "priority": "medium",
                    "confidence": min(len(energy_vals) / 20, 1.0),
                })

        # (3) Emission trend analysis
        co2e_vals = [r.get("co2e_emission", 0) for r in recent if r.get("co2e_emission")]
        if len(co2e_vals) >= 10:
            recent_avg = np.mean(co2e_vals[-10:])
            older_avg = np.mean(co2e_vals[:10])
            trend_pct = ((recent_avg - older_avg) / (older_avg + 1e-10)) * 100

            if trend_pct > 5:
                recommendations.append({
                    "recommendation": f"Emissions trending UP by {trend_pct:.1f}% — investigate root cause",
                    "category": "trend_alert",
                    "expected_emission_reduction": round(abs(recent_avg - older_avg), 4),
                    "cost_saving": round(abs(recent_avg - older_avg) * 0.001 * 25, 2),
                    "implementation_cost": 0,
                    "priority": "high",
                    "confidence": 0.8,
                })
            elif trend_pct < -5:
                recommendations.append({
                    "recommendation": f"Emissions trending DOWN by {abs(trend_pct):.1f}% — maintain current practices",
                    "category": "positive_trend",
                    "expected_emission_reduction": 0.0,
                    "cost_saving": 0.0,
                    "implementation_cost": 0,
                    "priority": "info",
                    "confidence": 0.8,
                })

        # (4) Peak emission reduction
        if co2e_vals:
            peak = max(co2e_vals)
            avg = np.mean(co2e_vals)
            if peak > avg * 1.5:
                recommendations.append({
                    "recommendation": "Reduce peak emissions — consider load shifting or scheduling optimization",
                    "category": "peak_reduction",
                    "expected_emission_reduction": round(peak - avg, 4),
                    "cost_saving": round((peak - avg) * 0.001 * 25, 2),
                    "implementation_cost": round(FUEL_REDUCTION_COST_PER_PCT * 3, 2),
                    "priority": "medium",
                    "confidence": 0.7,
                })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))

        self._recommendations_issued += len(recommendations)
        return recommendations

    def get_facility_profile(self, facility_id: str) -> Dict[str, Any]:
        """Return analytical profile for a facility."""
        history = self._facility_history.get(facility_id, [])
        if not history:
            return {"facility_id": facility_id, "status": "no data"}

        co2e_vals = [r.get("co2e_emission", 0) for r in history if r.get("co2e_emission")]

        return {
            "facility_id": facility_id,
            "facility_type": history[-1].get("facility_type", "unknown"),
            "total_readings": len(history),
            "avg_co2e": round(float(np.mean(co2e_vals)), 4) if co2e_vals else 0,
            "max_co2e": round(float(max(co2e_vals)), 4) if co2e_vals else 0,
            "min_co2e": round(float(min(co2e_vals)), 4) if co2e_vals else 0,
            "std_co2e": round(float(np.std(co2e_vals)), 4) if co2e_vals else 0,
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "facilities_tracked": len(self._facility_history),
            "total_readings": sum(len(v) for v in self._facility_history.values()),
            "benchmarks_computed": len(self._type_benchmarks),
            "recommendations_issued": self._recommendations_issued,
        }
