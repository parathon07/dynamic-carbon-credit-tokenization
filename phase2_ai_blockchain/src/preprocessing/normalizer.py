"""
Sensor Normalizer — Step 2.1
=============================
Min-max and z-score normalization for sensor readings.
Stores fitted parameters for consistent scaling during inference.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.config import NORMALIZATION_RANGES, SENSOR_FIELDS


class SensorNormalizer:
    """
    Normalizes sensor readings using min-max or z-score scaling.

    Modes:
      - 'minmax': scales to [0, 1] using configured ranges
      - 'zscore': standardizes using computed mean/std from fit data
    """

    def __init__(self, mode: str = "minmax"):
        assert mode in ("minmax", "zscore"), f"Unknown mode: {mode}"
        self._mode = mode
        self._ranges = dict(NORMALIZATION_RANGES)  # for minmax
        self._stats: Dict[str, Tuple[float, float]] = {}  # for zscore: {field: (mean, std)}
        self._fitted = mode == "minmax"  # minmax uses config ranges, always ready

    # ── Public API ───────────────────────────────────────────────────────

    def fit(self, readings: List[Dict[str, Any]]) -> "SensorNormalizer":
        """Compute mean/std from a batch (required for zscore mode)."""
        if self._mode == "zscore":
            for field in SENSOR_FIELDS:
                values = [r[field] for r in readings
                          if field in r and not np.isnan(r[field])]
                if values:
                    self._stats[field] = (float(np.mean(values)), float(np.std(values)) + 1e-8)
                else:
                    self._stats[field] = (0.0, 1.0)
        self._fitted = True
        return self

    def normalize_reading(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single reading in-place (returns copy)."""
        assert self._fitted, "Call fit() before normalize (zscore mode)"
        r = copy.deepcopy(reading)

        for field in SENSOR_FIELDS:
            if field not in r or (isinstance(r[field], float) and np.isnan(r[field])):
                continue

            val = float(r[field])

            if self._mode == "minmax":
                lo, hi = self._ranges[field]
                r[field] = round(max(0.0, min(1.0, (val - lo) / (hi - lo + 1e-8))), 6)
            else:
                mean, std = self._stats[field]
                r[field] = round((val - mean) / std, 6)

        r["normalization_mode"] = self._mode
        return r

    def normalize_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize a batch of readings."""
        return [self.normalize_reading(r) for r in readings]

    def denormalize_value(self, field: str, normalized_val: float) -> float:
        """Reverse the normalization for a single value."""
        if self._mode == "minmax":
            lo, hi = self._ranges[field]
            return normalized_val * (hi - lo) + lo
        else:
            mean, std = self._stats[field]
            return normalized_val * std + mean

    def get_params(self) -> Dict:
        """Return the normalization parameters."""
        if self._mode == "minmax":
            return {"mode": "minmax", "ranges": self._ranges}
        return {"mode": "zscore", "stats": self._stats}
