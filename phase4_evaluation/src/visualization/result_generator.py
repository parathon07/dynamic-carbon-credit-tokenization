"""
Visualization & Result Generation — Step 4.8
=================================================
Generates publication-quality figures (PNG, 300 DPI) for all
evaluation metrics across the entire system.

Figures:
  1. Predicted vs Actual CO₂e scatter
  2. Residual distribution histogram
  3. Anomaly detection confusion matrix heatmap
  4. Blockchain TPS vs batch size
  5. Latency distribution box plot
  6. Scalability curves (throughput vs scale)
  7. Comparative radar chart
  8. Credit price dynamics (policy simulation)
  9. Case study emissions (per-facility stacked area)
  10. Feature importance bar chart
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import (
    FIGURES_DIR, FIGURE_DPI, FIGURE_FORMAT, FIGURE_STYLE,
    COLOR_PALETTE, COMPARISON_DIMENSIONS,
)

logger = logging.getLogger("eval.result_generator")


def _setup_matplotlib():
    """Configure matplotlib for publication-quality output."""
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    try:
        plt.style.use(FIGURE_STYLE)
    except OSError:
        plt.style.use("seaborn-v0_8")
    plt.rcParams.update({
        "figure.dpi": FIGURE_DPI,
        "savefig.dpi": FIGURE_DPI,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "legend.fontsize": 10,
        "figure.figsize": (8, 6),
    })
    return plt


class ResultGenerator:
    """Generates all publication-quality figures."""

    def __init__(self):
        self._generated: List[str] = []
        os.makedirs(FIGURES_DIR, exist_ok=True)

    def generate_all(self, eval_results: Dict[str, Any]) -> List[str]:
        """Generate all 10 figures from evaluation results."""
        plt = _setup_matplotlib()
        paths = []

        ai = eval_results.get("ai_eval", {})
        bc = eval_results.get("blockchain", {})
        scale = eval_results.get("scalability", {})
        comp = eval_results.get("comparative", {})
        case = eval_results.get("case_studies", {})

        # 1. Predicted vs Actual scatter
        emission = ai.get("emission", {})
        plot_data = emission.get("_plot_data", {})
        if plot_data.get("y_test") and plot_data.get("y_pred"):
            p = self._fig_predicted_vs_actual(plt, plot_data)
            paths.append(p)

        # 2. Residual distribution
        if plot_data.get("residuals"):
            p = self._fig_residual_distribution(plt, plot_data)
            paths.append(p)

        # 3. Confusion matrix
        anomaly = ai.get("anomaly", {})
        if anomaly.get("confusion_matrix"):
            p = self._fig_confusion_matrix(plt, anomaly)
            paths.append(p)

        # 4. Blockchain TPS
        tp = bc.get("throughput", {})
        if tp.get("batches"):
            p = self._fig_blockchain_tps(plt, tp)
            paths.append(p)

        # 5. Latency distribution
        lat = bc.get("latency", {})
        if lat.get("_raw_latencies"):
            p = self._fig_latency_distribution(plt, lat)
            paths.append(p)

        # 6. Scalability curves
        fac = scale.get("facility_scaling", {})
        if fac.get("data_points"):
            p = self._fig_scalability_curves(plt, fac)
            paths.append(p)

        # 7. Comparative radar
        if comp.get("radar_chart_data"):
            p = self._fig_radar_chart(plt, comp)
            paths.append(p)

        # 8. Policy impact
        policy = case.get("scenario_c_policy_impact", {})
        if policy.get("policy_results"):
            p = self._fig_policy_impact(plt, policy)
            paths.append(p)

        # 9. Case study emissions
        ind = case.get("scenario_a_industrial", {})
        if ind.get("_plot_data", {}).get("facility_emissions"):
            p = self._fig_case_study_emissions(plt, ind)
            paths.append(p)

        # 10. Feature importance
        if emission.get("feature_importance"):
            p = self._fig_feature_importance(plt, emission)
            paths.append(p)

        self._generated = paths
        logger.info("Generated %d figures in %s", len(paths), FIGURES_DIR)
        return paths

    def _save(self, plt, name: str) -> str:
        path = str(FIGURES_DIR / f"{name}.{FIGURE_FORMAT}")
        plt.tight_layout()
        plt.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close()
        return path

    # ── Figure 1: Predicted vs Actual ──────────────────────────────────
    def _fig_predicted_vs_actual(self, plt, data) -> str:
        fig, ax = plt.subplots(figsize=(8, 7))
        y_test = np.array(data["y_test"])
        y_pred = np.array(data["y_pred"])

        ax.scatter(y_test, y_pred, alpha=0.4, s=10, c=COLOR_PALETTE[0], label="Predictions")

        # Perfect prediction line
        lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
        ax.plot(lims, lims, "--", color=COLOR_PALETTE[3], linewidth=2, label="Perfect Prediction")

        from sklearn.metrics import r2_score
        r2 = r2_score(y_test, y_pred)
        ax.set_xlabel("Actual CO₂e (kg)")
        ax.set_ylabel("Predicted CO₂e (kg)")
        ax.set_title(f"Emission Estimation: Predicted vs Actual (R² = {r2:.4f})")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        return self._save(plt, "01_predicted_vs_actual")

    # ── Figure 2: Residual Distribution ────────────────────────────────
    def _fig_residual_distribution(self, plt, data) -> str:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        residuals = np.array(data["residuals"])

        # Histogram
        ax1.hist(residuals, bins=50, color=COLOR_PALETTE[1], alpha=0.7, edgecolor="white")
        ax1.axvline(0, color=COLOR_PALETTE[3], linestyle="--", linewidth=2)
        ax1.set_xlabel("Residual (kg CO₂e)")
        ax1.set_ylabel("Frequency")
        ax1.set_title("Residual Distribution")

        # Q-Q plot
        from scipy import stats
        (osm, osr), (slope, intercept, r) = stats.probplot(residuals, dist="norm")
        ax2.scatter(osm, osr, s=10, alpha=0.5, c=COLOR_PALETTE[0])
        ax2.plot(osm, slope * np.array(osm) + intercept, color=COLOR_PALETTE[3], linewidth=2)
        ax2.set_xlabel("Theoretical Quantiles")
        ax2.set_ylabel("Sample Quantiles")
        ax2.set_title(f"Q-Q Plot (r = {r:.4f})")
        ax2.grid(True, alpha=0.3)

        return self._save(plt, "02_residual_distribution")

    # ── Figure 3: Confusion Matrix ─────────────────────────────────────
    def _fig_confusion_matrix(self, plt, anomaly_data) -> str:
        import seaborn as sns
        fig, ax = plt.subplots(figsize=(7, 6))
        cm = anomaly_data["confusion_matrix"]
        matrix = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])

        sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues",
                    xticklabels=["Normal", "Anomaly"],
                    yticklabels=["Normal", "Anomaly"], ax=ax)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        f1 = anomaly_data.get("f1_score", 0)
        ax.set_title(f"Anomaly Detection Confusion Matrix (F1 = {f1:.4f})")
        return self._save(plt, "03_confusion_matrix")

    # ── Figure 4: Blockchain TPS ───────────────────────────────────────
    def _fig_blockchain_tps(self, plt, throughput_data) -> str:
        fig, ax = plt.subplots(figsize=(8, 6))
        batches = throughput_data["batches"]
        sizes = [b["batch_size"] for b in batches]
        tps = [b["tps"] for b in batches]

        ax.bar(range(len(sizes)), tps, color=COLOR_PALETTE[0], alpha=0.8, edgecolor="white")
        ax.set_xticks(range(len(sizes)))
        ax.set_xticklabels([str(s) for s in sizes])
        ax.set_xlabel("Batch Size (transactions)")
        ax.set_ylabel("Throughput (TPS)")
        ax.set_title("Blockchain Throughput vs Batch Size")
        ax.grid(True, alpha=0.3, axis="y")

        # Annotate values
        for i, v in enumerate(tps):
            ax.text(i, v + max(tps) * 0.02, f"{v:.0f}", ha="center", fontsize=9)

        return self._save(plt, "04_blockchain_tps")

    # ── Figure 5: Latency Distribution ─────────────────────────────────
    def _fig_latency_distribution(self, plt, latency_data) -> str:
        fig, ax = plt.subplots(figsize=(8, 6))
        latencies = latency_data["_raw_latencies"]

        bp = ax.boxplot([latencies], patch_artist=True, widths=0.5,
                        boxprops=dict(facecolor=COLOR_PALETTE[0], alpha=0.6))
        ax.set_ylabel("Latency (ms)")
        ax.set_title(f"Transaction Latency Distribution (n={len(latencies)})")
        ax.set_xticklabels(["Blockchain Transactions"])

        # Add stats annotation
        stats_text = (f"Avg: {latency_data['avg_ms']:.2f} ms\n"
                      f"P95: {latency_data['percentiles']['p95']:.2f} ms\n"
                      f"P99: {latency_data['percentiles']['p99']:.2f} ms")
        ax.text(1.3, np.median(latencies), stats_text, fontsize=10,
                verticalalignment="center", bbox=dict(boxstyle="round", alpha=0.1))
        ax.grid(True, alpha=0.3, axis="y")
        return self._save(plt, "05_latency_distribution")

    # ── Figure 6: Scalability Curves ───────────────────────────────────
    def _fig_scalability_curves(self, plt, facility_data) -> str:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        points = [d for d in facility_data["data_points"] if d.get("success")]

        facilities = [d["facilities"] for d in points]
        throughput = [d["throughput"] for d in points]
        memory = [d.get("peak_memory_mb", 0) for d in points]

        ax1.plot(facilities, throughput, "o-", color=COLOR_PALETTE[0], linewidth=2, markersize=8)
        ax1.set_xlabel("Number of Facilities")
        ax1.set_ylabel("Throughput (readings/sec)")
        ax1.set_title("Pipeline Throughput Scaling")
        ax1.grid(True, alpha=0.3)

        ax2.plot(facilities, memory, "s-", color=COLOR_PALETTE[3], linewidth=2, markersize=8)
        ax2.set_xlabel("Number of Facilities")
        ax2.set_ylabel("Peak Memory (MB)")
        ax2.set_title("Memory Usage Scaling")
        ax2.grid(True, alpha=0.3)

        return self._save(plt, "06_scalability_curves")

    # ── Figure 7: Comparative Radar ────────────────────────────────────
    def _fig_radar_chart(self, plt, comp_data) -> str:
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        dims = COMPARISON_DIMENSIONS
        n = len(dims)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        angles += angles[:1]  # close the polygon

        for sys_name, color, marker in [
            ("proposed", COLOR_PALETTE[0], "o"),
            ("traditional_ets", COLOR_PALETTE[3], "s"),
            ("static_model", COLOR_PALETTE[2], "D"),
        ]:
            values = [comp_data["radar_chart_data"][d][sys_name] for d in dims]
            values += values[:1]
            ax.plot(angles, values, f"-{marker}", color=color, linewidth=2,
                    markersize=8, label=sys_name.replace("_", " ").title())
            ax.fill(angles, values, alpha=0.1, color=color)

        ax.set_thetagrids(np.degrees(angles[:-1]),
                          [d.replace("_", "\n").title() for d in dims])
        ax.set_ylim(0, 10)
        ax.set_title("System Comparison: Radar Chart", pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
        return self._save(plt, "07_comparative_radar")

    # ── Figure 8: Policy Impact ────────────────────────────────────────
    def _fig_policy_impact(self, plt, policy_data) -> str:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        results = policy_data["policy_results"]
        names = list(results.keys())
        price_changes = [results[n]["price_change_pct"] for n in names]
        emission_changes = [results[n]["emission_change_pct"] for n in names]

        colors_price = [COLOR_PALETTE[1] if v < 0 else COLOR_PALETTE[3] for v in price_changes]
        colors_emission = [COLOR_PALETTE[1] if v < 0 else COLOR_PALETTE[3] for v in emission_changes]

        short_names = [n.replace("_", "\n") for n in names]

        ax1.barh(range(len(names)), price_changes, color=colors_price, alpha=0.8)
        ax1.set_yticks(range(len(names)))
        ax1.set_yticklabels(short_names, fontsize=9)
        ax1.set_xlabel("Price Change (%)")
        ax1.set_title("Policy Impact on Credit Price")
        ax1.axvline(0, color="black", linewidth=0.5)
        ax1.grid(True, alpha=0.3, axis="x")

        ax2.barh(range(len(names)), emission_changes, color=colors_emission, alpha=0.8)
        ax2.set_yticks(range(len(names)))
        ax2.set_yticklabels(short_names, fontsize=9)
        ax2.set_xlabel("Emission Change (%)")
        ax2.set_title("Policy Impact on Emissions")
        ax2.axvline(0, color="black", linewidth=0.5)
        ax2.grid(True, alpha=0.3, axis="x")

        return self._save(plt, "08_policy_impact")

    # ── Figure 9: Case Study Emissions ─────────────────────────────────
    def _fig_case_study_emissions(self, plt, industrial_data) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        emissions = industrial_data["_plot_data"]["facility_emissions"]

        for i, (fid, vals) in enumerate(emissions.items()):
            color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
            ax.plot(vals, color=color, alpha=0.8, linewidth=1.5, label=fid)

        ax.set_xlabel("Reading Index")
        ax.set_ylabel("CO₂e Emission (kg)")
        ax.set_title("Industrial Plant: Per-Facility Emission Trends")
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)
        return self._save(plt, "09_case_study_emissions")

    # ── Figure 10: Feature Importance ──────────────────────────────────
    def _fig_feature_importance(self, plt, emission_data) -> str:
        fig, ax = plt.subplots(figsize=(8, 6))
        fi = emission_data["feature_importance"]
        features = list(fi.keys())
        importances = list(fi.values())

        sorted_idx = np.argsort(importances)
        features = [features[i] for i in sorted_idx]
        importances = [importances[i] for i in sorted_idx]

        colors = [COLOR_PALETTE[i % len(COLOR_PALETTE)] for i in range(len(features))]
        ax.barh(features, importances, color=colors, alpha=0.8, edgecolor="white")
        ax.set_xlabel("Importance Score")
        ax.set_title("Random Forest Feature Importance")
        ax.grid(True, alpha=0.3, axis="x")

        for i, v in enumerate(importances):
            ax.text(v + max(importances) * 0.01, i, f"{v:.4f}", va="center", fontsize=9)

        return self._save(plt, "10_feature_importance")

    def get_generated_paths(self) -> List[str]:
        return self._generated
