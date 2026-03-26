"""
Policy & Regulatory Simulator — Step 3.8
===========================================
Simulates carbon tax changes, cap-and-trade policies, and clean energy
subsidies to model their impact on prices, emissions, and market activity.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import (
    DEFAULT_CARBON_TAX_RATE, TAX_RATE_RANGE,
    CAP_AND_TRADE_DEFAULT_CAP, SUBSIDY_RATE_CLEAN_ENERGY,
    FACILITY_TYPES,
)

logger = logging.getLogger("policy.simulator")


class PolicySimulator:
    """
    Simulates regulatory policy changes and their market impact.

    Supported policies:
      1. Carbon tax: flat $/tonne tax on emissions
      2. Cap-and-trade: total emission cap with tradable allowances
      3. Clean energy subsidy: cost reduction for clean energy adoption
      4. Combined scenarios: multiple policies applied together

    Output per scenario:
      {policy_name, parameters, impact: {price_effect, emission_effect, market_effect}}
    """

    def __init__(self, current_price: float = 25.0, current_emissions: float = 100.0,
                 current_supply: float = 50.0):
        self._base_price = current_price
        self._base_emissions = current_emissions
        self._base_supply = current_supply
        self._scenarios: List[Dict[str, Any]] = []

    def update_baseline(self, price: float, emissions: float, supply: float):
        """Update baseline values from live market data."""
        self._base_price = price
        self._base_emissions = emissions
        self._base_supply = supply

    def simulate_carbon_tax(self, tax_rate: float = DEFAULT_CARBON_TAX_RATE) -> Dict[str, Any]:
        """
        Simulate effect of a carbon tax.

        A higher carbon tax increases the cost of emitting, which:
          - Raises credit prices (emissions have higher cost)
          - Reduces emissions (incentivises reduction)
          - Increases market activity (more trading to optimise costs)
        """
        tax_rate = max(TAX_RATE_RANGE[0], min(tax_rate, TAX_RATE_RANGE[1]))

        # Price effect: tax directly increases marginal cost of emissions
        price_increase_pct = (tax_rate / 100.0) * 40  # 40% sensitivity at $100 tax
        new_price = self._base_price * (1 + price_increase_pct / 100)

        # Emission reduction: higher tax → stronger incentive to cut emissions
        emission_elasticity = -0.3  # 10% tax increase → 3% emission decrease
        tax_multiplier = tax_rate / DEFAULT_CARBON_TAX_RATE
        emission_change_pct = emission_elasticity * (tax_multiplier - 1) * 100
        new_emissions = self._base_emissions * (1 + emission_change_pct / 100)

        # Market activity increase
        activity_boost_pct = min(tax_rate / DEFAULT_CARBON_TAX_RATE * 15, 50)

        result = {
            "policy": "carbon_tax",
            "parameters": {"tax_rate": tax_rate, "unit": "$/tonne CO₂e"},
            "impact": {
                "price_effect": {
                    "baseline": round(self._base_price, 2),
                    "projected": round(new_price, 2),
                    "change_pct": round(price_increase_pct, 2),
                },
                "emission_effect": {
                    "baseline": round(self._base_emissions, 2),
                    "projected": round(max(new_emissions, 0), 2),
                    "change_pct": round(emission_change_pct, 2),
                },
                "market_effect": {
                    "activity_change_pct": round(activity_boost_pct, 2),
                    "expected_trading_increase": True,
                },
            },
        }
        self._scenarios.append(result)
        return result

    def simulate_cap_and_trade(self, cap: float = CAP_AND_TRADE_DEFAULT_CAP) -> Dict[str, Any]:
        """
        Simulate cap-and-trade policy.

        A lower cap means fewer allowances → higher credit prices.
        """
        cap_ratio = cap / max(self._base_emissions, 1)

        if cap_ratio < 1.0:
            # Cap below current emissions → prices rise
            scarcity = 1.0 / max(cap_ratio, 0.1)
            price_effect_pct = (scarcity - 1) * 50
            emission_effect_pct = -(1 - cap_ratio) * 80  # forced reduction
        else:
            # Cap above current → prices fall
            price_effect_pct = -(cap_ratio - 1) * 20
            emission_effect_pct = 0  # no pressure to reduce

        new_price = self._base_price * (1 + price_effect_pct / 100)
        new_emissions = self._base_emissions * (1 + emission_effect_pct / 100)

        # Supply effect: cap limits total credits
        supply_change = cap - self._base_supply

        result = {
            "policy": "cap_and_trade",
            "parameters": {"cap": cap, "unit": "tonnes CO₂e"},
            "impact": {
                "price_effect": {
                    "baseline": round(self._base_price, 2),
                    "projected": round(max(new_price, 1.0), 2),
                    "change_pct": round(price_effect_pct, 2),
                },
                "emission_effect": {
                    "baseline": round(self._base_emissions, 2),
                    "projected": round(max(new_emissions, 0), 2),
                    "change_pct": round(emission_effect_pct, 2),
                },
                "market_effect": {
                    "supply_change": round(supply_change, 2),
                    "cap_binding": cap_ratio < 1.0,
                },
            },
        }
        self._scenarios.append(result)
        return result

    def simulate_subsidy(self, subsidy_rate: float = SUBSIDY_RATE_CLEAN_ENERGY) -> Dict[str, Any]:
        """
        Simulate clean energy subsidy.

        Subsidies reduce cost of adopting clean technology, leading to:
          - Lower emissions (faster transition)
          - Moderate price decrease (more supply of credits)
        """
        subsidy_pct = subsidy_rate * 100

        # Emission reduction from faster clean tech adoption
        emission_reduction_pct = subsidy_pct * 0.6  # 20% subsidy → 12% emission cut
        new_emissions = self._base_emissions * (1 - emission_reduction_pct / 100)

        # Price effect: more supply from lower emissions → slight price decrease
        price_change_pct = -subsidy_pct * 0.2
        new_price = self._base_price * (1 + price_change_pct / 100)

        result = {
            "policy": "clean_energy_subsidy",
            "parameters": {"subsidy_rate": subsidy_rate, "subsidy_pct": subsidy_pct},
            "impact": {
                "price_effect": {
                    "baseline": round(self._base_price, 2),
                    "projected": round(max(new_price, 1.0), 2),
                    "change_pct": round(price_change_pct, 2),
                },
                "emission_effect": {
                    "baseline": round(self._base_emissions, 2),
                    "projected": round(max(new_emissions, 0), 2),
                    "change_pct": round(-emission_reduction_pct, 2),
                },
                "market_effect": {
                    "adoption_incentive": f"{subsidy_pct:.0f}% cost reduction",
                },
            },
        }
        self._scenarios.append(result)
        return result

    def compare_scenarios(self, scenarios: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Compare multiple policy scenarios side by side."""
        scenarios = scenarios or self._scenarios

        if not scenarios:
            return {"status": "no scenarios to compare"}

        comparison = []
        for sc in scenarios:
            impact = sc["impact"]
            comparison.append({
                "policy": sc["policy"],
                "price_change": impact["price_effect"]["change_pct"],
                "emission_change": impact["emission_effect"]["change_pct"],
                "projected_price": impact["price_effect"]["projected"],
                "projected_emissions": impact["emission_effect"]["projected"],
            })

        # Determine best policy by emission reduction
        best_for_emissions = min(comparison, key=lambda x: x["emission_change"])
        best_for_price = min(comparison, key=lambda x: abs(x["price_change"]))

        return {
            "scenarios": comparison,
            "best_for_emissions": best_for_emissions["policy"],
            "best_for_price_stability": best_for_price["policy"],
        }

    def get_all_scenarios(self) -> List[Dict[str, Any]]:
        return list(self._scenarios)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "scenarios_simulated": len(self._scenarios),
            "baseline_price": self._base_price,
            "baseline_emissions": self._base_emissions,
            "baseline_supply": self._base_supply,
        }
