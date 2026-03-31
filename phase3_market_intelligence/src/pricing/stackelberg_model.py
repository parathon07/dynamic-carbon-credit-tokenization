"""
Stackelberg Leader-Follower Pricing — Step 3.2
================================================
Replaces elementary ARIMA / Supply-Demand pricing with a True 
Stackelberg Equilibrium Model implemented via SciPy optimization.

Leader (Regulator): Sets optimal price p* to hit target reductions.
Followers (Firms): React to price p* by minimizing individual cost.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger("pricing.stackelberg")


class StackelbergPricingModel:
    """
    Game theory mechanism where Regulator leads and Facilities follow.
    """
    
    def __init__(self, tolerance(float)=1e-6):
        self.tolerance = 1e-6
        self._price_history: List[float] = []

    def firm_optimal_emission(self, p: float, a_i: float, b_i: float) -> float:
        """
        Calculates optimal emission level E_i* for a single facility given price p.
        Cost Function modeled generally as: C_i(E_i) = a_i*(E_i)^2 - b_i*E_i + p*E_i
        (Where b_i represents revenue benefit from emitting/producing).
        """
        # SciPy minimization of Follower cost
        def cost(E):
            return a_i * (E[0]**2) - b_i * E[0] + p * E[0]

        # Firm emission must be >= 0
        res = minimize(cost, x0=[10.0], bounds=[(0.0, None)])
        return res.x[0]

    def solve_equilibrium_price(self, target_total_emission: float, 
                                firms_a: List[float], firms_b: List[float]) -> float:
        """
        Regulator (Leader) solves for optimal p* that induces followers
        to collectively emit exactly target_total_emission.
        """
        def regulator_objective(p_arr):
            p = p_arr[0]
            total_E = sum(self.firm_optimal_emission(p, a, b) 
                          for a, b in zip(firms_a, firms_b))
            
            # Leader wants distance between actual total E and target E to be minimized
            return (total_E - target_total_emission)**2

        # Regulator bounds the Carbon price between $1 and $500 per tonne
        res = minimize(regulator_objective, x0=[20.0], bounds=[(1.0, 500.0)])
        
        p_star = float(res.x[0])
        self._price_history.append(p_star)
        
        logger.info(f"Stackelberg Equilibrium Reached: p* = ${p_star:.2f}")
        return p_star

    def get_price_history(self) -> List[float]:
        return list(self._price_history)

    def current_price(self) -> float:
        return self._price_history[-1] if self._price_history else 20.0
