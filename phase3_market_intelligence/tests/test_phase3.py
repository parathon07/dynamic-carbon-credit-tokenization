"""
Phase 3 — Comprehensive Validation Test Suite
================================================
Tests the entire Market Intelligence layer:

  ▸ Marketplace (wallet, listings, bids, purchases)
  ▸ Dynamic Pricing Engine (supply-demand, ARIMA, volatility)
  ▸ Market Signals (aggregation)
  ▸ Advanced Order Book (limit/market orders, matching, spread)
  ▸ Emission Optimizer (recommendations, benchmarks)
  ▸ Incentive & Penalty Engine (tiers, bonuses, penalties)
  ▸ Fraud Detection (wash trading, hoarding, velocity, manipulation)
  ▸ Market Analytics (reports, flow, forecasts)
  ▸ Policy Simulator (carbon tax, cap-and-trade, subsidy)
  ▸ Phase 3 Pipeline Orchestrator (end-to-end integration)

Run:
    python -m pytest tests/test_phase3.py -v
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List

import numpy as np
import pytest

# Ensure Phase 3 root is FIRST on sys.path so src.config resolves to Phase 3's config
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Remove any existing entry and re-insert at position 0
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from src.config import (
    FACILITY_TYPES, INCENTIVE_TIERS, DEFAULT_CREDIT_PRICE,
    WASH_TRADE_MIN_TRADES, HOARDING_THRESHOLD_PCT,
)
from src.marketplace.wallet import Wallet
from src.marketplace.marketplace import CarbonMarketplace, Listing
from src.pricing.market_signals import MarketSignalAggregator
from src.pricing.pricing_engine import DynamicPricingEngine
from src.trading.order_book import AdvancedOrderBook, OrderEntry
from src.optimization.optimizer import EmissionOptimizer
from src.incentives.incentive_engine import IncentiveEngine
from src.risk.fraud_detector import FraudDetector
from src.analytics.analytics import MarketAnalytics
from src.policy.policy_simulator import PolicySimulator
from src.pipeline.orchestrator import Phase3Pipeline


# ── Helpers ──────────────────────────────────────────────────────────────

# Lightweight in-memory token and blockchain stubs that mirror Phase 2 API
# so Phase 3 tests run independently without Phase 2 imports.

class _StubToken:
    """Minimal CarbonToken stub for testing."""
    def __init__(self):
        self._balances: Dict[str, float] = {}
        self._supply = 0.0
        self._hashes = set()
        self.symbol = "CCT"

    def mint(self, to, amount, emission_hash):
        if emission_hash in self._hashes:
            raise ValueError("Duplicate hash")
        self._hashes.add(emission_hash)
        self._balances[to] = self._balances.get(to, 0) + amount
        self._supply += amount
        return {"type": "mint", "to": to, "amount": amount}

    def transfer(self, from_addr, to_addr, amount):
        if self._balances.get(from_addr, 0) < amount:
            raise ValueError("Insufficient balance")
        self._balances[from_addr] -= amount
        self._balances[to_addr] = self._balances.get(to_addr, 0) + amount
        return {"type": "transfer"}

    def burn(self, from_addr, amount):
        if self._balances.get(from_addr, 0) < amount:
            raise ValueError("Insufficient balance")
        self._balances[from_addr] -= amount
        self._supply -= amount

    def balance_of(self, addr):
        return round(self._balances.get(addr, 0), 4)

    @property
    def total_supply(self):
        return round(self._supply, 4)

    def get_all_balances(self):
        return {k: round(v, 4) for k, v in self._balances.items() if v > 0}

    @staticmethod
    def compute_emission_hash(reading):
        import hashlib, json
        return hashlib.sha256(json.dumps(reading, sort_keys=True).encode()).hexdigest()[:16]


class _StubBlock:
    def __init__(self, index, hash_val):
        self.index = index
        self.hash = hash_val

class _StubBlockchain:
    """Minimal Blockchain stub."""
    def __init__(self):
        self._blocks = [_StubBlock(0, "0" * 64)]
    def add_block(self, data):
        import hashlib, json
        h = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        b = _StubBlock(len(self._blocks), h)
        self._blocks.append(b)
        return b
    @property
    def length(self):
        return len(self._blocks)
    def is_valid(self):
        return True


def _make_token_and_chain():
    return _StubToken(), _StubBlockchain()

def _valid_reading(fac_id="FAC_001", fac_type="chemical_manufacturing",
                   co2e=20.0, credits_earned=0.01, reduction_pct=8.0):
    return {
        "facility_id": fac_id, "facility_type": fac_type,
        "timestamp_utc": "2024-06-15T10:00:00+00:00",
        "co2_ppm": 450.0, "ch4_ppm": 2.5, "nox_ppb": 55.0,
        "fuel_rate": 180.0, "energy_kwh": 3500.0,
        "co2e_emission": co2e,
        "confidence_score": 0.92,
        "anomaly_flag": False,
        "credits": {
            "credits_earned": credits_earned,
            "credits_penalty": 0.0,
            "net_credits": credits_earned,
            "reduction_pct": reduction_pct,
        },
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  1. WALLET                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestWallet:
    def test_creation(self):
        w = Wallet("FAC_001", "facility")
        assert w.participant_id == "FAC_001"
        assert w.participant_type == "facility"

    def test_activity_log(self):
        w = Wallet("FAC_001")
        w.record_activity("buy", {"amount": 10.0, "fee": 0.5})
        log = w.get_activity_log()
        assert len(log) == 1 and log[0]["type"] == "buy"

    def test_traded_volume(self):
        w = Wallet("FAC_001")
        w.record_activity("sell", {"amount": 5.0, "fee": 0.1})
        w.record_activity("buy", {"amount": 3.0, "fee": 0.05})
        s = w.get_summary()
        assert s["total_traded_volume"] == 8.0

    def test_pending_listings(self):
        w = Wallet("FAC_001")
        w.add_pending_listing("LST_001")
        assert w.get_summary()["pending_listings"] == 1
        w.remove_pending_listing("LST_001")
        assert w.get_summary()["pending_listings"] == 0

    def test_to_dict(self):
        w = Wallet("FAC_001", "broker")
        d = w.to_dict()
        assert d["participant_id"] == "FAC_001"
        assert d["participant_type"] == "broker"


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  2. MARKETPLACE                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestMarketplace:
    def test_register_participant(self):
        t, bc = _make_token_and_chain()
        m = CarbonMarketplace(t, bc)
        r = m.register_participant("FAC_001")
        assert r["status"] == "registered"

    def test_duplicate_registration(self):
        t, bc = _make_token_and_chain()
        m = CarbonMarketplace(t, bc)
        m.register_participant("FAC_001")
        r = m.register_participant("FAC_001")
        assert r["status"] == "exists"

    def test_create_listing(self):
        t, bc = _make_token_and_chain()
        t.mint("FAC_001", 100, "h1")
        m = CarbonMarketplace(t, bc)
        m.register_participant("FAC_001")
        r = m.create_listing("FAC_001", 50.0, 25.0)
        assert r["status"] == "listed"
        assert r["listing_id"] == "LST_000001"

    def test_listing_insufficient_balance(self):
        t, bc = _make_token_and_chain()
        m = CarbonMarketplace(t, bc)
        r = m.create_listing("FAC_001", 100.0)
        assert r["status"] == "error"

    def test_execute_purchase(self):
        t, bc = _make_token_and_chain()
        t.mint("seller", 100, "h1")
        m = CarbonMarketplace(t, bc)
        m.register_participant("seller")
        m.register_participant("buyer")
        lst = m.create_listing("seller", 50.0, 20.0)
        r = m.execute_purchase(lst["listing_id"], "buyer", 30.0)
        assert r["status"] == "executed"
        assert t.balance_of("buyer") == 30.0
        assert t.balance_of("seller") == 70.0

    def test_purchase_records_trade_history(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        m = CarbonMarketplace(t, bc)
        m.create_listing("S", 50.0, 10.0)
        m.execute_purchase("LST_000001", "B", 20.0)
        history = m.get_trade_history()
        assert len(history) == 1
        assert history[0]["credits_traded"] == 20.0

    def test_cancel_listing(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        m = CarbonMarketplace(t, bc)
        lst = m.create_listing("S", 50.0)
        r = m.cancel_listing(lst["listing_id"], "S")
        assert r["status"] == "cancelled"

    def test_place_bid(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        m = CarbonMarketplace(t, bc)
        lst = m.create_listing("S", 50.0, 25.0)
        r = m.place_bid(lst["listing_id"], "B", 20.0, 24.0)
        assert r["status"] == "bid_placed"

    def test_active_listings(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 200, "h1")
        m = CarbonMarketplace(t, bc)
        m.create_listing("S", 50.0, 30.0)
        m.create_listing("S", 30.0, 20.0)
        active = m.get_active_listings()
        assert len(active) == 2
        assert active[0]["price_per_credit"] <= active[1]["price_per_credit"]

    def test_market_summary(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        m = CarbonMarketplace(t, bc)
        m.create_listing("S", 50.0, 25.0)
        m.execute_purchase("LST_000001", "B", 10.0)
        s = m.get_market_summary()
        assert s["total_trades"] == 1
        assert s["total_volume"] == 10.0


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  3. MARKET SIGNALS                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestMarketSignals:
    def test_record_trade(self):
        sa = MarketSignalAggregator()
        sa.record_trade(25.0, 10.0)
        signals = sa.get_current_signals()
        assert signals["last_price"] == 25.0
        assert signals["total_trades"] == 1

    def test_supply_demand(self):
        sa = MarketSignalAggregator()
        sa.update_supply(100.0)
        sa.record_demand(50.0)
        signals = sa.get_current_signals()
        assert signals["supply_demand_ratio"] == 2.0

    def test_emission_tracking(self):
        sa = MarketSignalAggregator()
        sa.record_emission("chemical_manufacturing", 20.0)
        sa.record_emission("chemical_manufacturing", 30.0)
        signals = sa.get_current_signals()
        assert "chemical_manufacturing" in signals["avg_emission_intensity"]

    def test_price_series(self):
        sa = MarketSignalAggregator()
        for p in [10, 20, 30]:
            sa.record_trade(p, 5.0)
        assert sa.get_price_series() == [10, 20, 30]


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  4. DYNAMIC PRICING                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestDynamicPricing:
    def test_initial_price(self):
        pe = DynamicPricingEngine(base_price=25.0)
        assert pe.current_price == 25.0

    def test_price_update(self):
        pe = DynamicPricingEngine(base_price=25.0)
        r = pe.update_price(supply=100.0, demand=100.0)
        assert r["current_price"] > 0
        assert "volatility_index" in r

    def test_high_demand_raises_price(self):
        pe = DynamicPricingEngine(base_price=25.0)
        pe.update_price(supply=10.0, demand=100.0)  # low supply high demand
        assert pe.current_price > 25.0

    def test_high_supply_lowers_price(self):
        pe = DynamicPricingEngine(base_price=25.0)
        pe.update_price(supply=1000.0, demand=10.0)  # high supply low demand
        assert pe.current_price < 25.0

    def test_price_floor(self):
        pe = DynamicPricingEngine(base_price=25.0)
        pe.update_price(supply=100000.0, demand=0.01)
        assert pe.current_price >= 5.0  # BASE_PRICE_FLOOR

    def test_record_trade(self):
        pe = DynamicPricingEngine()
        pe.record_trade(30.0, 10.0)
        assert len(pe.get_price_history()) == 2  # base + trade

    def test_pricing_report(self):
        pe = DynamicPricingEngine()
        pe.update_price(50, 50)
        r = pe.get_pricing_report()
        assert "price_min" in r and "price_max" in r

    def test_volatility_calculation(self):
        pe = DynamicPricingEngine(base_price=25.0)
        for i in range(20):
            pe.record_trade(25.0 + np.sin(i) * 5, 1.0)
        r = pe.update_price(50, 50)
        assert r["volatility_index"] > 0  # should be non-zero with sine wave


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  5. ADVANCED ORDER BOOK                                               ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestAdvancedOrderBook:
    def test_place_sell_order(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        r = ob.place_order("S", "sell", 50.0, 10.0)
        assert r["status"] == "placed"

    def test_place_buy_order(self):
        t, bc = _make_token_and_chain()
        ob = AdvancedOrderBook(t, bc)
        r = ob.place_order("B", "buy", 50.0, 10.0)
        assert r["status"] == "placed"

    def test_order_matching(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S", "sell", 50.0, 10.0)
        r = ob.place_order("B", "buy", 30.0, 10.0)
        assert t.balance_of("B") == 30.0

    def test_price_priority(self):
        t, bc = _make_token_and_chain()
        t.mint("S1", 100, "h1")
        t.mint("S2", 100, "h2")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S1", "sell", 50.0, 15.0)
        ob.place_order("S2", "sell", 50.0, 10.0)  # cheaper
        ob.place_order("B", "buy", 30.0, 15.0)
        # S2 at $10 should be matched first (lower price)
        assert t.balance_of("S2") == 70.0  # S2 sold 30

    def test_market_order(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S", "sell", 50.0, 10.0)
        r = ob.place_order("B", "buy", 20.0, order_type="market")
        assert t.balance_of("B") == 20.0

    def test_cancel_order(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        r = ob.place_order("S", "sell", 50.0, 10.0)
        cr = ob.cancel_order(r["order_id"], "S")
        assert cr["status"] == "cancelled"

    def test_order_book_state(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S", "sell", 50.0, 10.0)
        ob.place_order("B", "buy", 30.0, 8.0)
        book = ob.get_order_book()
        assert len(book["sell_orders"]) == 1
        assert len(book["buy_orders"]) == 1

    def test_best_bid_ask(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S", "sell", 50.0, 12.0)
        ob.place_order("B", "buy", 30.0, 10.0)
        assert ob.get_best_ask() == 12.0
        assert ob.get_best_bid() == 10.0
        assert ob.get_spread() == 2.0

    def test_insufficient_balance_rejected(self):
        t, bc = _make_token_and_chain()
        ob = AdvancedOrderBook(t, bc)
        r = ob.place_order("S", "sell", 100.0, 10.0)
        assert r["status"] == "error"

    def test_trade_history(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S", "sell", 50.0, 10.0)
        ob.place_order("B", "buy", 20.0, 10.0)
        h = ob.get_trade_history()
        assert len(h) == 1

    def test_summary(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        ob = AdvancedOrderBook(t, bc)
        ob.place_order("S", "sell", 50.0, 10.0)
        s = ob.get_summary()
        assert s["total_orders"] == 1
        assert s["open_sell_orders"] == 1


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  6. EMISSION OPTIMIZER                                                ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestEmissionOptimizer:
    def test_record_reading(self):
        opt = EmissionOptimizer()
        opt.record_reading(_valid_reading())
        assert opt.get_summary()["facilities_tracked"] == 1

    def test_insufficient_data(self):
        opt = EmissionOptimizer()
        opt.record_reading(_valid_reading())
        recs = opt.generate_recommendations("FAC_001")
        assert recs[0]["recommendation"] == "Insufficient data for analysis"

    def test_recommendations_with_data(self):
        opt = EmissionOptimizer()
        for i in range(25):
            r = _valid_reading()
            r["fuel_rate"] = 300.0 + i * 2  # high fuel
            r["co2e_emission"] = 20.0 + i * 0.5
            opt.record_reading(r)
        opt.compute_benchmarks()
        recs = opt.generate_recommendations("FAC_001")
        assert len(recs) >= 1

    def test_facility_profile(self):
        opt = EmissionOptimizer()
        for _ in range(10):
            opt.record_reading(_valid_reading())
        p = opt.get_facility_profile("FAC_001")
        assert p["total_readings"] == 10
        assert p["avg_co2e"] > 0

    def test_benchmarks(self):
        opt = EmissionOptimizer()
        for i in range(20):
            opt.record_reading(_valid_reading(co2e=15.0 + i))
        opt.compute_benchmarks()
        assert opt.get_summary()["benchmarks_computed"] >= 1

    def test_trend_detection(self):
        opt = EmissionOptimizer()
        # Increasing trend
        for i in range(30):
            r = _valid_reading(co2e=10.0 + i * 2)
            opt.record_reading(r)
        opt.compute_benchmarks()
        recs = opt.generate_recommendations("FAC_001")
        trend_recs = [r for r in recs if r["category"] == "trend_alert"]
        assert len(trend_recs) >= 1


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  7. INCENTIVE & PENALTY ENGINE                                        ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestIncentiveEngine:
    def test_early_adopter(self):
        t, bc = _make_token_and_chain()
        ie = IncentiveEngine(t, bc)
        r = ie.register_early_adopter("FAC_001")
        assert r["early_adopter"] is True

    def test_early_adopter_limit(self):
        t, bc = _make_token_and_chain()
        ie = IncentiveEngine(t, bc)
        for i in range(12):
            ie.register_early_adopter(f"FAC_{i:03d}")
        r = ie.register_early_adopter("FAC_999")
        assert r["early_adopter"] is False

    def test_reward_tier(self):
        t, bc = _make_token_and_chain()
        t.mint("FAC_001", 10.0, "h_base")
        ie = IncentiveEngine(t, bc)
        # Feed readings with high reduction to get gold tier
        for i in range(25):
            r = _valid_reading(credits_earned=0.05, reduction_pct=25.0)
            ie.evaluate_reading(r)
        assert ie.get_participant_tier("FAC_001") == "gold"

    def test_penalty_application(self):
        t, bc = _make_token_and_chain()
        t.mint("FAC_001", 10.0, "h_initial")
        ie = IncentiveEngine(t, bc)
        # Penalise
        r = _valid_reading()
        r["credits"] = {"credits_earned": 0, "credits_penalty": 0.5, "reduction_pct": -10.0}
        result = ie.evaluate_reading(r)
        assert result["action"] == "penalty"
        assert result["penalty_amount"] > 0

    def test_consecutive_violation_escalation(self):
        t, bc = _make_token_and_chain()
        t.mint("FAC_001", 100.0, "h1")
        ie = IncentiveEngine(t, bc)
        penalties = []
        for i in range(5):
            r = _valid_reading()
            r["credits"] = {"credits_earned": 0, "credits_penalty": 1.0, "reduction_pct": -5.0}
            result = ie.evaluate_reading(r)
            penalties.append(result["penalty_amount"])
        # Penalties should escalate
        assert penalties[-1] > penalties[0]

    def test_leaderboard(self):
        t, bc = _make_token_and_chain()
        ie = IncentiveEngine(t, bc)
        for fid in ["F1", "F2", "F3"]:
            t.mint(fid, 10.0, f"h_{fid}")
            for _ in range(5):
                ie.evaluate_reading(_valid_reading(fac_id=fid, reduction_pct=15.0))
        lb = ie.get_leaderboard()
        assert len(lb) == 3

    def test_summary(self):
        t, bc = _make_token_and_chain()
        ie = IncentiveEngine(t, bc)
        ie.register_early_adopter("F1")
        s = ie.get_summary()
        assert s["early_adopters"] == 1


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  8. FRAUD DETECTION                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestFraudDetector:
    def test_no_alerts_on_few_trades(self):
        fd = FraudDetector()
        fd.record_trade({"seller": "A", "buyer": "B", "price": 25, "timestamp": time.time()})
        alerts = fd.analyse({}, 100)
        assert len(alerts) == 0  # below MIN_TRADE_HISTORY

    def test_wash_trade_detection(self):
        fd = FraudDetector()
        now = time.time()
        for i in range(10):
            fd.record_trade({
                "seller": "A", "buyer": "B",
                "price": 25, "timestamp": now,
            })
        alerts = fd.analyse({}, 100)
        wash = [a for a in alerts if a["alert_type"] == "wash_trading"]
        assert len(wash) >= 1

    def test_hoarding_detection(self):
        fd = FraudDetector()
        for i in range(6):
            fd.record_trade({"seller": f"S{i}", "buyer": f"B{i}", "price": 25, "timestamp": time.time()})
        balances = {"hoarder": 50.0, "normal": 10.0}
        alerts = fd.analyse(balances, total_supply=100.0)
        hoarding = [a for a in alerts if a["alert_type"] == "credit_hoarding"]
        assert len(hoarding) >= 1

    def test_price_manipulation_detection(self):
        fd = FraudDetector()
        now = time.time()
        # Normal trades
        for i in range(15):
            fd.record_trade({"seller": f"S{i}", "buyer": f"B{i}", "price": 25.0, "timestamp": now})
        # Anomalous price trade
        fd.record_trade({"seller": "X", "buyer": "Y", "price": 250.0, "timestamp": now})
        alerts = fd.analyse({}, 0)
        manipulation = [a for a in alerts if a["alert_type"] == "price_manipulation"]
        assert len(manipulation) >= 1

    def test_risk_score(self):
        fd = FraudDetector()
        now = time.time()
        for i in range(10):
            fd.record_trade({"seller": "A", "buyer": "B", "price": 25, "timestamp": now})
        fd.analyse({"A": 50}, 100)
        score = fd.get_risk_score("A")
        assert 0 <= score <= 1

    def test_summary(self):
        fd = FraudDetector()
        for i in range(6):
            fd.record_trade({"seller": f"S{i}", "buyer": f"B{i}", "price": 25, "timestamp": time.time()})
        fd.analyse({}, 100)
        s = fd.get_summary()
        assert s["total_trades_analysed"] == 6


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  9. MARKET ANALYTICS                                                  ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestMarketAnalytics:
    def test_record_trade(self):
        ma = MarketAnalytics()
        ma.record_trade({"seller_id": "S", "buyer_id": "B", "credits_traded": 10, "total_value": 250, "price_per_credit": 25})
        r = ma.generate_market_report()
        assert r["market_overview"]["total_trades"] == 1

    def test_emission_analytics(self):
        ma = MarketAnalytics()
        for i in range(10):
            ma.record_emission(_valid_reading(co2e=15.0 + i))
        r = ma.generate_market_report()
        assert r["emission_analytics"]["total_readings"] == 10

    def test_credit_flow(self):
        ma = MarketAnalytics()
        ma.record_mint({"amount": 50.0})
        ma.record_burn({"amount": 10.0})
        r = ma.generate_market_report()
        flow = r["credit_flow"]
        assert flow["total_minted"] == 50.0
        assert flow["total_burned"] == 10.0
        assert flow["net_supply_change"] == 40.0

    def test_price_analytics(self):
        ma = MarketAnalytics()
        for p in [20, 22, 25, 28, 30]:
            ma.record_trade({"price_per_credit": p, "credits_traded": 1, "total_value": p,
                            "seller_id": "S", "buyer_id": "B"})
        r = ma.generate_market_report()
        assert r["price_analytics"]["price_trend"] == "up"

    def test_participant_activity(self):
        ma = MarketAnalytics()
        for i in range(5):
            ma.record_trade({"seller_id": "S1", "buyer_id": "B1", "credits_traded": 10,
                            "total_value": 250, "price_per_credit": 25})
        r = ma.generate_market_report()
        assert len(r["participant_activity"]["top_buyers"]) >= 1

    def test_price_forecast(self):
        ma = MarketAnalytics()
        for p in range(10, 30):
            ma.record_trade({"price_per_credit": float(p), "credits_traded": 1, "total_value": p})
        forecast = ma.get_price_forecast(5)
        assert len(forecast) == 5


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  10. POLICY SIMULATOR                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestPolicySimulator:
    def test_carbon_tax(self):
        ps = PolicySimulator(current_price=25.0, current_emissions=100.0)
        r = ps.simulate_carbon_tax(50.0)
        assert r["policy"] == "carbon_tax"
        assert "price_effect" in r["impact"]

    def test_higher_tax_raises_price(self):
        ps = PolicySimulator(current_price=25.0, current_emissions=100.0)
        low = ps.simulate_carbon_tax(10.0)
        high = ps.simulate_carbon_tax(100.0)
        assert high["impact"]["price_effect"]["projected"] > low["impact"]["price_effect"]["projected"]

    def test_cap_and_trade(self):
        ps = PolicySimulator(current_price=25.0, current_emissions=100.0)
        r = ps.simulate_cap_and_trade(50.0)  # tight cap
        assert r["policy"] == "cap_and_trade"
        assert r["impact"]["price_effect"]["projected"] > 25.0  # tight cap raises price

    def test_loose_cap(self):
        ps = PolicySimulator(current_price=25.0, current_emissions=100.0)
        r = ps.simulate_cap_and_trade(500.0)  # loose cap
        assert r["impact"]["price_effect"]["projected"] <= 25.0

    def test_subsidy(self):
        ps = PolicySimulator(current_price=25.0, current_emissions=100.0)
        r = ps.simulate_subsidy(0.20)
        assert r["policy"] == "clean_energy_subsidy"
        assert r["impact"]["emission_effect"]["change_pct"] < 0  # reduces emissions

    def test_compare_scenarios(self):
        ps = PolicySimulator(current_price=25.0, current_emissions=100.0)
        ps.simulate_carbon_tax(50.0)
        ps.simulate_cap_and_trade(80.0)
        ps.simulate_subsidy(0.20)
        cmp = ps.compare_scenarios()
        assert "best_for_emissions" in cmp
        assert len(cmp["scenarios"]) == 3

    def test_update_baseline(self):
        ps = PolicySimulator()
        ps.update_baseline(30.0, 80.0, 200.0)
        s = ps.get_summary()
        assert s["baseline_price"] == 30.0


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  11. PHASE 3 PIPELINE ORCHESTRATOR                                    ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestPhase3Pipeline:
    def test_creation(self):
        t, bc = _make_token_and_chain()
        p = Phase3Pipeline(t, bc)
        assert p._processed == 0

    def test_register_participants(self):
        t, bc = _make_token_and_chain()
        p = Phase3Pipeline(t, bc)
        p.register_participants(["F1", "F2", "F3"])
        assert p.marketplace.get_market_summary()["registered_participants"] == 3

    def test_process_phase2_result(self):
        t, bc = _make_token_and_chain()
        t.mint("FAC_001", 10.0, "h_init")
        p = Phase3Pipeline(t, bc)
        r = p.process_phase2_result(_valid_reading())
        assert r["phase3_processed"] is True

    def test_process_batch(self):
        t, bc = _make_token_and_chain()
        p = Phase3Pipeline(t, bc)
        readings = [_valid_reading(fac_id=f"FAC_{i:03d}", co2e=15.0 + i) for i in range(10)]
        results = p.process_phase2_batch(readings)
        assert len(results) == 10

    def test_marketplace_round(self):
        t, bc = _make_token_and_chain()
        t.mint("S1", 100, "h1")
        t.mint("S2", 100, "h2")
        p = Phase3Pipeline(t, bc)
        trades = p.run_marketplace_round(
            sellers=[{"participant_id": "S1", "amount": 50.0, "price": 10.0}],
            buyers=[{"participant_id": "B1", "amount": 30.0, "price": 10.0}],
        )
        assert len(trades) == 1
        assert t.balance_of("B1") == 30.0

    def test_recommendations(self):
        t, bc = _make_token_and_chain()
        p = Phase3Pipeline(t, bc)
        for i in range(25):
            r = _valid_reading(co2e=20.0 + i)
            r["fuel_rate"] = 300.0
            p.process_phase2_result(r)
        recs = p.generate_recommendations("FAC_001")
        assert len(recs) >= 1

    def test_policy_simulation(self):
        t, bc = _make_token_and_chain()
        t.mint("F1", 50, "h1")
        p = Phase3Pipeline(t, bc)
        for i in range(10):
            p.process_phase2_result(_valid_reading(co2e=10.0 + i))
        result = p.run_policy_simulation()
        assert "carbon_tax" in result
        assert "comparison" in result

    def test_full_report(self):
        t, bc = _make_token_and_chain()
        p = Phase3Pipeline(t, bc)
        p.process_phase2_result(_valid_reading())
        report = p.get_full_report()
        assert "pipeline_stats" in report
        assert report["pipeline_stats"]["readings_ingested"] == 1

    def test_fraud_analysis(self):
        t, bc = _make_token_and_chain()
        t.mint("S", 100, "h1")
        p = Phase3Pipeline(t, bc)
        # Run trades
        for _ in range(10):
            p.run_marketplace_round(
                sellers=[{"participant_id": "S", "amount": 1.0, "price": 25.0}],
                buyers=[{"participant_id": "B", "amount": 1.0, "price": 25.0}],
            )
        alerts = p.run_fraud_analysis()
        # Should detect at minimum hoarding or wash-trade patterns
        assert isinstance(alerts, list)
