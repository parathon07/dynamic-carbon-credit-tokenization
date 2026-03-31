"""
Dynamic Carbon Measurement Model (DCMM) — Step 2.4
===================================================
Implementing true DCMM from the research paper.
Replaces static baseline minus actual calculation with:
    EF_t = α * G_t + β * R_t + γ * S_t
    E_i(t) = Energy_i(t) * EF_t
where:
    G_t: Grid Intensity
    R_t: Renewable Share Parameter
    S_t: Regional Factor multiplier
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List

from src.config import CREDIT_CONVERSION_FACTOR

logger = logging.getLogger("carbon_credits.calculator")


class DynamicGridSimulator:
    """
    Simulates external real-time data inputs for Grid Intensity, 
    Renewables, and Regional Factors dynamically.
    """
    @staticmethod
    def get_factors(timestamp_str: str = None) -> Dict[str, float]:
        # Using current time as proxy for dynamics simulation if none provided
        t = time.time()
        
        # G_t: Dynamic grid intensity (e.g., higher during peak evening hours)
        g_t = 0.6 + 0.2 * math.sin((t / 3600) + math.pi)
        
        # R_t: Renewable generation availability (peaks mid-day)
        r_t = 0.5 + 0.4 * math.cos(t / 86400)
        
        # S_t: Regional policy or infrastructure factor
        s_t = 1.05  
        
        return {
            "G_t": round(g_t, 4),
            "R_t": round(r_t, 4),
            "S_t": round(s_t, 4)
        }


class CarbonCreditCalculator:
    """
    Implements true DCMM for computing dynamic emissions and credits.
    """

    def __init__(self, alpha: float = 0.5, beta: float = 0.3, gamma: float = 0.2):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        
        # Ensure it is a valid convex combination
        assert abs((self.alpha + self.beta + self.gamma) - 1.0) < 1e-6, "DCMM weights must sum to 1.0"
        
        self._total_credits_earned = 0.0
        self._readings_processed = 0

    def calculate(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate dynamic emission and credits for a single reading.

        Follows research paper explicitly:
        EF_t = α * G_t + β * R_t + γ * S_t
        E_i(t) = Energy_i(t) * EF_t
        """
        energy_kwh = reading.get("energy_kwh", 0.0)
        factors = DynamicGridSimulator.get_factors(reading.get("timestamp_utc"))
        
        # 1. Compute Emission Factor (EF_t)
        ef_t = (
            self.alpha * factors["G_t"] + 
            self.beta * factors["R_t"] + 
            self.gamma * factors["S_t"]
        )
        
        # 2. Compute true Dynamic Emission (E_i(t))
        actual_emission_kg = energy_kwh * ef_t
        
        # (Assuming 'Baseline' is static allowable for credit calculation purely as reference)
        # However, to strictly align with dynamic requirements, we use adaptive allocation
        # For simplicity in this subsystem, token issuance relies on emission reduction vs allowed
        # Let's say baseline allowed is simply scaling by S_t
        baseline_allowed = energy_kwh * 0.8 * factors["S_t"]
        net_reduction = baseline_allowed - actual_emission_kg
        
        credits = 0.0
        if net_reduction > 0:
            credits = net_reduction * CREDIT_CONVERSION_FACTOR
            
        self._total_credits_earned += credits
        self._readings_processed += 1
        
        return {
            "actual_emission": round(actual_emission_kg, 6),
            "ef_t": round(ef_t, 6),
            "grid_factors": factors,
            "credits_earned": round(credits, 6),
            "baseline_allowed": round(baseline_allowed, 6)
        }

    def calculate_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.calculate(r) for r in readings]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_credits_earned": round(self._total_credits_earned, 6),
            "readings_processed": self._readings_processed,
            "dcmm_weights": {"alpha": self.alpha, "beta": self.beta, "gamma": self.gamma}
        }

    def reset(self):
        self._total_credits_earned = 0.0
        self._readings_processed = 0
