"""
Market Signal Aggregator — Step 3.2
=====================================
Collects supply, demand, emission intensity, and trade volume signals
to feed into the dynamic pricing engine.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np


class MarketSignalAggregator:
    """
    Aggregates market signals for pricing decisions.

    Tracked signals:
      - Available credit supply (total tokens minus locked in orders)
      - Market demand (pending buy orders / recent buy volume)
      - Average emission intensity across facilities
      - Trade volume and velocity
      - Price history
    """

    def __init__(self):
        self._price_history: List[float] = []
        self._volume_history: List[float] = []
        self._trade_timestamps: List[float] = []
        self._emission_data: Dict[str, List[float]] = defaultdict(list)
        self._supply_snapshots: List[float] = []
        self._demand_signals: List[float] = []

    def record_trade(self, price: float, volume: float):
        """Record a completed trade."""
        self._price_history.append(price)
        self._volume_history.append(volume)
        self._trade_timestamps.append(time.time())

    def record_emission(self, facility_type: str, co2e: float):
        """Record an emission observation."""
        self._emission_data[facility_type].append(co2e)

    def update_supply(self, total_supply: float):
        """Snapshot current credit supply."""
        self._supply_snapshots.append(total_supply)

    def record_demand(self, demand_volume: float):
        """Record a demand signal (e.g. pending buy volume)."""
        self._demand_signals.append(demand_volume)

    def get_current_signals(self) -> Dict[str, Any]:
        """Return current aggregated market signals."""
        prices = self._price_history or [0.0]
        volumes = self._volume_history or [0.0]

        # Supply-demand ratio
        supply = self._supply_snapshots[-1] if self._supply_snapshots else 1.0
        demand = self._demand_signals[-1] if self._demand_signals else 1.0
        sd_ratio = supply / max(demand, 0.001)

        # Trade velocity (trades per minute, last 10 trades)
        recent_ts = self._trade_timestamps[-10:]
        if len(recent_ts) >= 2:
            elapsed = recent_ts[-1] - recent_ts[0]
            velocity = len(recent_ts) / max(elapsed / 60.0, 0.001)
        else:
            velocity = 0.0

        # Emission intensity
        avg_emission = {}
        for ft, vals in self._emission_data.items():
            if vals:
                avg_emission[ft] = round(float(np.mean(vals[-50:])), 4)

        return {
            "last_price": prices[-1],
            "avg_price": round(float(np.mean(prices[-20:])), 4),
            "price_trend": round(float(np.mean(np.diff(prices[-20:]))) if len(prices) > 1 else 0.0, 6),
            "total_volume": round(sum(volumes), 4),
            "recent_volume": round(sum(volumes[-20:]), 4),
            "supply_demand_ratio": round(sd_ratio, 4),
            "trade_velocity": round(velocity, 2),
            "total_trades": len(self._price_history),
            "avg_emission_intensity": avg_emission,
        }

    def get_price_series(self) -> List[float]:
        return list(self._price_history)

    def get_volume_series(self) -> List[float]:
        return list(self._volume_history)
