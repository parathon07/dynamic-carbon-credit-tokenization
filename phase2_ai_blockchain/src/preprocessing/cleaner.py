"""
Data Cleaner — Step 2.1
========================
Removes noise, handles null values, clips outliers, replaces
fault sentinels (-999), and fills gaps via linear interpolation.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.config import VALID_SENSOR_BOUNDS, SENSOR_FIELDS

logger = logging.getLogger("preprocessing.cleaner")


class DataCleaner:
    """
    Cleans raw IoT sensor readings for downstream AI processing.

    Operations (in order):
      1. Remove readings with missing required keys
      2. Replace fault sentinels (-999.0) with NaN
      3. Type-coerce sensor values to float
      4. Clip values to valid bounds
      5. Interpolate NaN gaps using forward-fill + backward-fill
      6. Attach quality_flag to each reading
    """

    def __init__(self, bounds: Optional[Dict[str, Tuple[float, float]]] = None):
        self._bounds = bounds or VALID_SENSOR_BOUNDS
        self._stats = {"total": 0, "cleaned": 0, "rejected": 0, "interpolated": 0}

    # ── Public API ───────────────────────────────────────────────────────

    def clean_reading(self, reading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single reading dict. Returns None if unrecoverable."""
        self._stats["total"] += 1
        r = copy.deepcopy(reading)

        # Step 1: Check required keys
        required = {"facility_id", "timestamp_utc"} | set(SENSOR_FIELDS)
        if not required.issubset(r.keys()):
            self._stats["rejected"] += 1
            return None

        # Step 2 + 3: Coerce types and handle sentinels
        quality_issues = []
        for field in SENSOR_FIELDS:
            val = r[field]

            # Handle None
            if val is None:
                r[field] = float("nan")
                quality_issues.append(f"{field}_null")
                continue

            # Type coerce
            try:
                val = float(val)
            except (TypeError, ValueError):
                r[field] = float("nan")
                quality_issues.append(f"{field}_type_error")
                continue

            # Fault sentinel
            if val == -999.0:
                r[field] = float("nan")
                quality_issues.append(f"{field}_fault")
                continue

            # Step 4: Clip to valid bounds
            lo, hi = self._bounds.get(field, (None, None))
            if lo is not None and val < lo:
                r[field] = lo
                quality_issues.append(f"{field}_clipped_low")
            elif hi is not None and val > hi:
                r[field] = hi
                quality_issues.append(f"{field}_clipped_high")
            else:
                r[field] = val

        # Reject if all sensor fields are NaN
        if all(np.isnan(r[f]) for f in SENSOR_FIELDS):
            self._stats["rejected"] += 1
            return None

        r["quality_flag"] = "clean" if not quality_issues else "|".join(quality_issues)
        self._stats["cleaned"] += 1
        return r

    def clean_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean a batch of readings. Applies interpolation for NaN gaps."""
        cleaned = []
        for r in readings:
            result = self.clean_reading(r)
            if result is not None:
                cleaned.append(result)

        # Interpolate remaining NaN values across the batch
        if len(cleaned) > 1:
            cleaned = self._interpolate_nans(cleaned)

        return cleaned

    def get_stats(self) -> Dict[str, int]:
        """Return cleaning statistics."""
        return dict(self._stats)

    def reset_stats(self):
        """Reset cleaning statistics."""
        self._stats = {"total": 0, "cleaned": 0, "rejected": 0, "interpolated": 0}

    # ── Internal ─────────────────────────────────────────────────────────

    def _interpolate_nans(self, readings: List[Dict]) -> List[Dict]:
        """Forward-fill then backward-fill NaN values per sensor field."""
        for field in SENSOR_FIELDS:
            values = [r[field] for r in readings]
            arr = np.array(values, dtype=float)

            nan_mask = np.isnan(arr)
            if not nan_mask.any():
                continue

            # Forward fill
            for i in range(1, len(arr)):
                if np.isnan(arr[i]) and not np.isnan(arr[i - 1]):
                    arr[i] = arr[i - 1]
                    self._stats["interpolated"] += 1

            # Backward fill remaining
            for i in range(len(arr) - 2, -1, -1):
                if np.isnan(arr[i]) and not np.isnan(arr[i + 1]):
                    arr[i] = arr[i + 1]
                    self._stats["interpolated"] += 1

            for i, r in enumerate(readings):
                if nan_mask[i] and not np.isnan(arr[i]):
                    r[field] = round(float(arr[i]), 4)
                    if "interpolated" not in r.get("quality_flag", ""):
                        r["quality_flag"] = r.get("quality_flag", "") + "|interpolated"

        return readings
