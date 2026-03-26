"""
Phase 2 — Comprehensive Validation Test Suite
================================================
Tests the entire AI + Blockchain + Tokenization pipeline:

  ▸ Data preprocessing (cleaner, normalizer, synchronizer)
  ▸ AI emission estimation (Random Forest, confidence scoring)
  ▸ Anomaly detection (Isolation Forest, z-score thresholds)
  ▸ Carbon credit calculation (reward/penalty math)
  ▸ Blockchain ledger (chain integrity, proof-of-work)
  ▸ Token management (mint/transfer/burn, double-counting)
  ▸ Smart contracts (validation, issuance, trading)
  ▸ Pipeline orchestrator (end-to-end flow)
  ▸ Dashboard monitor (stat tracking, reports)

Run:
    python -m pytest tests/test_phase2.py -v
"""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import numpy as np
import pytest

# Ensure project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import (
    SENSOR_FIELDS, VALID_SENSOR_BOUNDS, NORMALIZATION_RANGES,
    EMISSION_BASELINES, GWP_CO2, GWP_CH4, GWP_N2O,
    EMISSION_CONVERSION, FACILITY_TYPES, SENSOR_BASELINES,
    CREDIT_CONVERSION_FACTOR, TOKEN_SYMBOL,
)
from src.preprocessing.cleaner import DataCleaner
from src.preprocessing.normalizer import SensorNormalizer
from src.preprocessing.synchronizer import TimestampSynchronizer
from src.ai_engine.emission_model import (
    EmissionEstimator, compute_co2e_ground_truth, extract_features,
)
from src.ai_engine.anomaly_detector import AnomalyDetector
from src.ai_engine.training import generate_synthetic_data
from src.carbon_credits.baselines import get_baseline, get_15s_baseline
from src.carbon_credits.calculator import CarbonCreditCalculator
from src.blockchain.ledger import Blockchain, Block
from src.blockchain.token_manager import CarbonToken
from src.blockchain.smart_contracts import (
    EmissionRecordContract, CreditIssuanceContract, TradingContract,
)
from src.blockchain.trading import TradingEngine
from src.pipeline.orchestrator import Phase2Pipeline
from src.dashboard.monitor import DashboardMonitor


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

def _valid_reading(fac_id="FAC_001", fac_type="chemical_manufacturing",
                   ts="2024-01-01T10:00:00+00:00"):
    return {
        "facility_id": fac_id, "facility_type": fac_type,
        "timestamp_utc": ts,
        "co2_ppm": 450.0, "ch4_ppm": 2.5, "nox_ppb": 55.0,
        "fuel_rate": 180.0, "energy_kwh": 3500.0,
    }

def _trained_models():
    """Train and return estimator + detector."""
    _, X, y = generate_synthetic_data(10, 100, seed=42)
    est = EmissionEstimator()
    est.train(X, y)
    det = AnomalyDetector()
    det.fit(X)
    return est, det


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  1. PREPROCESSING — DataCleaner                                      ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestDataCleaner:
    def test_clean_valid(self):
        r = DataCleaner().clean_reading(_valid_reading())
        assert r is not None and r["quality_flag"] == "clean"

    def test_reject_missing_keys(self):
        r = _valid_reading(); del r["co2_ppm"]
        assert DataCleaner().clean_reading(r) is None

    def test_replace_fault_sentinel(self):
        r = _valid_reading(); r["co2_ppm"] = -999.0
        out = DataCleaner().clean_reading(r)
        assert out is not None
        assert "fault" in out["quality_flag"]

    def test_clip_outlier_high(self):
        r = _valid_reading(); r["co2_ppm"] = 99999.0
        out = DataCleaner().clean_reading(r)
        assert out["co2_ppm"] == VALID_SENSOR_BOUNDS["co2_ppm"][1]

    def test_reject_all_nan(self):
        r = _valid_reading()
        for f in SENSOR_FIELDS: r[f] = None
        assert DataCleaner().clean_reading(r) is None

    def test_batch_interpolation(self):
        readings = [_valid_reading(ts=f"2024-01-01T10:{i:02d}:00+00:00") for i in range(5)]
        readings[2]["co2_ppm"] = -999.0
        batch = DataCleaner().clean_batch(readings)
        assert len(batch) == 5
        assert not np.isnan(batch[2]["co2_ppm"])

    def test_stats_tracking(self):
        c = DataCleaner()
        c.clean_reading(_valid_reading())
        c.clean_reading({})
        s = c.get_stats()
        assert s["total"] == 2 and s["cleaned"] == 1 and s["rejected"] == 1


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  2. PREPROCESSING — SensorNormalizer                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestSensorNormalizer:
    def test_minmax_output_in_01(self):
        n = SensorNormalizer("minmax")
        out = n.normalize_reading(_valid_reading())
        for f in SENSOR_FIELDS:
            assert 0.0 <= out[f] <= 1.0, f"{f}={out[f]}"

    def test_zscore_requires_fit(self):
        n = SensorNormalizer("zscore")
        with pytest.raises(AssertionError):
            n.normalize_reading(_valid_reading())

    def test_zscore_after_fit(self):
        n = SensorNormalizer("zscore")
        data = [_valid_reading() for _ in range(10)]
        n.fit(data)
        out = n.normalize_reading(data[0])
        assert "normalization_mode" in out

    def test_denormalize_roundtrip(self):
        n = SensorNormalizer("minmax")
        r = _valid_reading()
        normed = n.normalize_reading(r)
        for f in SENSOR_FIELDS:
            restored = n.denormalize_value(f, normed[f])
            assert abs(restored - r[f]) < 1.0


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  3. PREPROCESSING — TimestampSynchronizer                            ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestTimestampSynchronizer:
    def test_snap_to_grid(self):
        s = TimestampSynchronizer()
        snapped = s.snap_to_grid("2024-01-01T10:00:07+00:00")
        assert snapped == "2024-01-01T10:00:00+00:00"

    def test_detect_gaps(self):
        readings = [
            _valid_reading(ts="2024-01-01T10:00:00+00:00"),
            _valid_reading(ts="2024-01-01T10:00:15+00:00"),
            _valid_reading(ts="2024-01-01T10:05:00+00:00"),  # 5min gap
        ]
        gaps = TimestampSynchronizer().detect_gaps(readings)
        assert len(gaps) == 1 and gaps[0][2] > 0

    def test_compute_deltas(self):
        readings = [_valid_reading(ts=f"2024-01-01T10:00:{i*15:02d}+00:00") for i in range(3)]
        deltas = TimestampSynchronizer().compute_deltas(readings)
        assert all(d == 15.0 for d in deltas)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  4. AI ENGINE — Emission Estimation                                  ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestEmissionEstimation:
    def test_co2e_ground_truth(self):
        co2e = compute_co2e_ground_truth(_valid_reading())
        assert co2e > 0

    def test_co2e_formula(self):
        r = _valid_reading()
        expected = (r["co2_ppm"] * 0.044 * 1.0
                    + r["ch4_ppm"] * 0.016 * 28.0
                    + r["nox_ppb"] * 0.000046 * 265.0)
        assert abs(compute_co2e_ground_truth(r) - round(expected, 6)) < 0.001

    def test_feature_extraction_length(self):
        f = extract_features(_valid_reading())
        assert len(f) == 7  # 5 sensors + hour + day

    def test_training_and_prediction(self):
        est, _ = _trained_models()
        pred = est.predict(_valid_reading())
        assert pred["co2e_emission"] > 0
        assert 0 <= pred["confidence_score"] <= 1

    def test_cross_val_r2(self):
        _, X, y = generate_synthetic_data(10, 100, 42)
        est = EmissionEstimator()
        metrics = est.train(X, y)
        assert metrics["rf_r2_mean"] > 0.5  # RF should be decent

    def test_feature_importance(self):
        est, _ = _trained_models()
        imp = est.feature_importance()
        assert len(imp) == 7 and all(v >= 0 for v in imp.values())

    def test_batch_prediction(self):
        est, _ = _trained_models()
        readings = [_valid_reading() for _ in range(5)]
        preds = est.predict_batch(readings)
        assert len(preds) == 5


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  5. AI ENGINE — Anomaly Detection                                   ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestAnomalyDetection:
    def test_normal_reading(self):
        _, det = _trained_models()
        result = det.detect(_valid_reading())
        assert result["anomaly_type"] == "normal"

    def test_spike_detection(self):
        _, det = _trained_models()
        r = _valid_reading(); r["co2_ppm"] = 5000.0  # extreme spike
        result = det.detect(r)
        assert result["anomaly_flag"] is True
        assert result["severity_score"] > 0

    def test_multi_sensor_malfunction(self):
        _, det = _trained_models()
        r = _valid_reading()
        r["co2_ppm"] = 5000; r["ch4_ppm"] = 50; r["nox_ppb"] = 900
        result = det.detect(r)
        assert result["anomaly_flag"] is True

    def test_severity_range(self):
        _, det = _trained_models()
        r = _valid_reading(); r["co2_ppm"] = 3000
        result = det.detect(r)
        assert 0 <= result["severity_score"] <= 1

    def test_batch_detection(self):
        _, det = _trained_models()
        results = det.detect_batch([_valid_reading()] * 5)
        assert len(results) == 5


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  6. CARBON CREDITS — Calculator                                     ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestCarbonCredits:
    def test_baseline_lookup(self):
        for ft in FACILITY_TYPES:
            assert get_baseline(ft) > 0
            assert get_15s_baseline(ft) == get_baseline(ft) / 240.0

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            get_baseline("invalid_type")

    def test_credit_earned(self):
        r = _valid_reading()
        r["co2e_emission"] = 0.01  # very low → earn credits
        calc = CarbonCreditCalculator()
        result = calc.calculate(r)
        assert result["credits_earned"] > 0
        assert result["credits_penalty"] == 0

    def test_credit_penalty(self):
        r = _valid_reading()
        r["co2e_emission"] = 999.0  # very high → penalty
        calc = CarbonCreditCalculator()
        result = calc.calculate(r)
        assert result["credits_penalty"] > 0
        assert result["credits_earned"] == 0

    def test_cumulative_summary(self):
        calc = CarbonCreditCalculator()
        for _ in range(10):
            r = _valid_reading(); r["co2e_emission"] = 0.01
            calc.calculate(r)
        s = calc.get_summary()
        assert s["readings_processed"] == 10
        assert s["total_credits_earned"] > 0


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  7. BLOCKCHAIN — Ledger                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestBlockchain:
    def test_genesis_block(self):
        bc = Blockchain()
        assert bc.length == 1
        assert bc.latest_block.index == 0

    def test_add_block(self):
        bc = Blockchain()
        b = bc.add_block({"type": "test", "value": 42})
        assert b.index == 1 and len(b.hash) == 64

    def test_chain_validity(self):
        bc = Blockchain()
        for i in range(5):
            bc.add_block({"i": i})
        assert bc.is_valid()

    def test_tamper_detection(self):
        bc = Blockchain()
        bc.add_block({"data": "original"})
        bc._chain[1].data = {"data": "tampered"}
        assert not bc.is_valid()

    def test_proof_of_work(self):
        bc = Blockchain(difficulty=2)
        b = bc.add_block({"pow_test": True})
        assert b.hash.startswith("00")

    def test_facility_query(self):
        bc = Blockchain()
        bc.add_block({"facility_id": "FAC_001", "co2e": 10})
        bc.add_block({"facility_id": "FAC_002", "co2e": 20})
        bc.add_block({"facility_id": "FAC_001", "co2e": 15})
        results = bc.query_by_facility("FAC_001")
        assert len(results) == 2


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  8. BLOCKCHAIN — Token Manager                                      ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestCarbonToken:
    def test_mint(self):
        t = CarbonToken()
        t.mint("FAC_001", 100.0, "hash_001")
        assert t.balance_of("FAC_001") == 100.0
        assert t.total_supply == 100.0

    def test_double_mint_prevention(self):
        t = CarbonToken()
        t.mint("FAC_001", 50.0, "hash_001")
        with pytest.raises(ValueError, match="Double-counting"):
            t.mint("FAC_001", 50.0, "hash_001")

    def test_transfer(self):
        t = CarbonToken()
        t.mint("FAC_001", 100.0, "h1")
        t.transfer("FAC_001", "FAC_002", 30.0)
        assert t.balance_of("FAC_001") == 70.0
        assert t.balance_of("FAC_002") == 30.0

    def test_insufficient_transfer(self):
        t = CarbonToken()
        t.mint("FAC_001", 10.0, "h1")
        with pytest.raises(ValueError, match="Insufficient"):
            t.transfer("FAC_001", "FAC_002", 50.0)

    def test_burn(self):
        t = CarbonToken()
        t.mint("FAC_001", 100.0, "h1")
        t.burn("FAC_001", 40.0)
        assert t.balance_of("FAC_001") == 60.0
        assert t.total_supply == 60.0

    def test_allowance_and_transferFrom(self):
        t = CarbonToken()
        t.mint("owner", 100.0, "h1")
        t.approve("owner", "spender", 50.0)
        t.transfer_from("spender", "owner", "buyer", 30.0)
        assert t.balance_of("owner") == 70.0
        assert t.balance_of("buyer") == 30.0
        assert t.allowance("owner", "spender") == 20.0

    def test_emission_hash(self):
        r = _valid_reading()
        r["co2e_emission"] = 20.5
        h = CarbonToken.compute_emission_hash(r)
        assert len(h) == 16  # truncated SHA-256

    def test_tx_log(self):
        t = CarbonToken()
        t.mint("A", 10, "h1"); t.transfer("A", "B", 5)
        assert len(t.get_tx_log()) == 2


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  9. SMART CONTRACTS                                                  ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestSmartContracts:
    def test_emission_record_valid(self):
        bc = Blockchain()
        c = EmissionRecordContract(bc)
        r = {"facility_id": "FAC_001", "co2e_emission": 20.0,
             "anomaly_flag": False, "timestamp_utc": "2024-01-01T10:00:00+00:00"}
        result = c.record(r)
        assert result["status"] == "recorded"

    def test_emission_record_rejects_anomaly(self):
        bc = Blockchain()
        c = EmissionRecordContract(bc)
        r = {"facility_id": "FAC_001", "co2e_emission": 20.0, "anomaly_flag": True}
        result = c.record(r)
        assert result["status"] == "rejected"

    def test_emission_record_rejects_negative(self):
        bc = Blockchain()
        c = EmissionRecordContract(bc)
        result = c.record({"facility_id": "F", "co2e_emission": -5})
        assert result["status"] == "rejected"

    def test_credit_issuance_mints_tokens(self):
        bc = Blockchain(); t = CarbonToken()
        calc = CarbonCreditCalculator()
        c = CreditIssuanceContract(bc, t, calc)
        r = _valid_reading(); r["co2e_emission"] = 0.01
        result = c.process(r)
        assert result["credits"]["credits_earned"] > 0

    def test_trading_contract(self):
        bc = Blockchain(); t = CarbonToken()
        tc = TradingContract(bc, t)
        t.mint("seller", 100.0, "h1")
        result = tc.execute_trade("seller", "buyer", 25.0, 10.0)
        assert result["status"] == "executed"
        assert t.balance_of("buyer") == 25.0

    def test_trading_insufficient(self):
        bc = Blockchain(); t = CarbonToken()
        tc = TradingContract(bc, t)
        result = tc.execute_trade("seller", "buyer", 100.0)
        assert result["status"] == "rejected"


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  10. TRADING ENGINE                                                  ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestTradingEngine:
    def test_place_sell_order(self):
        t = CarbonToken(); bc = Blockchain()
        t.mint("seller", 100, "h1")
        eng = TradingEngine(t, bc)
        r = eng.place_order("seller", "sell", 50.0, 10.0)
        assert r["status"] == "placed"

    def test_order_matching(self):
        t = CarbonToken(); bc = Blockchain()
        t.mint("seller", 100, "h1")
        eng = TradingEngine(t, bc)
        eng.place_order("seller", "sell", 50.0, 10.0)
        r = eng.place_order("buyer", "buy", 30.0, 10.0)
        assert t.balance_of("buyer") == 30.0

    def test_order_book_state(self):
        t = CarbonToken(); bc = Blockchain()
        t.mint("S", 100, "h1")
        eng = TradingEngine(t, bc)
        eng.place_order("S", "sell", 50.0, 15.0)
        book = eng.get_order_book()
        assert len(book["sell_orders"]) == 1


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  11. PIPELINE ORCHESTRATOR                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestPipelineOrchestrator:
    def test_e2e_single_reading(self):
        pipe = Phase2Pipeline()
        pipe.train_models(5, 50, seed=42)
        result = pipe.process_reading(_valid_reading())
        assert result is not None
        assert "co2e_emission" in result
        assert "anomaly_flag" in result
        assert result["blockchain_status"] in ("recorded", "rejected")

    def test_e2e_batch(self):
        pipe = Phase2Pipeline()
        pipe.train_models(5, 50, seed=42)
        readings = [_valid_reading(ts=f"2024-01-01T10:{i:02d}:00+00:00")
                    for i in range(10)]
        results = pipe.process_batch(readings)
        assert len(results) == 10

    def test_pipeline_blockchain_integrity(self):
        pipe = Phase2Pipeline()
        pipe.train_models(5, 50, seed=42)
        for i in range(5):
            pipe.process_reading(_valid_reading(ts=f"2024-01-01T10:{i:02d}:00+00:00"))
        assert pipe.blockchain.is_valid()

    def test_pipeline_summary(self):
        pipe = Phase2Pipeline()
        pipe.train_models(5, 50, seed=42)
        pipe.process_reading(_valid_reading())
        s = pipe.get_summary()
        assert s["processed"] == 1
        assert s["blockchain_valid"] is True

    def test_pipeline_rejects_bad_data(self):
        pipe = Phase2Pipeline()
        pipe.train_models(5, 50, seed=42)
        assert pipe.process_reading({"bad": "data"}) is None


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  12. DASHBOARD MONITOR                                              ║
# ╚═══════════════════════════════════════════════════════════════════════╝

class TestDashboardMonitor:
    def test_record_and_report(self):
        mon = DashboardMonitor()
        mon.record_result({
            "facility_id": "FAC_001", "co2e_emission": 20.0,
            "credits": {"net_credits": 0.05, "credits_earned": 0.05},
            "anomaly_flag": False, "block_hash": "abc123",
            "token_minted": True,
        })
        report = mon.generate_report()
        assert report["overview"]["total_processed"] == 1
        assert report["overview"]["blockchain_transactions"] == 1

    def test_anomaly_tracking(self):
        mon = DashboardMonitor()
        mon.record_result({
            "facility_id": "FAC_001", "anomaly_flag": True,
            "anomaly_type": "emission_spike", "severity_score": 0.8,
            "timestamp_utc": "2024-01-01T10:00:00+00:00",
        })
        alerts = mon.get_anomaly_alerts()
        assert len(alerts) == 1 and alerts[0]["type"] == "emission_spike"

    def test_facility_ranking(self):
        mon = DashboardMonitor()
        mon.record_result({"facility_id": "FAC_001",
                           "credits": {"net_credits": 0.1, "credits_earned": 0.1}})
        mon.record_result({"facility_id": "FAC_002",
                           "credits": {"net_credits": 0.5, "credits_earned": 0.5}})
        ranking = mon.get_facility_ranking()
        assert ranking[0]["facility_id"] == "FAC_002"
