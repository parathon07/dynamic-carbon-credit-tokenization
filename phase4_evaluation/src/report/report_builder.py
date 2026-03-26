"""
Report Builder — Step 4.9
============================
Orchestrates all Phase 4 evaluation modules and assembles results
into a structured report with metrics, figures, and key insights.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

from src.config import OUTPUT_DIR, TABLES_DIR, REPORT_TITLE

logger = logging.getLogger("eval.report_builder")


class ReportBuilder:
    """
    Master orchestrator for Phase 4 evaluation.

    Runs all steps (4.1–4.8) and produces:
      - Structured JSON report
      - Markdown report with tables
      - All 10 publication figures
    """

    def __init__(self):
        self._report: Dict[str, Any] = {}
        self._figure_paths: List[str] = []

    def build_full_report(
        self,
        readings: List[Dict],
        co2e_values: List,
        estimator, detector,
        X_features, y_labels,
        facility_types: List[str],
        blockchain_class,
        block_data_factory,
        p2_pipeline, token, blockchain,
        reading_generator=None,
        pipeline_processor=None,
        policy_simulator=None,
    ) -> Dict[str, Any]:
        """
        Execute all evaluation steps and build the report.

        This is the top-level entry point. All previous phase objects
        are passed in so the evaluator can measure them.
        """
        report = {"title": REPORT_TITLE, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

        # Step 4.1: Dataset validation
        logger.info("Step 4.1: Dataset Validation")
        from src.dataset.validator import DatasetValidator
        dv = DatasetValidator()
        report["dataset_validation"] = dv.validate(readings, co2e_values)

        # Step 4.2: AI model evaluation
        logger.info("Step 4.2: AI Model Evaluation")
        from src.ai_eval.model_evaluator import ModelEvaluator
        me = ModelEvaluator()
        report["ai_eval"] = {
            "emission": me.evaluate_emission_model(estimator, X_features, y_labels, facility_types),
            "anomaly": me.evaluate_anomaly_detector(
                detector, X_features, readings,
                ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"],
            ),
        }

        # Step 4.3: Blockchain benchmarking
        logger.info("Step 4.3: Blockchain Benchmarking")
        from src.blockchain_eval.chain_benchmarker import BlockchainBenchmarker
        bb = BlockchainBenchmarker()
        report["blockchain"] = bb.benchmark_all(blockchain_class, block_data_factory)

        # Step 4.4: Integration testing
        logger.info("Step 4.4: Integration Testing")
        from src.integration.pipeline_tester import PipelineTester
        pt = PipelineTester()
        report["integration"] = pt.run_all_tests(p2_pipeline, token, blockchain, readings)

        # Step 4.5: Scalability testing
        logger.info("Step 4.5: Scalability Testing")
        from src.scalability.load_tester import LoadTester
        lt = LoadTester()
        if reading_generator and pipeline_processor:
            report["scalability"] = lt.run_all_tests(reading_generator, pipeline_processor)
        else:
            report["scalability"] = {"status": "skipped — generators not provided"}

        # Step 4.6: Comparative analysis
        logger.info("Step 4.6: Comparative Analysis")
        from src.comparative.system_comparator import SystemComparator
        sc = SystemComparator()
        report["comparative"] = sc.compare(report)

        # Step 4.7: Case studies
        logger.info("Step 4.7: Case Studies")
        from src.case_studies.scenario_runner import ScenarioRunner
        sr = ScenarioRunner()
        if reading_generator and pipeline_processor:
            report["case_studies"] = sr.run_all(
                reading_generator, pipeline_processor, policy_simulator
            )
        else:
            report["case_studies"] = {"status": "skipped"}

        # Step 4.8: Visualization
        logger.info("Step 4.8: Generating Figures")
        from src.visualization.result_generator import ResultGenerator
        rg = ResultGenerator()
        self._figure_paths = rg.generate_all(report)
        report["figures_generated"] = len(self._figure_paths)
        report["figure_paths"] = self._figure_paths

        # Step 4.9: Compile insights
        report["key_insights"] = self._extract_insights(report)

        # Save outputs
        self._report = report
        self._save_json(report)
        self._save_markdown(report)

        logger.info("Report complete: %d figures, saved to %s", len(self._figure_paths), OUTPUT_DIR)
        return report

    def _extract_insights(self, report: Dict) -> Dict[str, Any]:
        """Extract key findings from all evaluation results."""
        insights = {}

        # AI performance
        ai = report.get("ai_eval", {})
        em = ai.get("emission", {}).get("random_forest", {})
        an = ai.get("anomaly", {})
        insights["ai_model_accuracy"] = {
            "r2_score": em.get("r2", 0),
            "mae": em.get("mae", 0),
            "anomaly_f1": an.get("f1_score", 0),
            "verdict": "Excellent" if em.get("r2", 0) > 0.99 else "Good" if em.get("r2", 0) > 0.95 else "Acceptable",
        }

        # Blockchain efficiency
        bc = report.get("blockchain", {})
        lat = bc.get("latency", {})
        tp = bc.get("throughput", {})
        insights["blockchain_efficiency"] = {
            "avg_latency_ms": lat.get("avg_ms", 0),
            "max_tps": tp.get("max_tps", 0),
            "verdict": "Efficient" if lat.get("avg_ms", 999) < 50 else "Acceptable",
        }

        # Integration
        integ = report.get("integration", {}).get("summary", {})
        insights["system_integrity"] = {
            "tests_passed": integ.get("tests_passed", 0),
            "tests_total": integ.get("tests_total", 0),
            "verdict": "All Passed" if integ.get("all_passed") else "Issues Found",
        }

        # Comparative advantage
        comp = report.get("comparative", {})
        overall = comp.get("overall_scores", {})
        if overall:
            proposed = overall.get("proposed", 0)
            ets = overall.get("traditional_ets", 0)
            improvement = ((proposed - ets) / max(ets, 0.01)) * 100
            insights["competitive_advantage"] = {
                "proposed_score": proposed,
                "ets_score": ets,
                "improvement_pct": round(improvement, 1),
            }

        return insights

    def _save_json(self, report: Dict):
        """Save report as clean JSON (excluding plot data)."""
        clean = self._strip_plot_data(report)
        path = str(OUTPUT_DIR / "evaluation_report.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, default=str)
        logger.info("JSON report saved: %s", path)

    def _save_markdown(self, report: Dict):
        """Save report as formatted Markdown."""
        path = str(OUTPUT_DIR / "evaluation_report.md")
        lines = [f"# {report['title']}", f"\n**Generated:** {report['timestamp']}\n"]

        # Dataset validation
        dv = report.get("dataset_validation", {})
        lines.append("## 1. Dataset Validation")
        lines.append(f"- **Validation Score:** {dv.get('validation_score', 'N/A')}")
        lines.append(f"- **Data Reliability:** {dv.get('data_reliability', 'N/A')}")
        lines.append(f"- **Sample Size:** {dv.get('sample_size', 'N/A')}")
        lines.append("")

        # AI evaluation
        ai = report.get("ai_eval", {})
        em = ai.get("emission", {}).get("random_forest", {})
        an = ai.get("anomaly", {})
        lines.append("## 2. AI Model Evaluation")
        lines.append("### Emission Estimator (Random Forest)")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        for k in ["mae", "rmse", "r2", "mape_pct", "cv_r2_mean"]:
            lines.append(f"| {k.upper()} | {em.get(k, 'N/A')} |")
        lines.append("")
        lines.append("### Anomaly Detector")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        for k in ["precision", "recall", "f1_score", "auc_roc"]:
            lines.append(f"| {k.replace('_', ' ').title()} | {an.get(k, 'N/A')} |")
        lines.append("")

        # Blockchain
        bc = report.get("blockchain", {})
        lat = bc.get("latency", {})
        tp = bc.get("throughput", {})
        lines.append("## 3. Blockchain Performance")
        lines.append(f"- **Avg Latency:** {lat.get('avg_ms', 'N/A')} ms")
        lines.append(f"- **P95 Latency:** {lat.get('percentiles', {}).get('p95', 'N/A')} ms")
        lines.append(f"- **Max TPS:** {tp.get('max_tps', 'N/A')}")
        lines.append("")

        # Integration
        integ = report.get("integration", {}).get("summary", {})
        lines.append("## 4. Integration Testing")
        lines.append(f"- **Tests Passed:** {integ.get('tests_passed', 0)}/{integ.get('tests_total', 0)}")
        lines.append(f"- **Pass Rate:** {integ.get('pass_rate', 0)}%")
        lines.append("")

        # Key insights
        ki = report.get("key_insights", {})
        lines.append("## 9. Key Insights")
        for section, data in ki.items():
            lines.append(f"### {section.replace('_', ' ').title()}")
            if isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
            lines.append("")

        # Figures
        lines.append(f"## Figures Generated: {report.get('figures_generated', 0)}")
        for p in report.get("figure_paths", []):
            name = os.path.basename(p)
            lines.append(f"- `{name}`")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Markdown report saved: %s", path)

    def _strip_plot_data(self, obj):
        """Remove _plot_data keys for clean JSON output."""
        if isinstance(obj, dict):
            return {k: self._strip_plot_data(v) for k, v in obj.items()
                    if not k.startswith("_plot")}
        elif isinstance(obj, list):
            return [self._strip_plot_data(i) for i in obj]
        return obj

    def get_report(self) -> Dict[str, Any]:
        return self._report

    def get_figure_paths(self) -> List[str]:
        return self._figure_paths
