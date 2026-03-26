"""
Fraud & Risk Detection — Step 3.6
====================================
Detects market manipulation, fake transactions, credit hoarding,
and abnormal trading behaviours using statistical analysis.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.config import (
    WASH_TRADE_WINDOW_SEC, WASH_TRADE_MIN_TRADES,
    HOARDING_THRESHOLD_PCT, VELOCITY_SPIKE_ZSCORE,
    MIN_TRADE_HISTORY,
)

logger = logging.getLogger("risk.fraud_detector")


class FraudDetector:
    """
    Multi-method fraud and risk detection for the carbon credit market.

    Detection methods:
      1. Wash trading: repeated trades between the same pair in a short window
      2. Credit hoarding: single participant holds disproportionate supply
      3. Velocity anomaly: sudden spike in trade frequency
      4. Price manipulation: trades far from market price
      5. Self-dealing: circular trades that return tokens to origin

    Output per alert:
      {alert_type, severity, participants, details, timestamp}
    """

    def __init__(self):
        self._trade_log: List[Dict[str, Any]] = []
        self._pair_history: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._participant_velocity: Dict[str, List[float]] = defaultdict(list)
        self._alerts: List[Dict[str, Any]] = []
        self._price_history: List[float] = []

    def record_trade(self, trade: Dict[str, Any]):
        """Record a trade for fraud analysis."""
        self._trade_log.append(trade)

        seller = trade.get("seller_id", trade.get("seller", ""))
        buyer = trade.get("buyer_id", trade.get("buyer", ""))
        ts = trade.get("timestamp", 0.0)
        price = trade.get("price_per_credit", trade.get("price", 0.0))

        if seller and buyer:
            pair = tuple(sorted([seller, buyer]))
            self._pair_history[pair].append(ts)
            self._participant_velocity[seller].append(ts)
            self._participant_velocity[buyer].append(ts)

        if price > 0:
            self._price_history.append(price)

    def analyse(self, balances: Dict[str, float],
                total_supply: float = 0.0) -> List[Dict[str, Any]]:
        """
        Run all fraud detection methods.

        Args:
            balances: Current token balances {participant → balance}.
            total_supply: Total token supply.

        Returns:
            List of fraud alerts.
        """
        if len(self._trade_log) < MIN_TRADE_HISTORY:
            return []

        new_alerts = []

        # (1) Wash trading detection
        new_alerts.extend(self._detect_wash_trading())

        # (2) Credit hoarding detection
        if total_supply > 0:
            new_alerts.extend(self._detect_hoarding(balances, total_supply))

        # (3) Velocity spike detection
        new_alerts.extend(self._detect_velocity_spikes())

        # (4) Price manipulation detection
        new_alerts.extend(self._detect_price_manipulation())

        self._alerts.extend(new_alerts)
        return new_alerts

    def _detect_wash_trading(self) -> List[Dict[str, Any]]:
        """Detect repeated trades between the same pair in a short window."""
        alerts = []
        import time
        now = time.time()

        for pair, timestamps in self._pair_history.items():
            # Count trades in the detection window
            recent = [ts for ts in timestamps if now - ts < WASH_TRADE_WINDOW_SEC]
            if len(recent) >= WASH_TRADE_MIN_TRADES:
                severity = min(len(recent) / (WASH_TRADE_MIN_TRADES * 2), 1.0)
                alerts.append({
                    "alert_type": "wash_trading",
                    "severity": round(severity, 2),
                    "participants": list(pair),
                    "details": {
                        "trades_in_window": len(recent),
                        "window_seconds": WASH_TRADE_WINDOW_SEC,
                        "threshold": WASH_TRADE_MIN_TRADES,
                    },
                })
        return alerts

    def _detect_hoarding(self, balances: Dict[str, float],
                         total_supply: float) -> List[Dict[str, Any]]:
        """Detect participants holding disproportionate supply."""
        alerts = []
        threshold = HOARDING_THRESHOLD_PCT / 100.0

        for pid, balance in balances.items():
            pct = balance / max(total_supply, 0.001)
            if pct >= threshold:
                alerts.append({
                    "alert_type": "credit_hoarding",
                    "severity": round(min(pct / threshold, 1.0), 2),
                    "participants": [pid],
                    "details": {
                        "balance": round(balance, 4),
                        "supply_percentage": round(pct * 100, 2),
                        "threshold_pct": HOARDING_THRESHOLD_PCT,
                    },
                })
        return alerts

    def _detect_velocity_spikes(self) -> List[Dict[str, Any]]:
        """Detect sudden spikes in trade frequency for a participant."""
        alerts = []
        import time
        now = time.time()

        for pid, timestamps in self._participant_velocity.items():
            if len(timestamps) < 5:
                continue

            # Calculate inter-trade intervals
            sorted_ts = sorted(timestamps)
            intervals = np.diff(sorted_ts)

            if len(intervals) < 3:
                continue

            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals) + 1e-10

            # Check if the most recent interval is anomalously short
            latest_interval = now - sorted_ts[-1]
            z_score = (mean_interval - latest_interval) / std_interval

            if z_score > VELOCITY_SPIKE_ZSCORE:
                alerts.append({
                    "alert_type": "velocity_spike",
                    "severity": round(min(z_score / (VELOCITY_SPIKE_ZSCORE * 2), 1.0), 2),
                    "participants": [pid],
                    "details": {
                        "z_score": round(z_score, 2),
                        "mean_interval_sec": round(mean_interval, 1),
                        "latest_interval_sec": round(latest_interval, 1),
                    },
                })
        return alerts

    def _detect_price_manipulation(self) -> List[Dict[str, Any]]:
        """Detect trades at prices far from market average."""
        alerts = []

        if len(self._price_history) < 10:
            return alerts

        prices = np.array(self._price_history)
        mean_price = np.mean(prices)
        std_price = np.std(prices) + 1e-10

        # Check last 5 trades
        for trade in self._trade_log[-5:]:
            price = trade.get("price_per_credit", trade.get("price", 0))
            if price <= 0:
                continue
            z = abs(price - mean_price) / std_price
            if z > 3.0:
                seller = trade.get("seller_id", trade.get("seller", "unknown"))
                buyer = trade.get("buyer_id", trade.get("buyer", "unknown"))
                alerts.append({
                    "alert_type": "price_manipulation",
                    "severity": round(min(z / 6.0, 1.0), 2),
                    "participants": [seller, buyer],
                    "details": {
                        "trade_price": round(price, 2),
                        "market_avg": round(mean_price, 2),
                        "z_score": round(z, 2),
                    },
                })
        return alerts

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._alerts[-limit:]

    def get_risk_score(self, participant_id: str) -> float:
        """Calculate aggregate risk score (0-1) for a participant."""
        relevant = [
            a for a in self._alerts
            if participant_id in a.get("participants", [])
        ]
        if not relevant:
            return 0.0
        return min(
            sum(a["severity"] for a in relevant) / len(relevant),
            1.0,
        )

    def get_summary(self) -> Dict[str, Any]:
        type_counts = defaultdict(int)
        for a in self._alerts:
            type_counts[a["alert_type"]] += 1
        return {
            "total_trades_analysed": len(self._trade_log),
            "total_alerts": len(self._alerts),
            "alert_types": dict(type_counts),
            "unique_pairs_monitored": len(self._pair_history),
        }
