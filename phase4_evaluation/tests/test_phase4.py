"""
Phase 4 Test Suite
====================
Tests all evaluation modules independently.
"""

import os
import sys
import time
import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

import numpy as np

# ── Path setup ─────────────────────────────────────────────────────────
PHASE4_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PHASE4_DIR)


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _make_readings(n=200, n_facilities=5, seed=42):
    """Generate test readings mimicking Phase 1 output."""
    rng = np.random.RandomState(seed)
    readings = []
    facility_types = [
        "chemical_manufacturing", "power_generation",
        "cement_production", "steel_manufacturing", "petroleum_refining",
    ]
    base_time = datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone.utc)

    for i in range(n):
        fac_idx = i % n_facilities
        readings.append({
            "facility_id": f"FAC_{fac_idx+1:03d}",
            "facility_type": facility_types[fac_idx % len(facility_types)],
            "timestamp_utc": (base_time + timedelta(seconds=15 * i)).isoformat(),
            "co2_ppm": float(rng.uniform(350, 600)),
            "ch4_ppm": float(rng.uniform(1.5, 5.0)),
            "nox_ppb": float(rng.uniform(20, 120)),
            "fuel_rate": float(rng.uniform(100, 350)),
            "energy_kwh": float(rng.uniform(1000, 5000)),
        })
    return readings


def _compute_co2e(reading):
    """Simple CO₂e computation."""
    co2_kg = reading["co2_ppm"] * 0.044
    ch4_kg = reading["ch4_ppm"] * 0.016
    nox_kg = reading["nox_ppb"] * 0.000046
    return co2_kg * 1.0 + ch4_kg * 28.0 + nox_kg * 265.0


# ═══════════════════════════════════════════════════════════════════════
#  4.1 DATASET VALIDATION
# ═══════════════════════════════════════════════════════════════════════

class TestDatasetValidator(unittest.TestCase):
    def setUp(self):
        from src.dataset.validator import DatasetValidator
        self.validator = DatasetValidator()
        self.readings = _make_readings(200)
        self.co2e = [_compute_co2e(r) for r in self.readings]

    def test_validate_returns_score(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn("validation_score", result)
        self.assertIn("data_reliability", result)
        self.assertGreater(result["validation_score"], 0)

    def test_completeness(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertEqual(result["completeness"]["score"], 1.0)

    def test_range_validation(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn("range_validation", result)
        self.assertGreater(result["range_validation"]["score"], 0.5)

    def test_distribution_analysis(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn("distribution_analysis", result)
        self.assertIn("fields", result["distribution_analysis"])

    def test_benchmark_alignment(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn("benchmark_alignment", result)
        self.assertIn("by_facility_type", result["benchmark_alignment"])

    def test_temporal_consistency(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn("temporal_consistency", result)

    def test_insufficient_samples(self):
        result = self.validator.validate(self.readings[:5], self.co2e[:5])
        self.assertEqual(result["status"], "error")

    def test_correlation_analysis(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn("correlation_analysis", result)

    def test_reliability_levels(self):
        result = self.validator.validate(self.readings, self.co2e)
        self.assertIn(result["data_reliability"], ["high", "medium", "low"])


# ═══════════════════════════════════════════════════════════════════════
#  4.2 AI MODEL EVALUATION
# ═══════════════════════════════════════════════════════════════════════

class TestModelEvaluator(unittest.TestCase):
    def setUp(self):
        from src.ai_eval.model_evaluator import ModelEvaluator
        self.evaluator = ModelEvaluator()
        self.readings = _make_readings(500, 10)
        self.X = np.array([
            [r["co2_ppm"], r["ch4_ppm"], r["nox_ppb"],
             r["fuel_rate"], r["energy_kwh"], 12, 2]
            for r in self.readings
        ])
        self.y = np.array([_compute_co2e(r) for r in self.readings])

    def _get_trained_estimator(self):
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        estimator = MagicMock()
        rf = RandomForestRegressor(n_estimators=10, random_state=42)
        lr = LinearRegression()
        rf.fit(self.X, self.y)
        lr.fit(self.X, self.y)
        estimator._rf = rf
        estimator._lr = lr
        estimator.feature_importance.return_value = {
            "co2_ppm": 0.95, "ch4_ppm": 0.02, "nox_ppb": 0.01,
            "fuel_rate": 0.01, "energy_kwh": 0.005,
            "hour_of_day": 0.003, "day_of_week": 0.002,
        }
        return estimator

    def _get_trained_detector(self):
        from sklearn.ensemble import IsolationForest
        detector = MagicMock()
        iforest = IsolationForest(contamination=0.05, random_state=42)
        sensor_X = self.X[:, :5]
        iforest.fit(sensor_X)
        detector._iforest = iforest
        detector._mean = np.mean(sensor_X, axis=0)
        detector._std = np.std(sensor_X, axis=0) + 1e-8
        detector._fitted = True

        def _detect(reading):
            vals = np.array([reading.get(f, 0) for f in
                           ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"]])
            z_scores = np.abs((vals - detector._mean) / detector._std)
            is_anomaly = np.max(z_scores) > 3
            return {
                "anomaly_flag": is_anomaly,
                "anomaly_type": "emission_spike" if is_anomaly else "normal",
                "severity_score": min(1.0, float(np.max(z_scores)) / 10.0),
                "details": {},
            }

        detector.detect = _detect
        return detector

    def test_emission_eval_returns_metrics(self):
        estimator = self._get_trained_estimator()
        result = self.evaluator.evaluate_emission_model(estimator, self.X, self.y)
        self.assertIn("random_forest", result)
        self.assertIn("mae", result["random_forest"])
        self.assertIn("rmse", result["random_forest"])
        self.assertIn("r2", result["random_forest"])

    def test_emission_r2_acceptable(self):
        estimator = self._get_trained_estimator()
        result = self.evaluator.evaluate_emission_model(estimator, self.X, self.y)
        self.assertGreater(result["random_forest"]["r2"], 0.9)

    def test_emission_residual_analysis(self):
        estimator = self._get_trained_estimator()
        result = self.evaluator.evaluate_emission_model(estimator, self.X, self.y)
        self.assertIn("residual_analysis", result)
        self.assertIn("mean", result["residual_analysis"])
        self.assertIn("std", result["residual_analysis"])

    def test_emission_per_facility_type(self):
        estimator = self._get_trained_estimator()
        ftypes = [r["facility_type"] for r in self.readings]
        result = self.evaluator.evaluate_emission_model(estimator, self.X, self.y, ftypes)
        self.assertIn("per_facility_type", result)

    def test_anomaly_eval_returns_metrics(self):
        detector = self._get_trained_detector()
        result = self.evaluator.evaluate_anomaly_detector(
            detector, self.X, self.readings,
            ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"],
        )
        self.assertIn("precision", result)
        self.assertIn("recall", result)
        self.assertIn("f1_score", result)
        self.assertIn("confusion_matrix", result)

    def test_anomaly_confusion_matrix(self):
        detector = self._get_trained_detector()
        result = self.evaluator.evaluate_anomaly_detector(
            detector, self.X, self.readings,
            ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"],
        )
        cm = result["confusion_matrix"]
        self.assertIn("tn", cm)
        self.assertIn("fp", cm)
        self.assertIn("fn", cm)
        self.assertIn("tp", cm)

    def test_anomaly_per_type_rates(self):
        detector = self._get_trained_detector()
        result = self.evaluator.evaluate_anomaly_detector(
            detector, self.X, self.readings,
            ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"],
        )
        self.assertIn("per_anomaly_type", result)


# ═══════════════════════════════════════════════════════════════════════
#  4.3 BLOCKCHAIN BENCHMARKING
# ═══════════════════════════════════════════════════════════════════════

class TestBlockchainBenchmarker(unittest.TestCase):
    def setUp(self):
        from src.blockchain_eval.chain_benchmarker import BlockchainBenchmarker
        self.benchmarker = BlockchainBenchmarker()

    def _mock_blockchain_class(self):
        class MockBlockchain:
            def __init__(self, difficulty=2):
                self._blocks = [{"index": 0, "data": {}, "hash": "0" * 64}]
                self._difficulty = difficulty

            def add_block(self, data):
                # Simulate mining delay proportional to difficulty
                time.sleep(0.0001 * (2 ** self._difficulty))
                block = {"index": len(self._blocks), "data": data, "hash": f"mock_{len(self._blocks)}"}
                self._blocks.append(block)
                return block

            def is_valid(self):
                return True

            @property
            def length(self):
                return len(self._blocks)

            def get_chain(self):
                return self._blocks

        return MockBlockchain

    def _data_factory(self):
        return {"type": "emission", "facility_id": "FAC_001", "co2e": 25.5}

    def test_benchmark_all_returns_results(self):
        bc_class = self._mock_blockchain_class()
        result = self.benchmarker.benchmark_all(bc_class, self._data_factory)
        self.assertIn("latency", result)
        self.assertIn("throughput", result)
        self.assertIn("difficulty_scaling", result)
        self.assertIn("validation_scaling", result)
        self.assertIn("storage_efficiency", result)
        self.assertIn("gas_cost", result)

    def test_latency_has_percentiles(self):
        bc_class = self._mock_blockchain_class()
        result = self.benchmarker.benchmark_all(bc_class, self._data_factory)
        self.assertIn("percentiles", result["latency"])
        self.assertIn("p95", result["latency"]["percentiles"])

    def test_throughput_has_batches(self):
        bc_class = self._mock_blockchain_class()
        result = self.benchmarker.benchmark_all(bc_class, self._data_factory)
        self.assertGreater(len(result["throughput"]["batches"]), 0)

    def test_gas_cost_model(self):
        bc_class = self._mock_blockchain_class()
        result = self.benchmarker.benchmark_all(bc_class, self._data_factory)
        self.assertIn("cost_per_tx_usd", result["gas_cost"])
        self.assertGreater(result["gas_cost"]["cost_per_tx_usd"], 0)


# ═══════════════════════════════════════════════════════════════════════
#  4.4 INTEGRATION TESTING
# ═══════════════════════════════════════════════════════════════════════

class TestPipelineTester(unittest.TestCase):
    def setUp(self):
        from src.integration.pipeline_tester import PipelineTester
        self.tester = PipelineTester()

    def _mock_pipeline(self):
        pipeline = MagicMock()
        pipeline.process_single.return_value = {
            "co2e_emission": 25.5, "anomaly_flag": False,
            "credits": {"credits_earned": 0.01, "credits_penalty": 0},
        }
        return pipeline

    def _mock_token(self):
        token = MagicMock()
        token.total_supply = 3.0
        token.get_all_balances.return_value = {"FAC_001": 1.5, "FAC_002": 1.5}
        token._hashes = {"hash1", "hash2", "hash3"}
        return token

    def _mock_blockchain(self):
        bc = MagicMock()
        bc.is_valid.return_value = True
        bc.length = 100
        latestblock = MagicMock()
        latestblock.hash = "a" * 64
        bc.latest_block = latestblock
        return bc

    def test_integration_tests_pass(self):
        pipeline = self._mock_pipeline()
        token = self._mock_token()
        bc = self._mock_blockchain()
        readings = _make_readings(50)

        result = self.tester.run_all_tests(pipeline, token, bc, readings)
        self.assertIn("summary", result)
        self.assertGreater(result["summary"]["tests_passed"], 0)

    def test_credit_conservation(self):
        token = self._mock_token()
        pipeline = self._mock_pipeline()
        bc = self._mock_blockchain()
        readings = _make_readings(20)

        result = self.tester.run_all_tests(pipeline, token, bc, readings)
        self.assertTrue(result["credit_conservation"]["passed"])


# ═══════════════════════════════════════════════════════════════════════
#  4.5 SCALABILITY TESTING
# ═══════════════════════════════════════════════════════════════════════

class TestLoadTester(unittest.TestCase):
    def setUp(self):
        from src.scalability.load_tester import LoadTester
        self.tester = LoadTester()

    def test_facility_scaling(self):
        def gen(n_fac, n_read):
            return _make_readings(min(n_read, 100), n_fac)

        def proc(readings):
            return [{"co2e": _compute_co2e(r)} for r in readings]

        result = self.tester.run_all_tests(gen, proc)
        self.assertIn("facility_scaling", result)
        self.assertGreater(len(result["facility_scaling"]["data_points"]), 0)

    def test_bottleneck_analysis(self):
        def gen(n_fac, n_read):
            return _make_readings(min(n_read, 50), n_fac)

        def proc(readings):
            return [{"co2e": _compute_co2e(r)} for r in readings]

        result = self.tester.run_all_tests(gen, proc)
        self.assertIn("bottleneck_analysis", result)


# ═══════════════════════════════════════════════════════════════════════
#  4.6 COMPARATIVE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

class TestSystemComparator(unittest.TestCase):
    def setUp(self):
        from src.comparative.system_comparator import SystemComparator
        self.comparator = SystemComparator()

    def test_compare_returns_all_systems(self):
        mock_eval = {
            "blockchain": {"validation_scaling": {"results": [{"is_valid": True}]}},
            "scalability": {"facility_scaling": {"data_points": [{"throughput": 100, "success": True}]}, "bottleneck_analysis": "scales_well"},
            "ai_eval": {"emission": {"random_forest": {"r2": 0.99}}, "anomaly": {"f1_score": 0.8}},
        }
        result = self.comparator.compare(mock_eval)
        self.assertIn("proposed", result["systems"])
        self.assertIn("traditional_ets", result["systems"])
        self.assertIn("static_model", result["systems"])

    def test_improvement_percentages(self):
        mock_eval = {
            "blockchain": {"validation_scaling": {"results": [{"is_valid": True}]}},
            "scalability": {"facility_scaling": {"data_points": []}, "bottleneck_analysis": "scales_well"},
            "ai_eval": {"emission": {"random_forest": {"r2": 0.99}}, "anomaly": {"f1_score": 0.85}},
        }
        result = self.comparator.compare(mock_eval)
        self.assertIn("improvement_vs_ets_pct", result)

    def test_radar_chart_data(self):
        mock_eval = {
            "blockchain": {"validation_scaling": {"results": []}},
            "scalability": {"facility_scaling": {"data_points": []}, "bottleneck_analysis": ""},
            "ai_eval": {"emission": {"random_forest": {}}, "anomaly": {}},
        }
        result = self.comparator.compare(mock_eval)
        self.assertIn("radar_chart_data", result)


# ═══════════════════════════════════════════════════════════════════════
#  4.7 CASE STUDIES
# ═══════════════════════════════════════════════════════════════════════

class TestScenarioRunner(unittest.TestCase):
    def setUp(self):
        from src.case_studies.scenario_runner import ScenarioRunner
        self.runner = ScenarioRunner()

    def test_industrial_scenario(self):
        def gen(n, r):
            return _make_readings(r, n)

        def proc(readings):
            results = []
            supply = 0
            for r in readings:
                co2e = _compute_co2e(r)
                credit = max(0, (30 - co2e) * 0.01)
                supply += credit
                results.append({
                    "facility_id": r["facility_id"],
                    "facility_type": r["facility_type"],
                    "co2e_emission": co2e,
                    "anomaly_flag": False,
                    "credits": {"credits_earned": credit},
                })
            return results, supply, supply

        result = self.runner.run_all(gen, proc)
        self.assertIn("scenario_a_industrial", result)
        self.assertIn("scenario_b_smart_city", result)

    def test_scenario_has_stats(self):
        def gen(n, r): return _make_readings(r, n)
        def proc(readings):
            results = [{"facility_id": r["facility_id"], "facility_type": r["facility_type"],
                        "co2e_emission": _compute_co2e(r), "anomaly_flag": False,
                        "credits": {"credits_earned": 0.01}} for r in readings]
            return results, 0.5, 0.5

        result = self.runner.run_all(gen, proc)
        self.assertIn("emission_stats", result["scenario_a_industrial"])


# ═══════════════════════════════════════════════════════════════════════
#  4.8 VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════

class TestResultGenerator(unittest.TestCase):
    def test_import(self):
        from src.visualization.result_generator import ResultGenerator
        rg = ResultGenerator()
        self.assertIsNotNone(rg)

    def test_generate_with_minimal_data(self):
        from src.visualization.result_generator import ResultGenerator
        rg = ResultGenerator()
        # Empty eval results → should produce 0 figures without crashing
        paths = rg.generate_all({})
        self.assertIsInstance(paths, list)


# ═══════════════════════════════════════════════════════════════════════
#  4.9 REPORT BUILDER
# ═══════════════════════════════════════════════════════════════════════

class TestReportBuilder(unittest.TestCase):
    def test_import(self):
        from src.report.report_builder import ReportBuilder
        rb = ReportBuilder()
        self.assertIsNotNone(rb)

    def test_strip_plot_data(self):
        from src.report.report_builder import ReportBuilder
        rb = ReportBuilder()
        data = {"key": "val", "_plot_data": [1, 2, 3], "nested": {"_plot_data": []}}
        clean = rb._strip_plot_data(data)
        self.assertNotIn("_plot_data", clean)
        self.assertNotIn("_plot_data", clean["nested"])

    def test_extract_insights(self):
        from src.report.report_builder import ReportBuilder
        rb = ReportBuilder()
        mock_report = {
            "ai_eval": {
                "emission": {"random_forest": {"r2": 0.99, "mae": 0.1}},
                "anomaly": {"f1_score": 0.85},
            },
            "blockchain": {"latency": {"avg_ms": 10}, "throughput": {"max_tps": 100}},
            "integration": {"summary": {"tests_passed": 5, "tests_total": 5, "all_passed": True}},
            "comparative": {"overall_scores": {"proposed": 8.5, "traditional_ets": 3.8}},
        }
        insights = rb._extract_insights(mock_report)
        self.assertIn("ai_model_accuracy", insights)
        self.assertIn("blockchain_efficiency", insights)
        self.assertIn("system_integrity", insights)


# ═══════════════════════════════════════════════════════════════════════
#  CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestConfig(unittest.TestCase):
    def test_imports(self):
        from src.config import (BENCHMARK_EMISSION_RANGES, SENSOR_REALISTIC_RANGES,
                                BENCH_BATCH_SIZES, COMPARISON_DIMENSIONS)
        self.assertEqual(len(BENCHMARK_EMISSION_RANGES), 5)
        self.assertGreater(len(BENCH_BATCH_SIZES), 0)

    def test_output_dirs(self):
        from src.config import OUTPUT_DIR, FIGURES_DIR, TABLES_DIR
        self.assertTrue(OUTPUT_DIR.exists())


if __name__ == "__main__":
    unittest.main()
