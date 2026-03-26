"""
Scalability & Load Testing — Step 4.5
========================================
Simulates increasing load (facilities, readings, trades) and
measures system response time, throughput, and failure rates.
"""

from __future__ import annotations

import logging
import time
import tracemalloc
from typing import Any, Callable, Dict, List

import numpy as np

from src.config import (
    SCALE_FACILITY_COUNTS, SCALE_READING_COUNTS, SCALE_TRADE_COUNTS,
)

logger = logging.getLogger("eval.load_tester")


class LoadTester:
    """
    Scalability testing for the full pipeline.

    Tests:
      1. Facility scaling: throughput vs facility count
      2. Reading scaling: throughput vs reading count
      3. Trade scaling: order book performance vs trade volume
      4. Memory profiling at each scale point
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def run_all_tests(self, reading_generator, pipeline_processor,
                      trade_executor=None) -> Dict[str, Any]:
        """
        Run full scalability test suite.

        Args:
            reading_generator: Callable(n_facilities, n_readings) -> List[Dict]
            pipeline_processor: Callable(readings) -> List[Dict]
            trade_executor: Optional Callable(n_trades) -> List[Dict]
        """
        results = {
            "facility_scaling": self._test_facility_scaling(
                reading_generator, pipeline_processor
            ),
            "reading_scaling": self._test_reading_scaling(
                reading_generator, pipeline_processor
            ),
        }

        if trade_executor:
            results["trade_scaling"] = self._test_trade_scaling(trade_executor)

        # Identify bottleneck
        facility_data = results["facility_scaling"]["data_points"]
        if len(facility_data) >= 2:
            tps_values = [d["throughput"] for d in facility_data]
            if tps_values[-1] < tps_values[0] * 0.5:
                bottleneck = "significant_degradation"
            elif tps_values[-1] < tps_values[0] * 0.8:
                bottleneck = "moderate_degradation"
            else:
                bottleneck = "scales_well"
        else:
            bottleneck = "insufficient_data"

        results["bottleneck_analysis"] = bottleneck
        self._results = results
        return results

    def _test_facility_scaling(self, generator, processor) -> Dict[str, Any]:
        """Test throughput scaling with increasing facility count."""
        data_points = []

        for n_fac in SCALE_FACILITY_COUNTS:
            n_readings = min(n_fac * 10, 2000)  # Cap for speed
            try:
                readings = generator(n_fac, n_readings)

                tracemalloc.start()
                start = time.perf_counter()
                results = processor(readings)
                elapsed = time.perf_counter() - start
                _, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                throughput = len(readings) / max(elapsed, 1e-6)

                data_points.append({
                    "facilities": n_fac,
                    "readings": len(readings),
                    "elapsed_sec": round(elapsed, 3),
                    "throughput": round(throughput, 1),
                    "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
                    "success": True,
                })
            except Exception as e:
                data_points.append({
                    "facilities": n_fac,
                    "success": False,
                    "error": str(e),
                })

        return {"data_points": data_points}

    def _test_reading_scaling(self, generator, processor) -> Dict[str, Any]:
        """Test throughput scaling with increasing readings per facility."""
        data_points = []

        for n_readings in SCALE_READING_COUNTS:
            if n_readings > 5000:
                continue  # Skip very large for speed
            n_fac = max(5, n_readings // 20)
            try:
                readings = generator(n_fac, n_readings)

                start = time.perf_counter()
                results = processor(readings)
                elapsed = time.perf_counter() - start

                throughput = len(readings) / max(elapsed, 1e-6)

                data_points.append({
                    "target_readings": n_readings,
                    "actual_readings": len(readings),
                    "facilities": n_fac,
                    "elapsed_sec": round(elapsed, 3),
                    "throughput": round(throughput, 1),
                    "success": True,
                })
            except Exception as e:
                data_points.append({
                    "target_readings": n_readings,
                    "success": False,
                    "error": str(e),
                })

        return {"data_points": data_points}

    def _test_trade_scaling(self, executor) -> Dict[str, Any]:
        """Test order book performance at increasing trade volumes."""
        data_points = []

        for n_trades in SCALE_TRADE_COUNTS:
            try:
                start = time.perf_counter()
                trades = executor(n_trades)
                elapsed = time.perf_counter() - start

                tps = n_trades / max(elapsed, 1e-6)

                data_points.append({
                    "target_trades": n_trades,
                    "executed": len(trades) if isinstance(trades, list) else 0,
                    "elapsed_sec": round(elapsed, 3),
                    "trades_per_sec": round(tps, 1),
                    "success": True,
                })
            except Exception as e:
                data_points.append({
                    "target_trades": n_trades,
                    "success": False,
                    "error": str(e),
                })

        return {"data_points": data_points}

    def get_results(self) -> Dict[str, Any]:
        return self._results
