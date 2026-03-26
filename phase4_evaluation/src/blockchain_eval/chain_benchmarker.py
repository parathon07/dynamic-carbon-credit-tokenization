"""
Blockchain Performance Benchmarker — Step 4.3
================================================
Measures transaction latency, throughput (TPS), mining efficiency,
and storage overhead for the simulated blockchain.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

import numpy as np

from src.config import (
    BENCH_BATCH_SIZES, DIFFICULTY_LEVELS,
    LATENCY_PERCENTILES, GAS_COST_PER_BLOCK, GAS_PRICE_GWEI,
)

logger = logging.getLogger("eval.chain_benchmarker")


class BlockchainBenchmarker:
    """
    Benchmarks the Phase 2 blockchain implementation.

    Measures:
      1. Transaction latency (add_block timing)
      2. Throughput (TPS) at various batch sizes
      3. Mining time vs difficulty level
      4. Chain validation time scaling
      5. Storage efficiency (bytes per transaction)
      6. Simulated gas cost model
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def benchmark_all(self, blockchain_class, block_data_factory) -> Dict[str, Any]:
        """
        Run full benchmark suite.

        Args:
            blockchain_class: The Blockchain class to instantiate.
            block_data_factory: Callable() returning a dict for block data.
        """
        results = {
            "latency": self._benchmark_latency(blockchain_class, block_data_factory),
            "throughput": self._benchmark_throughput(blockchain_class, block_data_factory),
            "difficulty_scaling": self._benchmark_difficulty(blockchain_class, block_data_factory),
            "validation_scaling": self._benchmark_validation(blockchain_class, block_data_factory),
            "storage_efficiency": self._benchmark_storage(blockchain_class, block_data_factory),
            "gas_cost": self._estimate_gas_costs(),
        }

        self._results = results
        return results

    def _benchmark_latency(self, bc_class, data_factory,
                           n_transactions: int = 100) -> Dict[str, Any]:
        """Measure per-transaction latency."""
        bc = bc_class(difficulty=2)
        latencies = []

        for _ in range(n_transactions):
            data = data_factory()
            start = time.perf_counter()
            bc.add_block(data)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)

        arr = np.array(latencies)
        percentiles = {
            f"p{p}": round(float(np.percentile(arr, p)), 3)
            for p in LATENCY_PERCENTILES
        }

        return {
            "n_transactions": n_transactions,
            "avg_ms": round(float(np.mean(arr)), 3),
            "std_ms": round(float(np.std(arr)), 3),
            "min_ms": round(float(np.min(arr)), 3),
            "max_ms": round(float(np.max(arr)), 3),
            "percentiles": percentiles,
            "_raw_latencies": arr.tolist(),
        }

    def _benchmark_throughput(self, bc_class, data_factory) -> Dict[str, Any]:
        """Measure TPS at different batch sizes."""
        tps_results = []

        for batch_size in BENCH_BATCH_SIZES:
            if batch_size > 500:
                continue  # Skip very large for speed
            bc = bc_class(difficulty=2)
            data_batch = [data_factory() for _ in range(batch_size)]

            start = time.perf_counter()
            for d in data_batch:
                bc.add_block(d)
            elapsed = time.perf_counter() - start

            tps = batch_size / max(elapsed, 1e-6)
            tps_results.append({
                "batch_size": batch_size,
                "elapsed_sec": round(elapsed, 3),
                "tps": round(tps, 2),
            })

        return {
            "batches": tps_results,
            "avg_tps": round(
                float(np.mean([r["tps"] for r in tps_results])), 2
            ) if tps_results else 0,
            "max_tps": round(
                float(max(r["tps"] for r in tps_results)), 2
            ) if tps_results else 0,
        }

    def _benchmark_difficulty(self, bc_class, data_factory,
                               n_per_level: int = 20) -> Dict[str, Any]:
        """Measure mining time at different difficulty levels."""
        diff_results = []

        for diff in DIFFICULTY_LEVELS:
            bc = bc_class(difficulty=diff)
            times = []
            for _ in range(n_per_level):
                data = data_factory()
                start = time.perf_counter()
                bc.add_block(data)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

            arr = np.array(times)
            diff_results.append({
                "difficulty": diff,
                "avg_ms": round(float(np.mean(arr)), 3),
                "std_ms": round(float(np.std(arr)), 3),
                "min_ms": round(float(np.min(arr)), 3),
                "max_ms": round(float(np.max(arr)), 3),
            })

        return {"levels": diff_results}

    def _benchmark_validation(self, bc_class, data_factory) -> Dict[str, Any]:
        """Measure chain validation time scaling."""
        val_results = []

        for chain_size in [10, 50, 100, 200, 500]:
            bc = bc_class(difficulty=1)
            for _ in range(chain_size):
                bc.add_block(data_factory())

            start = time.perf_counter()
            is_valid = bc.is_valid()
            elapsed = (time.perf_counter() - start) * 1000

            val_results.append({
                "chain_size": chain_size + 1,  # +1 for genesis
                "validation_ms": round(elapsed, 3),
                "is_valid": is_valid,
            })

        return {"results": val_results}

    def _benchmark_storage(self, bc_class, data_factory,
                           n_blocks: int = 100) -> Dict[str, Any]:
        """Estimate storage efficiency."""
        import json

        bc = bc_class(difficulty=1)
        for _ in range(n_blocks):
            bc.add_block(data_factory())

        chain_data = bc.get_chain()
        total_bytes = len(json.dumps(chain_data).encode("utf-8"))
        bytes_per_block = total_bytes / len(chain_data)

        return {
            "total_blocks": len(chain_data),
            "total_bytes": total_bytes,
            "bytes_per_block": round(bytes_per_block, 1),
            "kb_per_block": round(bytes_per_block / 1024, 3),
            "estimated_1000_blocks_mb": round((bytes_per_block * 1000) / (1024 * 1024), 2),
        }

    def _estimate_gas_costs(self) -> Dict[str, Any]:
        """Simulated Ethereum gas cost model."""
        gas_per_tx = GAS_COST_PER_BLOCK
        gwei_price = GAS_PRICE_GWEI
        eth_per_gwei = 1e-9

        cost_eth = gas_per_tx * gwei_price * eth_per_gwei
        eth_usd = 3000.0  # approximate
        cost_usd = cost_eth * eth_usd

        return {
            "gas_per_transaction": gas_per_tx,
            "gas_price_gwei": gwei_price,
            "cost_per_tx_eth": round(cost_eth, 6),
            "cost_per_tx_usd": round(cost_usd, 4),
            "cost_1000_tx_usd": round(cost_usd * 1000, 2),
            "note": "Simulated model based on Ethereum mainnet gas pricing",
        }

    def get_results(self) -> Dict[str, Any]:
        return self._results
