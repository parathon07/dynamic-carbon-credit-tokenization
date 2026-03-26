"""
Dashboard Monitor — Step 2.8
==============================
Real-time monitoring interface: tracks emissions, credits, anomalies,
blockchain transactions, and token balances.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class DashboardMonitor:
    """
    Tracks real-time system statistics and generates reports.

    Metrics tracked:
      - Per-facility emissions and credits
      - Anomaly alerts
      - Blockchain transaction count
      - Token balances
      - Pipeline throughput
    """

    def __init__(self):
        self._facility_emissions: Dict[str, List[float]] = defaultdict(list)
        self._facility_credits: Dict[str, float] = defaultdict(float)
        self._anomaly_alerts: List[Dict[str, Any]] = []
        self._blockchain_txs: int = 0
        self._total_processed: int = 0
        self._start_time: float = time.time()
        self._token_supply: float = 0.0

    def record_result(self, result: Dict[str, Any]):
        """Record a pipeline processing result."""
        fid = result.get("facility_id", "unknown")
        self._total_processed += 1

        # Track emissions
        co2e = result.get("co2e_emission")
        if co2e is not None:
            self._facility_emissions[fid].append(co2e)

        # Track credits
        credits = result.get("credits")
        if credits and isinstance(credits, dict):
            net = credits.get("net_credits", 0)
            self._facility_credits[fid] += net

        # Track anomalies
        if result.get("anomaly_flag"):
            self._anomaly_alerts.append({
                "facility_id": fid,
                "timestamp": result.get("timestamp_utc"),
                "type": result.get("anomaly_type"),
                "severity": result.get("severity_score"),
            })

        # Track blockchain
        if result.get("block_hash"):
            self._blockchain_txs += 1

        # Track tokens
        if result.get("token_minted"):
            earned = result.get("credits", {}).get("credits_earned", 0)
            self._token_supply += earned

    def generate_report(self) -> Dict[str, Any]:
        """Generate a formatted dashboard report."""
        elapsed = time.time() - self._start_time

        # Per-facility emission averages
        facility_stats = {}
        for fid, emissions in self._facility_emissions.items():
            facility_stats[fid] = {
                "avg_co2e": round(sum(emissions) / len(emissions), 4) if emissions else 0,
                "readings": len(emissions),
                "net_credits": round(self._facility_credits.get(fid, 0), 6),
            }

        return {
            "overview": {
                "total_processed": self._total_processed,
                "throughput_per_sec": round(
                    self._total_processed / (elapsed + 1e-8), 2,
                ),
                "elapsed_seconds": round(elapsed, 1),
                "blockchain_transactions": self._blockchain_txs,
                "total_token_supply": round(self._token_supply, 4),
            },
            "anomaly_summary": {
                "total_anomalies": len(self._anomaly_alerts),
                "recent_alerts": self._anomaly_alerts[-5:],
            },
            "facility_stats": facility_stats,
        }

    def get_anomaly_alerts(self, limit: int = 10) -> List[Dict]:
        """Return most recent anomaly alerts."""
        return self._anomaly_alerts[-limit:]

    def get_facility_ranking(self) -> List[Dict]:
        """Rank facilities by net credits (best performers first)."""
        ranking = [
            {"facility_id": fid, "net_credits": round(cred, 6)}
            for fid, cred in self._facility_credits.items()
        ]
        ranking.sort(key=lambda x: -x["net_credits"])
        return ranking
