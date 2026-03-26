"""
Timestamp Synchronizer — Step 2.1
===================================
Aligns timestamps to a 15-second grid, detects gaps,
and computes inter-reading deltas.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple


GRID_INTERVAL = timedelta(seconds=15)


class TimestampSynchronizer:
    """
    Synchronizes sensor reading timestamps to a uniform 15-second grid.

    Operations:
      - Snap timestamps to nearest 15-second boundary
      - Detect and flag gaps (missing readings)
      - Compute inter-reading time deltas
      - Sort readings chronologically
    """

    def __init__(self, interval_sec: int = 15):
        self._interval = timedelta(seconds=interval_sec)
        self._stats = {"total": 0, "snapped": 0, "gaps_detected": 0}

    def snap_to_grid(self, timestamp: str) -> str:
        """Snap an ISO timestamp to the nearest 15-second boundary."""
        dt = datetime.fromisoformat(timestamp)
        seconds = dt.second
        remainder = seconds % self._interval.total_seconds()
        if remainder <= self._interval.total_seconds() / 2:
            snapped = dt.replace(second=int(seconds - remainder), microsecond=0)
        else:
            snapped = dt.replace(second=0, microsecond=0) + timedelta(
                seconds=int((seconds // self._interval.total_seconds() + 1)
                            * self._interval.total_seconds())
            )
        return snapped.isoformat()

    def synchronize_reading(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Snap a single reading's timestamp to grid."""
        self._stats["total"] += 1
        r = copy.deepcopy(reading)
        original = r["timestamp_utc"]
        r["timestamp_utc"] = self.snap_to_grid(original)
        if r["timestamp_utc"] != original:
            self._stats["snapped"] += 1
            r["timestamp_synced"] = True
        else:
            r["timestamp_synced"] = False
        return r

    def synchronize_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Synchronize and sort a batch of readings chronologically."""
        synced = [self.synchronize_reading(r) for r in readings]
        synced.sort(key=lambda r: r["timestamp_utc"])
        return synced

    def detect_gaps(self, readings: List[Dict[str, Any]]) -> List[Tuple[str, str, int]]:
        """
        Detect time gaps in a sorted sequence of readings.

        Returns list of (gap_start, gap_end, missing_count) tuples.
        """
        if len(readings) < 2:
            return []

        gaps = []
        interval_sec = self._interval.total_seconds()
        for i in range(1, len(readings)):
            t0 = datetime.fromisoformat(readings[i - 1]["timestamp_utc"])
            t1 = datetime.fromisoformat(readings[i]["timestamp_utc"])
            delta = (t1 - t0).total_seconds()

            if delta > interval_sec * 1.5:  # gap threshold: 1.5× interval
                missing = int(delta / interval_sec) - 1
                gaps.append((readings[i - 1]["timestamp_utc"],
                             readings[i]["timestamp_utc"], missing))
                self._stats["gaps_detected"] += 1

        return gaps

    def compute_deltas(self, readings: List[Dict[str, Any]]) -> List[float]:
        """Compute time deltas (seconds) between consecutive readings."""
        deltas = []
        for i in range(1, len(readings)):
            t0 = datetime.fromisoformat(readings[i - 1]["timestamp_utc"])
            t1 = datetime.fromisoformat(readings[i]["timestamp_utc"])
            deltas.append((t1 - t0).total_seconds())
        return deltas

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
