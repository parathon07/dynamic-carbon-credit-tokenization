"""
Case Studies & Scenario Simulation — Step 4.7
===============================================
Simulates real-world scenarios (industrial plant, smart city, policy impact)
to demonstrate system behaviour under realistic conditions.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import (
    INDUSTRIAL_PLANT_FACILITIES, INDUSTRIAL_PLANT_READINGS,
    SMART_CITY_FACILITIES, SMART_CITY_READINGS,
)

logger = logging.getLogger("eval.scenario_runner")


class ScenarioRunner:
    """
    Executes pre-defined real-world scenarios and collects metrics.

    Scenarios:
      A. Industrial Plant — 5 high-emission facilities, 500 readings
      B. Smart City — 50 mixed facilities, 200 readings
      C. Policy Impact — Apply policies on Scenario A data
    """

    def __init__(self):
        self._results: Dict[str, Any] = {}

    def run_all(self, reading_generator, pipeline_processor,
                policy_simulator=None) -> Dict[str, Any]:
        """
        Run all case study scenarios.

        Args:
            reading_generator: Callable(n_fac, n_readings) -> List[Dict]
            pipeline_processor: Callable(readings) -> (results, token, bc)
            policy_simulator: Optional Phase 3 PolicySimulator instance.
        """
        results = {
            "scenario_a_industrial": self._run_industrial(
                reading_generator, pipeline_processor
            ),
            "scenario_b_smart_city": self._run_smart_city(
                reading_generator, pipeline_processor
            ),
        }

        if policy_simulator:
            results["scenario_c_policy_impact"] = self._run_policy_impact(
                policy_simulator, results["scenario_a_industrial"]
            )

        self._results = results
        return results

    def _run_industrial(self, generator, processor) -> Dict[str, Any]:
        """Scenario A: Industrial plant with high emissions."""
        n_fac = INDUSTRIAL_PLANT_FACILITIES
        n_read = INDUSTRIAL_PLANT_READINGS

        start = time.perf_counter()
        readings = generator(n_fac, n_read)
        results, token_supply, credits = processor(readings)
        elapsed = time.perf_counter() - start

        # Analyse results
        co2e_values = [r.get("co2e_emission", 0) for r in results if r]
        credit_values = [
            r.get("credits", {}).get("credits_earned", 0)
            for r in results if r and r.get("credits")
        ]
        anomaly_count = sum(
            1 for r in results if r and r.get("anomaly_flag")
        )

        # Per-facility emission trends
        facility_trends = {}
        for r in results:
            if not r:
                continue
            fid = r.get("facility_id", "unknown")
            if fid not in facility_trends:
                facility_trends[fid] = []
            facility_trends[fid].append(r.get("co2e_emission", 0))

        return {
            "scenario": "Industrial Plant",
            "facilities": n_fac,
            "readings_processed": len(results),
            "elapsed_sec": round(elapsed, 3),
            "emission_stats": {
                "total_co2e": round(sum(co2e_values), 2),
                "avg_co2e": round(float(np.mean(co2e_values)), 4) if co2e_values else 0,
                "std_co2e": round(float(np.std(co2e_values)), 4) if co2e_values else 0,
            },
            "credit_stats": {
                "total_earned": round(sum(credit_values), 6),
                "avg_per_reading": round(float(np.mean(credit_values)), 6) if credit_values else 0,
            },
            "anomalies_detected": anomaly_count,
            "token_supply": round(token_supply, 6),
            "facility_trends": {
                fid: {
                    "readings": len(vals),
                    "avg": round(float(np.mean(vals)), 4),
                    "trend": "decreasing" if len(vals) > 5 and vals[-1] < vals[0] else "stable",
                }
                for fid, vals in facility_trends.items()
            },
            "_plot_data": {
                "facility_emissions": {
                    fid: vals for fid, vals in facility_trends.items()
                },
            },
        }

    def _run_smart_city(self, generator, processor) -> Dict[str, Any]:
        """Scenario B: Smart city with diverse facility types."""
        n_fac = SMART_CITY_FACILITIES
        n_read = SMART_CITY_READINGS

        start = time.perf_counter()
        readings = generator(n_fac, n_read)
        results, token_supply, credits = processor(readings)
        elapsed = time.perf_counter() - start

        co2e_values = [r.get("co2e_emission", 0) for r in results if r]

        # Per-type analysis
        by_type: Dict[str, List[float]] = {}
        for r in results:
            if not r:
                continue
            ft = r.get("facility_type", "unknown")
            if ft not in by_type:
                by_type[ft] = []
            by_type[ft].append(r.get("co2e_emission", 0))

        type_summary = {
            ft: {
                "count": len(vals),
                "avg_co2e": round(float(np.mean(vals)), 4),
                "total_co2e": round(sum(vals), 2),
            }
            for ft, vals in by_type.items()
        }

        return {
            "scenario": "Smart City",
            "facilities": n_fac,
            "readings_processed": len(results),
            "elapsed_sec": round(elapsed, 3),
            "total_co2e": round(sum(co2e_values), 2),
            "avg_co2e": round(float(np.mean(co2e_values)), 4) if co2e_values else 0,
            "token_supply": round(token_supply, 6),
            "by_facility_type": type_summary,
        }

    def _run_policy_impact(self, policy_sim, industrial_results) -> Dict[str, Any]:
        """Scenario C: Policy impact on industrial scenario."""
        base_emissions = industrial_results.get("emission_stats", {}).get("total_co2e", 100)
        base_price = 25.0

        policy_sim.update_baseline(base_price, base_emissions, 50.0)

        scenarios = {
            "carbon_tax_low": policy_sim.simulate_carbon_tax(25.0),
            "carbon_tax_high": policy_sim.simulate_carbon_tax(100.0),
            "cap_tight": policy_sim.simulate_cap_and_trade(base_emissions * 0.7),
            "cap_loose": policy_sim.simulate_cap_and_trade(base_emissions * 1.3),
            "subsidy_moderate": policy_sim.simulate_subsidy(0.15),
            "subsidy_aggressive": policy_sim.simulate_subsidy(0.30),
        }

        # Summary
        summary = {}
        for name, result in scenarios.items():
            impact = result.get("impact", {})
            summary[name] = {
                "price_change_pct": impact.get("price_effect", {}).get("change_pct", 0),
                "emission_change_pct": impact.get("emission_effect", {}).get("change_pct", 0),
            }

        return {
            "scenario": "Policy Impact Analysis",
            "base_emissions": base_emissions,
            "base_price": base_price,
            "policy_results": summary,
            "detailed_results": scenarios,
        }

    def get_results(self) -> Dict[str, Any]:
        return self._results
