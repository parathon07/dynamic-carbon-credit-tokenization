"""
Market Analytics — Step 3.7
=============================
Advanced analytics dashboard providing market trends, price predictions,
emission forecasts, and credit flow visualisation data.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import ANALYTICS_REPORT_TOP_N, FACILITY_TYPES

logger = logging.getLogger("analytics.dashboard")


class MarketAnalytics:
    """
    Aggregates data from all Phase 3 components into structured reports.

    Report sections:
      1. Market overview (volume, value, participants)
      2. Price analytics (trends, predictions, volatility)
      3. Emission analytics (per-type, per-facility trends)
      4. Credit flow (minting, trading, burning)
      5. Participant leaderboard
    """

    def __init__(self):
        self._trade_data: List[Dict[str, Any]] = []
        self._emission_data: List[Dict[str, Any]] = []
        self._credit_mints: List[Dict[str, Any]] = []
        self._credit_burns: List[Dict[str, Any]] = []
        self._price_series: List[float] = []

    def record_trade(self, trade: Dict[str, Any]):
        self._trade_data.append(trade)
        price = trade.get("price_per_credit", trade.get("price", 0))
        if price > 0:
            self._price_series.append(price)

    def record_emission(self, reading: Dict[str, Any]):
        self._emission_data.append(reading)

    def record_mint(self, mint_data: Dict[str, Any]):
        self._credit_mints.append(mint_data)

    def record_burn(self, burn_data: Dict[str, Any]):
        self._credit_burns.append(burn_data)

    def generate_market_report(self) -> Dict[str, Any]:
        """Generate comprehensive market analytics report."""
        return {
            "market_overview": self._market_overview(),
            "price_analytics": self._price_analytics(),
            "emission_analytics": self._emission_analytics(),
            "credit_flow": self._credit_flow(),
            "participant_activity": self._participant_activity(),
        }

    def _market_overview(self) -> Dict[str, Any]:
        trades = self._trade_data
        if not trades:
            return {"total_trades": 0, "total_volume": 0, "total_value": 0}

        volumes = [t.get("credits_traded", t.get("amount", 0)) for t in trades]
        values = [t.get("total_value", 0) for t in trades]
        participants = set()
        for t in trades:
            participants.add(t.get("seller_id", t.get("seller", "")))
            participants.add(t.get("buyer_id", t.get("buyer", "")))
        participants.discard("")

        return {
            "total_trades": len(trades),
            "total_volume": round(sum(volumes), 4),
            "total_value": round(sum(values), 2),
            "avg_trade_size": round(float(np.mean(volumes)), 4) if volumes else 0,
            "unique_participants": len(participants),
        }

    def _price_analytics(self) -> Dict[str, Any]:
        prices = self._price_series
        if not prices:
            return {"current_price": 0, "avg_price": 0, "volatility": 0}

        arr = np.array(prices)
        returns = np.diff(arr) / arr[:-1] if len(arr) > 1 else np.array([0])

        return {
            "current_price": round(prices[-1], 2),
            "avg_price": round(float(np.mean(arr)), 2),
            "min_price": round(float(np.min(arr)), 2),
            "max_price": round(float(np.max(arr)), 2),
            "volatility": round(float(np.std(returns)), 4) if len(returns) > 0 else 0,
            "price_trend": "up" if len(prices) > 1 and prices[-1] > prices[0] else "down",
            "price_change_pct": round(
                ((prices[-1] - prices[0]) / (prices[0] + 1e-10)) * 100, 2
            ) if len(prices) > 1 else 0,
        }

    def _emission_analytics(self) -> Dict[str, Any]:
        if not self._emission_data:
            return {"total_readings": 0}

        by_type: Dict[str, List[float]] = defaultdict(list)
        total_co2e = []

        for r in self._emission_data:
            co2e = r.get("co2e_emission", 0)
            ft = r.get("facility_type", "unknown")
            if co2e > 0:
                by_type[ft].append(co2e)
                total_co2e.append(co2e)

        type_stats = {}
        for ft, vals in by_type.items():
            type_stats[ft] = {
                "readings": len(vals),
                "avg_co2e": round(float(np.mean(vals)), 4),
                "total_co2e": round(sum(vals), 2),
            }

        return {
            "total_readings": len(self._emission_data),
            "total_co2e": round(sum(total_co2e), 2) if total_co2e else 0,
            "avg_co2e": round(float(np.mean(total_co2e)), 4) if total_co2e else 0,
            "by_facility_type": type_stats,
        }

    def _credit_flow(self) -> Dict[str, Any]:
        total_minted = sum(m.get("amount", m.get("credits_earned", 0)) for m in self._credit_mints)
        total_burned = sum(b.get("amount", b.get("burned", 0)) for b in self._credit_burns)
        total_traded = sum(
            t.get("credits_traded", t.get("amount", 0)) for t in self._trade_data
        )

        return {
            "total_minted": round(total_minted, 4),
            "total_burned": round(total_burned, 4),
            "total_traded": round(total_traded, 4),
            "net_supply_change": round(total_minted - total_burned, 4),
            "mint_events": len(self._credit_mints),
            "burn_events": len(self._credit_burns),
        }

    def _participant_activity(self) -> Dict[str, Any]:
        buy_volume: Dict[str, float] = defaultdict(float)
        sell_volume: Dict[str, float] = defaultdict(float)

        for t in self._trade_data:
            buyer = t.get("buyer_id", t.get("buyer", ""))
            seller = t.get("seller_id", t.get("seller", ""))
            vol = t.get("credits_traded", t.get("amount", 0))
            if buyer:
                buy_volume[buyer] += vol
            if seller:
                sell_volume[seller] += vol

        # Top buyers
        top_buyers = sorted(buy_volume.items(), key=lambda x: -x[1])[:ANALYTICS_REPORT_TOP_N]
        top_sellers = sorted(sell_volume.items(), key=lambda x: -x[1])[:ANALYTICS_REPORT_TOP_N]

        return {
            "top_buyers": [{"participant": p, "volume": round(v, 4)} for p, v in top_buyers],
            "top_sellers": [{"participant": p, "volume": round(v, 4)} for p, v in top_sellers],
        }

    def get_price_forecast(self, horizon: int = 5) -> List[float]:
        """Simple exponential smoothing forecast."""
        if len(self._price_series) < 3:
            return [self._price_series[-1]] * horizon if self._price_series else [0] * horizon

        alpha = 0.3
        prices = self._price_series
        ema = prices[0]
        for p in prices[1:]:
            ema = alpha * p + (1 - alpha) * ema

        # Project forward with slight trend
        trend = (prices[-1] - prices[0]) / max(len(prices), 1)
        forecast = []
        for i in range(1, horizon + 1):
            forecast.append(round(ema + trend * i, 2))
        return forecast
