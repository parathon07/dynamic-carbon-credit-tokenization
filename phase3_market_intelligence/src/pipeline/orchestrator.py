"""
Phase 3 Pipeline Orchestrator — Step 3.9
==========================================
Integrates Phase 2 outputs (verified emissions, credits, tokens) into the
Phase 3 marketplace and intelligence layer.

Full loop:
  IoT Data → AI (Phase 2) → Credits → Marketplace (Phase 3) → Optimization → Feedback
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.marketplace.marketplace import CarbonMarketplace
from src.marketplace.wallet import Wallet
from src.pricing.pricing_engine import DynamicPricingEngine
from src.pricing.market_signals import MarketSignalAggregator
from src.trading.order_book import AdvancedOrderBook
from src.optimization.optimizer import EmissionOptimizer
from src.incentives.incentive_engine import IncentiveEngine
from src.risk.fraud_detector import FraudDetector
from src.analytics.analytics import MarketAnalytics
from src.policy.policy_simulator import PolicySimulator

logger = logging.getLogger("pipeline.phase3")


class Phase3Pipeline:
    """
    Orchestrates all Phase 3 components into a unified marketplace layer.

    Requires Phase 2 objects (Blockchain, CarbonToken) as inputs.
    """

    def __init__(self, token_manager, blockchain):
        """
        Args:
            token_manager: Phase 2 CarbonToken instance.
            blockchain: Phase 2 Blockchain instance.
        """
        self._token = token_manager
        self._chain = blockchain

        # Phase 3 components
        self.signal_aggregator = MarketSignalAggregator()
        self.pricing_engine = DynamicPricingEngine(
            signal_aggregator=self.signal_aggregator
        )
        self.marketplace = CarbonMarketplace(token_manager, blockchain)
        self.order_book = AdvancedOrderBook(
            token_manager, blockchain, self.pricing_engine
        )
        self.optimizer = EmissionOptimizer()
        self.incentives = IncentiveEngine(token_manager, blockchain)
        self.fraud_detector = FraudDetector()
        self.analytics = MarketAnalytics()
        self.policy_simulator = PolicySimulator()

        self._processed = 0
        self._start_time = time.time()

    def register_participants(self, participant_ids: List[str]):
        """Register facilities as marketplace participants."""
        for pid in participant_ids:
            self.marketplace.register_participant(pid, "facility")
            self.incentives.register_early_adopter(pid)

    def process_phase2_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest a Phase 2 pipeline result into Phase 3.

        This:
          1. Records emission data for optimisation
          2. Evaluates incentives/penalties
          3. Updates market signals
          4. Records analytics data
        """
        fid = result.get("facility_id", "unknown")

        # (1) Feed optimizer
        self.optimizer.record_reading(result)

        # (2) Evaluate incentives
        incentive_result = self.incentives.evaluate_reading(result)

        # (3) Update market signals
        co2e = result.get("co2e_emission", 0)
        ft = result.get("facility_type", "unknown")
        self.signal_aggregator.record_emission(ft, co2e)

        # (4) Analytics
        self.analytics.record_emission(result)
        if result.get("credits") and result["credits"].get("credits_earned", 0) > 0:
            self.analytics.record_mint({
                "facility_id": fid,
                "amount": result["credits"]["credits_earned"],
            })

        self._processed += 1
        return {
            "facility_id": fid,
            "incentive": incentive_result,
            "phase3_processed": True,
        }

    def process_phase2_batch(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of Phase 2 results."""
        return [self.process_phase2_result(r) for r in results]

    def run_marketplace_round(self, sellers: List[Dict], buyers: List[Dict]) -> List[Dict]:
        """
        Execute a round of marketplace trading.

        Args:
            sellers: [{participant_id, amount, price}]
            buyers: [{participant_id, amount, price}]
        """
        trades = []

        # Place sell orders
        for s in sellers:
            result = self.order_book.place_order(
                s["participant_id"], "sell", s["amount"], s["price"], "limit"
            )
            if result.get("matches"):
                trades.extend(result["matches"])

        # Place buy orders
        for b in buyers:
            result = self.order_book.place_order(
                b["participant_id"], "buy", b["amount"], b["price"], "limit"
            )
            if result.get("matches"):
                trades.extend(result["matches"])

        # Record trades for fraud detection and analytics
        for t in trades:
            self.fraud_detector.record_trade(t)
            self.analytics.record_trade(t)

        # Update pricing
        supply = self._token.total_supply
        demand = sum(b["amount"] for b in buyers)
        self.pricing_engine.update_price(supply, max(demand, 0.1))

        return trades

    def run_fraud_analysis(self) -> List[Dict]:
        """Run fraud detection on current market state."""
        balances = self._token.get_all_balances()
        return self.fraud_detector.analyse(balances, self._token.total_supply)

    def generate_recommendations(self, facility_id: str) -> List[Dict]:
        """Generate emission optimization recommendations."""
        self.optimizer.compute_benchmarks()
        return self.optimizer.generate_recommendations(facility_id)

    def run_policy_simulation(self) -> Dict[str, Any]:
        """Run standard policy simulations."""
        self.policy_simulator.update_baseline(
            price=self.pricing_engine.current_price,
            emissions=sum(
                r.get("co2e_emission", 0) for r in
                list(self.optimizer._facility_history.values())[0][-10:]
            ) if self.optimizer._facility_history else 100.0,
            supply=self._token.total_supply,
        )

        tax = self.policy_simulator.simulate_carbon_tax(50.0)
        cap = self.policy_simulator.simulate_cap_and_trade(800.0)
        sub = self.policy_simulator.simulate_subsidy(0.20)
        comparison = self.policy_simulator.compare_scenarios()

        return {
            "carbon_tax": tax,
            "cap_and_trade": cap,
            "subsidy": sub,
            "comparison": comparison,
        }

    def get_full_report(self) -> Dict[str, Any]:
        """Generate comprehensive Phase 3 report."""
        return {
            "pipeline_stats": {
                "readings_ingested": self._processed,
                "uptime_seconds": round(time.time() - self._start_time, 1),
            },
            "market_report": self.analytics.generate_market_report(),
            "pricing": self.pricing_engine.get_pricing_report(),
            "order_book": self.order_book.get_summary(),
            "optimizer": self.optimizer.get_summary(),
            "incentives": self.incentives.get_summary(),
            "fraud": self.fraud_detector.get_summary(),
            "policy": self.policy_simulator.get_summary(),
        }
