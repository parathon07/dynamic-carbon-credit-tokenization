"""
Dynamic Pricing Engine — Step 3.2
====================================
AI-based carbon credit pricing using supply-demand dynamics,
ARIMA time-series forecasting, and volatility analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import (
    DEFAULT_CREDIT_PRICE, PRICING_LOOKBACK_WINDOW,
    SUPPLY_DEMAND_SENSITIVITY, ARIMA_ORDER,
    VOLATILITY_WINDOW, BASE_PRICE_FLOOR, BASE_PRICE_CEILING,
    FORECAST_HORIZON,
)
from src.pricing.market_signals import MarketSignalAggregator

logger = logging.getLogger("pricing.engine")


class DynamicPricingEngine:
    """
    AI-driven dynamic pricing for carbon credits.

    Methods:
      1. Supply-demand equilibrium pricing
      2. ARIMA time-series price forecasting
      3. Volatility index calculation
      4. Combined price recommendation

    Output:
      {current_price, predicted_price, volatility_index, supply, demand, confidence}
    """

    def __init__(self, base_price: float = DEFAULT_CREDIT_PRICE,
                 signal_aggregator: Optional[MarketSignalAggregator] = None):
        self._base_price = base_price
        self._current_price = base_price
        self._signals = signal_aggregator or MarketSignalAggregator()
        self._price_history: List[float] = [base_price]
        self._arima_fitted = False

    @property
    def current_price(self) -> float:
        return self._current_price

    @property
    def signal_aggregator(self) -> MarketSignalAggregator:
        return self._signals

    def update_price(self, supply: float, demand: float) -> Dict[str, Any]:
        """
        Recalculate price based on current supply-demand dynamics.

        Args:
            supply: Total available credit supply.
            demand: Current demand volume.

        Returns:
            Pricing update with current, predicted, and volatility.
        """
        self._signals.update_supply(supply)
        self._signals.record_demand(demand)

        # (1) Supply-demand model
        sd_ratio = supply / max(demand, 0.001)
        # Price adjusts inversely with supply-demand ratio
        # High supply / low demand → lower price; Low supply / high demand → higher price
        sd_factor = 1.0 / max(sd_ratio, 0.1)
        sd_price = self._base_price * (1.0 + SUPPLY_DEMAND_SENSITIVITY * (sd_factor - 1.0))

        # Clamp to floor/ceiling
        sd_price = max(BASE_PRICE_FLOOR, min(sd_price, BASE_PRICE_CEILING))

        # (2) ARIMA forecast (if enough history)
        predicted_price = self._arima_forecast()

        # (3) Volatility
        volatility = self._compute_volatility()

        # (4) Combined price: weighted blend of SD model and ARIMA
        if predicted_price is not None:
            combined = 0.6 * sd_price + 0.4 * predicted_price
        else:
            combined = sd_price

        combined = max(BASE_PRICE_FLOOR, min(combined, BASE_PRICE_CEILING))

        self._current_price = round(combined, 2)
        self._price_history.append(self._current_price)

        # Confidence based on data availability
        n_trades = len(self._signals.get_price_series())
        confidence = min(n_trades / PRICING_LOOKBACK_WINDOW, 1.0)

        return {
            "current_price": self._current_price,
            "predicted_price": round(predicted_price, 2) if predicted_price else self._current_price,
            "volatility_index": round(volatility, 4),
            "supply": round(supply, 4),
            "demand": round(demand, 4),
            "supply_demand_ratio": round(sd_ratio, 4),
            "confidence": round(confidence, 2),
        }

    def record_trade(self, price: float, volume: float):
        """Record a completed trade for price tracking."""
        self._signals.record_trade(price, volume)
        self._price_history.append(price)

    def _arima_forecast(self) -> Optional[float]:
        """
        ARIMA-based price forecast.
        Falls back to exponential moving average if statsmodels unavailable
        or insufficient data.
        """
        prices = self._price_history[-PRICING_LOOKBACK_WINDOW:]

        if len(prices) < 10:
            return None

        # Try statsmodels ARIMA
        try:
            from statsmodels.tsa.arima.model import ARIMA
            model = ARIMA(prices, order=ARIMA_ORDER)
            fitted = model.fit()
            forecast = fitted.forecast(steps=1)
            pred = float(forecast.iloc[0]) if hasattr(forecast, 'iloc') else float(forecast[0])
            return max(BASE_PRICE_FLOOR, min(pred, BASE_PRICE_CEILING))
        except Exception:
            pass

        # Fallback: exponential moving average
        alpha = 0.3
        ema = prices[0]
        for p in prices[1:]:
            ema = alpha * p + (1 - alpha) * ema
        return max(BASE_PRICE_FLOOR, min(ema, BASE_PRICE_CEILING))

    def _compute_volatility(self) -> float:
        """Compute price volatility as rolling std of returns."""
        prices = self._price_history[-VOLATILITY_WINDOW:]

        if len(prices) < 3:
            return 0.0

        arr = np.array(prices)
        returns = np.diff(arr) / arr[:-1]
        return float(np.std(returns))

    def get_price_history(self) -> List[float]:
        return list(self._price_history)

    def get_pricing_report(self) -> Dict[str, Any]:
        """Full pricing analytics report."""
        prices = self._price_history
        return {
            "current_price": self._current_price,
            "base_price": self._base_price,
            "price_history_length": len(prices),
            "price_min": round(min(prices), 2),
            "price_max": round(max(prices), 2),
            "price_avg": round(float(np.mean(prices)), 2),
            "volatility": round(self._compute_volatility(), 4),
            "price_floor": BASE_PRICE_FLOOR,
            "price_ceiling": BASE_PRICE_CEILING,
        }
