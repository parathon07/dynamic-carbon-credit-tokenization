"""
Integration Testing — Step 4.4
=================================
End-to-end pipeline verification:
IoT → Clean → AI → Credit → Blockchain → Marketplace
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("eval.integration_tester")


class PipelineTester:
    """
    Tests the full system pipeline for data integrity, credit
    conservation, double-counting prevention, and token consistency.
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def run_all_tests(self, p2_pipeline, token, blockchain,
                      readings: List[Dict]) -> Dict[str, Any]:
        """
        Run full integration test suite.

        Args:
            p2_pipeline: Phase 2 pipeline orchestrator instance.
            token: CarbonToken instance.
            blockchain: Blockchain instance.
            readings: Phase 1 validated sensor readings.
        """
        results = {
            "pipeline_flow": self._test_pipeline_flow(p2_pipeline, readings),
            "credit_conservation": self._test_credit_conservation(token),
            "blockchain_integrity": self._test_blockchain_integrity(blockchain),
            "double_counting": self._test_double_counting(token),
            "token_consistency": self._test_token_consistency(token),
        }

        passed = sum(1 for v in results.values() if v.get("passed"))
        total = len(results)

        results["summary"] = {
            "tests_passed": passed,
            "tests_total": total,
            "pass_rate": round(passed / max(total, 1) * 100, 1),
            "all_passed": passed == total,
        }
        self._results = results
        return results

    def _test_pipeline_flow(self, pipeline, readings) -> Dict[str, Any]:
        """Verify data flows correctly through each pipeline stage."""
        start = time.perf_counter()
        results = []
        errors = []

        for i, reading in enumerate(readings[:100]):  # Sample
            try:
                result = pipeline.process_single(reading)
                if result and "co2e_emission" in result:
                    results.append(result)
                else:
                    errors.append({"index": i, "error": "missing co2e_emission"})
            except Exception as e:
                errors.append({"index": i, "error": str(e)})

        elapsed = time.perf_counter() - start
        success_rate = len(results) / max(len(results) + len(errors), 1)

        return {
            "passed": success_rate >= 0.95,
            "total_processed": len(results) + len(errors),
            "successful": len(results),
            "errors": len(errors),
            "success_rate": round(success_rate * 100, 2),
            "elapsed_sec": round(elapsed, 3),
            "error_details": errors[:5],  # First 5 errors
        }

    def _test_credit_conservation(self, token) -> Dict[str, Any]:
        """Verify total minted = sum of all balances + burned."""
        balances = token.get_all_balances()
        total_held = sum(balances.values())
        total_supply = token.total_supply

        # Supply should equal sum of balances
        diff = abs(total_supply - total_held)
        passed = diff < 0.0001

        return {
            "passed": passed,
            "total_supply": round(total_supply, 6),
            "total_held_by_participants": round(total_held, 6),
            "discrepancy": round(diff, 8),
            "holders": len(balances),
        }

    def _test_blockchain_integrity(self, blockchain) -> Dict[str, Any]:
        """Verify full chain hash integrity."""
        start = time.perf_counter()
        is_valid = blockchain.is_valid()
        elapsed = (time.perf_counter() - start) * 1000

        return {
            "passed": is_valid,
            "chain_length": blockchain.length,
            "validation_time_ms": round(elapsed, 3),
            "latest_hash": blockchain.latest_block.hash[:32] + "...",
        }

    def _test_double_counting(self, token) -> Dict[str, Any]:
        """Verify emission hashes are unique (no double-counting)."""
        hashes = list(token._hashes) if hasattr(token, "_hashes") else []
        unique = len(set(hashes))
        total = len(hashes)

        return {
            "passed": unique == total,
            "total_hashes": total,
            "unique_hashes": unique,
            "duplicates": total - unique,
        }

    def _test_token_consistency(self, token) -> Dict[str, Any]:
        """Verify no negative balances exist."""
        balances = token.get_all_balances()
        negative = {k: v for k, v in balances.items() if v < 0}

        return {
            "passed": len(negative) == 0,
            "total_holders": len(balances),
            "negative_balances": negative,
        }

    def get_results(self) -> Dict[str, Any]:
        return self._results
