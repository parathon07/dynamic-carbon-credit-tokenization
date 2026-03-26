"""
Dataset Validation — Step 4.1
================================
Validates synthetic IoT data against real-world benchmarks
(EPA/IPCC emission ranges) and performs statistical quality checks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
from scipy import stats

from src.config import (
    BENCHMARK_EMISSION_RANGES, SENSOR_REALISTIC_RANGES,
    VALIDATION_MIN_SAMPLES, SHAPIRO_ALPHA, CORRELATION_THRESHOLD,
)

logger = logging.getLogger("eval.dataset_validator")


class DatasetValidator:
    """
    Validates Phase 1 synthetic sensor data for realism and consistency.

    Methods:
      1. Range validation: sensor values within real-world bounds
      2. Distribution: normality test (Shapiro-Wilk)
      3. Correlation: expected sensor inter-correlations
      4. Benchmark alignment: CO₂e vs EPA/IPCC ranges
      5. Completeness: missing values, NaN check
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def validate(self, readings: List[Dict[str, Any]],
                 co2e_values: List[float]) -> Dict[str, Any]:
        """
        Run full validation suite.

        Args:
            readings: List of Phase 1 sensor reading dicts.
            co2e_values: Corresponding CO₂e emission values.

        Returns:
            Validation report with scores and details.
        """
        if len(readings) < VALIDATION_MIN_SAMPLES:
            return {"status": "error", "message": "Insufficient samples"}

        results = {
            "sample_size": len(readings),
            "completeness": self._check_completeness(readings),
            "range_validation": self._validate_ranges(readings),
            "distribution_analysis": self._analyse_distribution(readings),
            "correlation_analysis": self._analyse_correlations(readings),
            "benchmark_alignment": self._align_benchmarks(readings, co2e_values),
            "temporal_consistency": self._check_temporal(readings),
        }

        # Aggregate score (0-1)
        scores = [
            results["completeness"]["score"],
            results["range_validation"]["score"],
            results["distribution_analysis"]["score"],
            results["benchmark_alignment"]["score"],
        ]
        overall = round(float(np.mean(scores)), 4)

        results["validation_score"] = overall
        results["data_reliability"] = (
            "high" if overall >= 0.85 else "medium" if overall >= 0.65 else "low"
        )
        self._results = results
        return results

    def _check_completeness(self, readings: List[Dict]) -> Dict[str, Any]:
        """Check for missing values and NaN."""
        required = ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh",
                     "facility_id", "timestamp_utc"]
        total_fields = len(readings) * len(required)
        missing = 0

        for r in readings:
            for field in required:
                val = r.get(field)
                if val is None:
                    missing += 1
                elif isinstance(val, float) and np.isnan(val):
                    missing += 1

        completeness = 1.0 - (missing / max(total_fields, 1))
        return {
            "total_fields": total_fields,
            "missing_fields": missing,
            "completeness_pct": round(completeness * 100, 2),
            "score": round(completeness, 4),
        }

    def _validate_ranges(self, readings: List[Dict]) -> Dict[str, Any]:
        """Check sensor values are within realistic bounds."""
        in_range = 0
        out_of_range = 0
        violations = {}

        for field, (lo, hi) in SENSOR_REALISTIC_RANGES.items():
            values = [r.get(field, 0) for r in readings if field in r]
            in_count = sum(1 for v in values if lo <= v <= hi)
            out_count = len(values) - in_count
            in_range += in_count
            out_of_range += out_count
            if out_count > 0:
                violations[field] = {
                    "out_of_range": out_count,
                    "pct": round(out_count / max(len(values), 1) * 100, 2),
                    "expected": (lo, hi),
                    "actual_range": (round(min(values), 2), round(max(values), 2)),
                }

        total = in_range + out_of_range
        score = in_range / max(total, 1)
        return {
            "in_range": in_range,
            "out_of_range": out_of_range,
            "score": round(score, 4),
            "violations": violations,
        }

    def _analyse_distribution(self, readings: List[Dict]) -> Dict[str, Any]:
        """Normality tests and distribution statistics for each sensor."""
        dist_results = {}
        scores = []

        for field in SENSOR_REALISTIC_RANGES.keys():
            values = np.array([r.get(field, 0) for r in readings if field in r])
            if len(values) < 20:
                continue

            # Shapiro-Wilk on a sample (max 5000 for performance)
            sample = values[:5000] if len(values) > 5000 else values
            try:
                stat, p_value = stats.shapiro(sample)
            except Exception:
                stat, p_value = 0.0, 0.0

            is_normal = p_value > SHAPIRO_ALPHA
            dist_results[field] = {
                "mean": round(float(np.mean(values)), 4),
                "std": round(float(np.std(values)), 4),
                "min": round(float(np.min(values)), 4),
                "max": round(float(np.max(values)), 4),
                "skewness": round(float(stats.skew(values)), 4),
                "kurtosis": round(float(stats.kurtosis(values)), 4),
                "shapiro_stat": round(float(stat), 4),
                "shapiro_p": round(float(p_value), 4),
                "is_normal": is_normal,
            }
            # Score: give partial credit even for non-normal (common in env data)
            scores.append(min(1.0, p_value / SHAPIRO_ALPHA) if p_value > 0.001 else 0.5)

        return {
            "fields": dist_results,
            "score": round(float(np.mean(scores)), 4) if scores else 0.0,
        }

    def _analyse_correlations(self, readings: List[Dict]) -> Dict[str, Any]:
        """Check expected inter-sensor correlations."""
        fields = list(SENSOR_REALISTIC_RANGES.keys())
        n = len(fields)
        data = {}
        for f in fields:
            data[f] = np.array([r.get(f, 0) for r in readings])

        corr_matrix = {}
        significant_pairs = 0
        total_pairs = 0

        for i in range(n):
            for j in range(i + 1, n):
                fi, fj = fields[i], fields[j]
                r_val, p_val = stats.pearsonr(data[fi], data[fj])
                pair_key = f"{fi}_vs_{fj}"
                corr_matrix[pair_key] = {
                    "r": round(float(r_val), 4),
                    "p_value": round(float(p_val), 6),
                    "significant": abs(r_val) > CORRELATION_THRESHOLD,
                }
                total_pairs += 1
                if abs(r_val) > CORRELATION_THRESHOLD:
                    significant_pairs += 1

        return {
            "correlations": corr_matrix,
            "significant_pairs": significant_pairs,
            "total_pairs": total_pairs,
        }

    def _align_benchmarks(self, readings: List[Dict],
                          co2e_values: List[float]) -> Dict[str, Any]:
        """Compare emission values against EPA/IPCC benchmark ranges."""
        by_type: Dict[str, List[float]] = {}

        for r, co2e in zip(readings, co2e_values):
            ft = r.get("facility_type", "unknown")
            if ft not in by_type:
                by_type[ft] = []
            by_type[ft].append(co2e)

        alignment = {}
        scores = []

        for ft, values in by_type.items():
            arr = np.array(values)
            avg = float(np.mean(arr))
            bench = BENCHMARK_EMISSION_RANGES.get(ft)

            if bench:
                lo, hi = bench
                in_range = sum(1 for v in values if lo <= v <= hi)
                pct = in_range / len(values)
                deviation = 0.0
                if avg < lo:
                    deviation = (lo - avg) / lo
                elif avg > hi:
                    deviation = (avg - hi) / hi

                alignment[ft] = {
                    "avg_co2e": round(avg, 4),
                    "benchmark_range": bench,
                    "in_range_pct": round(pct * 100, 2),
                    "deviation": round(deviation, 4),
                }
                scores.append(pct)

        return {
            "by_facility_type": alignment,
            "score": round(float(np.mean(scores)), 4) if scores else 0.0,
            "deviation_from_standard": round(
                float(np.mean([a["deviation"] for a in alignment.values()])), 4
            ) if alignment else 0.0,
        }

    def _check_temporal(self, readings: List[Dict]) -> Dict[str, Any]:
        """Check temporal consistency (intervals, ordering)."""
        from datetime import datetime
        timestamps = []
        for r in readings[:1000]:  # sample
            try:
                ts = datetime.fromisoformat(r["timestamp_utc"])
                timestamps.append(ts)
            except (KeyError, ValueError):
                pass

        if len(timestamps) < 2:
            return {"status": "insufficient_data"}

        intervals = [(timestamps[i+1] - timestamps[i]).total_seconds()
                      for i in range(len(timestamps)-1)]
        intervals = [i for i in intervals if i > 0]

        return {
            "total_timestamps": len(timestamps),
            "avg_interval_sec": round(float(np.mean(intervals)), 2) if intervals else 0,
            "std_interval_sec": round(float(np.std(intervals)), 2) if intervals else 0,
            "min_interval_sec": round(min(intervals), 2) if intervals else 0,
            "max_interval_sec": round(max(intervals), 2) if intervals else 0,
        }

    def get_results(self) -> Dict[str, Any]:
        return self._results
