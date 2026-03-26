"""
Carbon Credit Calculator — Step 2.4
=====================================
Computes carbon credits based on emission reduction vs baseline.

Formula:
    net_credits = (baseline_emission - actual_emission) × conversion_factor
    credits_earned  = max(0, net_credits) × reward_multiplier
    credits_penalty = max(0, -net_credits) × penalty_multiplier
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.config import (
    CREDIT_CONVERSION_FACTOR,
    CREDIT_REWARD_MULTIPLIER,
    CREDIT_PENALTY_MULTIPLIER,
)
from src.carbon_credits.baselines import get_15s_baseline

logger = logging.getLogger("carbon_credits.calculator")


class CarbonCreditCalculator:
    """
    Calculates carbon credits earned or penalties incurred
    by comparing actual emissions against facility baselines.
    """

    def __init__(self):
        self._total_credits_earned = 0.0
        self._total_credits_penalty = 0.0
        self._readings_processed = 0

    def calculate(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate credits for a single reading.

        Args:
            reading: Must contain 'facility_type' and 'co2e_emission'.

        Returns:
            {credits_earned, credits_penalty, net_credits, baseline_emission,
             actual_emission, reduction_pct}
        """
        facility_type = reading["facility_type"]
        actual = reading["co2e_emission"]
        baseline = get_15s_baseline(facility_type)

        # Net reduction in kg CO₂e
        reduction_kg = baseline - actual

        # Convert to credits (1 credit = 1 tonne = 1000 kg)
        net_credits = reduction_kg * CREDIT_CONVERSION_FACTOR

        # Apply reward/penalty multipliers
        if net_credits >= 0:
            credits_earned = net_credits * CREDIT_REWARD_MULTIPLIER
            credits_penalty = 0.0
        else:
            credits_earned = 0.0
            credits_penalty = abs(net_credits) * CREDIT_PENALTY_MULTIPLIER

        # Track totals
        self._total_credits_earned += credits_earned
        self._total_credits_penalty += credits_penalty
        self._readings_processed += 1

        # Reduction percentage
        reduction_pct = (reduction_kg / (baseline + 1e-10)) * 100

        return {
            "credits_earned": round(credits_earned, 6),
            "credits_penalty": round(credits_penalty, 6),
            "net_credits": round(net_credits, 6),
            "baseline_emission": round(baseline, 6),
            "actual_emission": round(actual, 6),
            "reduction_pct": round(reduction_pct, 2),
        }

    def calculate_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate credits for a batch of readings."""
        return [self.calculate(r) for r in readings]

    def get_summary(self) -> Dict[str, Any]:
        """Return cumulative credit summary."""
        return {
            "total_credits_earned": round(self._total_credits_earned, 6),
            "total_credits_penalty": round(self._total_credits_penalty, 6),
            "net_balance": round(self._total_credits_earned - self._total_credits_penalty, 6),
            "readings_processed": self._readings_processed,
        }

    def reset(self):
        """Reset cumulative totals."""
        self._total_credits_earned = 0.0
        self._total_credits_penalty = 0.0
        self._readings_processed = 0
